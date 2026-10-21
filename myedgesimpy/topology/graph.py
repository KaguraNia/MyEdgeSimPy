"""Pure-Python description of the edge infrastructure geometry.

This module deliberately has no EdgeSimPy dependency: it only decides *where* the base
stations and edge servers are and *how* they are wired together. The scenario builder
turns this description into EdgeSimPy components.

Two sources are supported:

``grid``
    A synthetic ``N x M`` cellular grid. Every cell holds one base station, one edge
    server and one network switch, and neighbours are wired with 4-connectivity. This is
    the default because it makes speed/overlap sweeps reproducible.

``sites``
    Real base-station sites (for example the DATA7 cellular dataset). The expected input
    is a CSV file with, at least, ``latitude`` and ``longitude`` columns (``id`` is
    optional). Sites are snapped to a lattice whose step is derived from the median
    nearest-neighbour distance, and wired to their ``k`` nearest neighbours plus a
    spanning tree so that the graph stays connected.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

Coordinate = Tuple[int, int]


@dataclass(frozen=True)
class Cell:
    """A coverage cell: the granularity at which a vehicle is attached to an edge node."""

    index: int
    x: int
    y: int

    @property
    def coordinates(self) -> Coordinate:
        return (self.x, self.y)


@dataclass
class TopologyLayout:
    """Cells plus the undirected links between them."""

    name: str
    cells: List[Cell]
    links: List[Tuple[int, int]] = field(default_factory=list)
    # Optional mapping from an external site id (e.g. DATA7 cell_id) to the cell index.
    site_id_to_index: Dict[str, int] = field(default_factory=dict)
    # Optional geographic position (latitude, longitude) for direction-based predictors.
    geographic: Dict[int, Tuple[float, float]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._by_coordinate: Dict[Coordinate, int] = {cell.coordinates: cell.index for cell in self.cells}
        adjacency: Dict[int, List[int]] = {cell.index: [] for cell in self.cells}
        for a, b in self.links:
            adjacency[a].append(b)
            adjacency[b].append(a)
        for node in adjacency:
            adjacency[node] = sorted(set(adjacency[node]))
        self._adjacency = adjacency

    # -- lookups ------------------------------------------------------------------------
    @property
    def size(self) -> int:
        return len(self.cells)

    @property
    def adjacency(self) -> Dict[int, List[int]]:
        return self._adjacency

    def index_of(self, coordinates: Coordinate) -> int:
        return self._by_coordinate[coordinates]

    def cell(self, index: int) -> Cell:
        return self.cells[index]

    def coordinates(self) -> List[Coordinate]:
        return [cell.coordinates for cell in self.cells]

    def neighbors(self, index: int) -> List[int]:
        return self._adjacency.get(index, [])

    def position_of(self, index: int) -> Tuple[float, float]:
        """Geographic position when available, otherwise the lattice coordinate."""
        return self.geographic.get(index, self.cells[index].coordinates)

    def shortest_path(self, start: int, goal: int) -> List[int]:
        """Breadth-first shortest path (hop count) between two cells."""
        if start == goal:
            return [start]
        previous: Dict[int, int] = {start: -1}
        queue: List[int] = [start]
        head = 0
        while head < len(queue):
            node = queue[head]
            head += 1
            for nxt in self._adjacency[node]:
                if nxt in previous:
                    continue
                previous[nxt] = node
                if nxt == goal:
                    path = [goal]
                    while previous[path[-1]] != -1:
                        path.append(previous[path[-1]])
                    path.reverse()
                    return path
                queue.append(nxt)
        raise ValueError(f"No path between cell {start} and cell {goal}.")

    def random_path(self, start: int, goal: int) -> List[int]:
        """Shortest path is used as the vehicle route; kept as a hook for richer routing."""
        return self.shortest_path(start, goal)

    def summary(self) -> Dict[str, object]:
        degrees = [len(v) for v in self._adjacency.values()]
        return {
            "name": self.name,
            "cells": self.size,
            "links": len(self.links),
            "mean_degree": round(sum(degrees) / max(len(degrees), 1), 2),
            "min_degree": min(degrees) if degrees else 0,
            "max_degree": max(degrees) if degrees else 0,
        }


# --------------------------------------------------------------------------------------
# Grid layout
# --------------------------------------------------------------------------------------
def grid_layout(x_size: int, y_size: int, name: Optional[str] = None) -> TopologyLayout:
    """Build an ``x_size`` by ``y_size`` 4-connected grid of cells."""
    cells: List[Cell] = []
    index = 0
    for y in range(y_size):
        for x in range(x_size):
            cells.append(Cell(index=index, x=x, y=y))
            index += 1

    links: List[Tuple[int, int]] = []
    by_coord = {cell.coordinates: cell.index for cell in cells}
    for cell in cells:
        for dx, dy in ((1, 0), (0, 1)):
            neighbor = (cell.x + dx, cell.y + dy)
            if neighbor in by_coord:
                links.append((cell.index, by_coord[neighbor]))

    return TopologyLayout(name=name or f"grid-{x_size}x{y_size}", cells=cells, links=links)


# --------------------------------------------------------------------------------------
# Real base-station sites (DATA7)
# --------------------------------------------------------------------------------------
def load_sites_csv(
    path: str,
    id_column: Optional[str] = None,
    latitude_column: str = "latitude",
    longitude_column: str = "longitude",
) -> List[Tuple[float, float]]:
    """Load ``(latitude, longitude)`` pairs from a CSV file.

    Column names are case-insensitive and common aliases are accepted
    (``lat``/``latitude``/``y`` and ``lon``/``lng``/``longitude``/``x``).
    """
    lat_aliases = {latitude_column.lower(), "lat", "latitude", "y"}
    lon_aliases = {longitude_column.lower(), "lon", "lng", "long", "longitude", "x"}

    sites: List[Tuple[float, float]] = []
    with open(path, "r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path} has no header row.")
        columns = {name.strip().lower(): name for name in reader.fieldnames}

        lat_key = next((columns[c] for c in columns if c in lat_aliases), None)
        lon_key = next((columns[c] for c in columns if c in lon_aliases), None)
        if lat_key is None or lon_key is None:
            raise ValueError(
                f"Could not find latitude/longitude columns in {path}. Found: {reader.fieldnames}"
            )

        for row in reader:
            try:
                sites.append((float(row[lat_key]), float(row[lon_key])))
            except (TypeError, ValueError):
                continue
    if not sites:
        raise ValueError(f"No usable base-station sites found in {path}.")
    return sites


def sites_layout(
    sites: Sequence[Tuple[float, float]],
    k_neighbors: int = 3,
    name: str = "sites",
) -> TopologyLayout:
    """Snap real sites onto an integer lattice and wire them into a connected graph."""
    unique = sorted(set(sites))
    if len(unique) < 2:
        raise ValueError("At least two distinct sites are required.")

    step = _median_nearest_neighbor_distance(unique)
    step = step if step > 0 else 1e-6

    # Snap coordinates to a lattice so that each site becomes a distinct cell.
    snapped: Dict[Coordinate, List[Tuple[float, float]]] = {}
    for lat, lon in unique:
        key = (int(round(lat / step)), int(round(lon / step)))
        snapped.setdefault(key, []).append((lat, lon))

    # Normalise the lattice so that coordinates start near the origin (readable ids).
    raw_keys = sorted(snapped)
    offset_x = min(key[0] for key in raw_keys)
    offset_y = min(key[1] for key in raw_keys)
    cells = [
        Cell(index=i, x=key[0] - offset_x, y=key[1] - offset_y)
        for i, key in enumerate(raw_keys)
    ]
    coordinates = [cell.coordinates for cell in cells]

    # k-nearest-neighbour links, then a spanning tree to guarantee connectivity.
    links = set()
    for i, cell in enumerate(cells):
        distances = sorted(
            ((_sq_distance(cell.coordinates, other.coordinates), j) for j, other in enumerate(cells) if j != i),
            key=lambda item: item[0],
        )
        for _, j in distances[: max(1, k_neighbors)]:
            links.add((min(i, j), max(i, j)))

    links |= _spanning_tree_links(coordinates)

    return TopologyLayout(name=name, cells=cells, links=sorted(links))


def labeled_sites_layout(
    sites: Dict[str, Tuple[float, float]],
    k_neighbors: int = 3,
    name: str = "sites",
) -> TopologyLayout:
    """Build a layout from named sites while keeping their external ids.

    Cell coordinates are synthetic labels ``(index, 0)``; the graph is wired using the
    real latitude/longitude of the sites. ``site_id_to_index`` lets a mobility trace refer
    to its original ids (e.g. DATA7 ``cell_id``).
    """
    ids = sorted(sites)
    if len(ids) < 2:
        raise ValueError("At least two sites are required.")

    cells = [Cell(index=i, x=i, y=0) for i in range(len(ids))]
    coordinates = [sites[sid] for sid in ids]
    links = set()
    for i in range(len(ids)):
        distances = sorted(
            ((_sq_distance(coordinates[i], coordinates[j]), j) for j in range(len(ids)) if j != i),
            key=lambda item: item[0],
        )
        for _, j in distances[: max(1, k_neighbors)]:
            links.add((min(i, j), max(i, j)))
    links |= _spanning_tree_links(coordinates)

    return TopologyLayout(
        name=name,
        cells=cells,
        links=sorted(links),
        site_id_to_index={sid: i for i, sid in enumerate(ids)},
        geographic={i: sites[sid] for i, sid in enumerate(ids)},
    )


def data7_layout(cells_path: str, k_neighbors: int = 3) -> TopologyLayout:
    """Build a topology from the prepared DATA7 ``cells.csv``."""
    import pandas as pd

    frame = pd.read_csv(cells_path)
    columns = {str(name).strip().lower(): name for name in frame.columns}
    id_col = next((columns[c] for c in columns if c in {"id", "cell_id", "edge_id"}), None)
    lat_col = next((columns[c] for c in columns if c in {"latitude", "lat", "y"}), None)
    lon_col = next((columns[c] for c in columns if c in {"longitude", "lon", "lng", "x"}), None)
    if not all([id_col, lat_col, lon_col]):
        raise ValueError(f"DATA7 cells file needs id/latitude/longitude columns: {list(frame.columns)}")

    sites = {}
    for record in frame.itertuples(index=False):
        values = dict(zip(frame.columns, record))
        site_id = values[id_col]
        if isinstance(site_id, float) and site_id.is_integer():
            site_id = int(site_id)
        sites[str(site_id)] = (float(values[lat_col]), float(values[lon_col]))
    return labeled_sites_layout(sites, k_neighbors=k_neighbors, name=f"data7-{len(sites)}cells")


def _median_nearest_neighbor_distance(points: Sequence[Tuple[float, float]]) -> float:
    distances: List[float] = []
    for i, point in enumerate(points):
        best = math.inf
        for j, other in enumerate(points):
            if i == j:
                continue
            best = min(best, _sq_distance(point, other))
        if best < math.inf:
            distances.append(math.sqrt(best))
    distances.sort()
    return distances[len(distances) // 2] if distances else 1.0


def _sq_distance(a: Sequence[float], b: Sequence[float]) -> float:
    return sum((float(x) - float(y)) ** 2 for x, y in zip(a, b))


def _spanning_tree_links(coordinates: Sequence[Coordinate]) -> set:
    """Prim's algorithm over the complete graph of cells (Euclidean weights)."""
    n = len(coordinates)
    if n <= 1:
        return set()
    in_tree = {0}
    links = set()
    while len(in_tree) < n:
        best = None
        for i in in_tree:
            for j in range(n):
                if j in in_tree:
                    continue
                weight = _sq_distance(coordinates[i], coordinates[j])
                if best is None or weight < best[0]:
                    best = (weight, i, j)
        _, i, j = best  # type: ignore[misc]
        links.add((min(i, j), max(i, j)))
        in_tree.add(j)
    return links


# --------------------------------------------------------------------------------------
# Factory
# --------------------------------------------------------------------------------------
def build_layout(config) -> TopologyLayout:
    """Build the layout described by a :class:`~myedgesimpy.config.SimulationConfig`."""
    settings = config.topology
    if settings.source == "grid":
        return grid_layout(settings.grid_x, settings.grid_y)

    if settings.source == "sites":
        if not settings.sites_path:
            raise ValueError("topology.source='sites' requires topology.sites_path.")
        sites = load_sites_csv(settings.sites_path)
        return sites_layout(sites, k_neighbors=settings.sites_k_neighbors)

    if settings.source == "data7":
        if not settings.data7_cells_path:
            raise ValueError("topology.source='data7' requires topology.data7_cells_path.")
        return data7_layout(settings.data7_cells_path, k_neighbors=settings.sites_k_neighbors)

    raise ValueError(f"Unknown topology source '{settings.source}' (use 'grid' or 'sites').")
