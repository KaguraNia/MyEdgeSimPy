"""Loaders for the two real taxi mobility datasets (Rome and San Francisco).

Because the raw datasets are distributed in several shapes, the loader accepts the two
formats that are commonly used in the literature and normalises them into a list of
per-taxi polylines (ordered ``(lat, lon)`` samples).

Supported inputs
----------------

1. **One CSV file** with a header containing an identifier, a timestamp and coordinates,
   for example ``taxi_id,timestamp,lat,lon``. This is the format produced by most
   preprocessing scripts for the San Francisco cabspotting traces::

        taxi_id,timestamp,lat,lon
        1,1202913214,37.75134,-122.39420
        1,1202913215,37.75136,-122.39425

2. **A directory of per-taxi files** (the CRAWDAD ``roma/taxi`` layout). Each file may
   contain either a JSON ``POLYLINE`` array of ``[lat, lon]`` pairs or whitespace/comma
   separated rows. Column roles are auto-detected from the values (latitude in
   ``[-90, 90]``, longitude in ``[-180, 180]``, timestamps by magnitude).

The loader returns *polylines*; :func:`trajectories_to_paths` then maps them to the
simulated coverage grid. Mapping is a linear rescaling of the trajectory bounding box
onto the grid, which is sufficient to preserve the *order and relative shape* of the
movement, i.e. exactly what determines the handover sequence and its rate.
"""

from __future__ import annotations

import csv
import json
import math
import os
import random
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from ..topology.graph import TopologyLayout
from .paths import build_traces  # noqa: F401  (re-exported for convenience)

Polyline = List[Tuple[float, float]]


# --------------------------------------------------------------------------------------
# Raw loading
# --------------------------------------------------------------------------------------
def load_taxi_trajectories(path: str | os.PathLike) -> List[Polyline]:
    """Load per-taxi polylines from a CSV file or a directory of per-taxi files."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Taxi dataset path not found: {path}")

    if path.is_dir():
        polylines: List[Polyline] = []
        for file in sorted(path.iterdir()):
            if not file.is_file():
                continue
            try:
                polyline = _parse_file(file)
            except Exception:
                continue
            if len(polyline) >= 2:
                polylines.append(polyline)
        if not polylines:
            raise ValueError(f"No usable taxi trajectories found in directory {path}.")
        return polylines

    return _group_by_taxi(_parse_file(path))


def _parse_file(file: Path) -> List[Tuple[float, float]]:
    text = file.read_text(encoding="utf-8-sig", errors="ignore").strip()
    if not text:
        return []

    # (a) JSON polyline:  [[lat, lon], [lat, lon], ...]
    if text[0] in "[":
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = None
        if isinstance(data, list):
            points = [tuple(map(float, item)) for item in data if isinstance(item, (list, tuple)) and len(item) >= 2]
            if points:
                return _orient(points)

    # (b) Line based. Try JSON first, then numeric parsing with role auto-detection.
    rows: List[Tuple[float, float, float]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        line = re.sub(r"^(POLYLINE|TRIP)\s*[:=]?\s*", "", line, flags=re.IGNORECASE)
        if line.startswith("["):
            try:
                item = json.loads(line)
                if isinstance(item, list) and len(item) >= 2 and all(isinstance(v, (int, float)) for v in item[:2]):
                    rows.append((float("nan"), float(item[0]), float(item[1])))
                    continue
            except json.JSONDecodeError:
                pass
        numbers = _extract_numbers(line)
        if len(numbers) < 2 or not _looks_like_coordinates(numbers):
            continue
        rows.append(_rows_to_lat_lon(numbers))

    points = [(lat, lon) for _, lat, lon in rows if not math.isnan(lat)]
    return _orient(points)


_NUMBER_RE = re.compile(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?")


def _extract_numbers(line: str) -> List[float]:
    values = []
    for token in re.split(r"[;,|\s]+", line):
        token = token.strip()
        if not token:
            continue
        try:
            values.append(float(token))
        except ValueError:
            continue
    return values or [float(v) for v in _NUMBER_RE.findall(line)]


def _looks_like_coordinates(values: Sequence[float]) -> bool:
    pairs = [(v, w) for v in values for w in values if v != w]
    return any(abs(v) <= 90 and abs(w) <= 180 for v, w in pairs)


def _rows_to_lat_lon(values: Sequence[float]) -> Tuple[float, float, float]:
    """Pick the most plausible (timestamp, lat, lon) triple out of a numeric row."""
    timestamp = 0.0
    coordinates = [v for v in values if abs(v) <= 180]
    # Timestamps are large numbers (seconds since epoch / ms) and are not in [-180, 180].
    big = [v for v in values if abs(v) > 180]
    if big:
        timestamp = max(big, key=abs)
    if len(coordinates) >= 2:
        lat, lon = coordinates[-2], coordinates[-1]
        return timestamp, lat, lon
    return timestamp, values[0], values[1]


def _orient(points: Sequence[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """Fix latitude/longitude order when the source stores (lon, lat)."""
    if not points:
        return []
    lats = [p[0] for p in points]
    if max(abs(min(lats)), abs(max(lats))) > 90:
        return [(lon, lat) for lat, lon in points]
    return list(points)


def _group_by_taxi(points: Sequence[Tuple[float, float]]) -> List[Polyline]:
    """A single CSV file is treated as one trajectory (split happens upstream if needed)."""
    return [list(points)] if len(points) >= 2 else []


def load_taxi_csv_grouped(path: str | os.PathLike) -> Dict[str, Polyline]:
    """Load a single CSV with a ``taxi_id`` column, returning one polyline per taxi."""
    path = Path(path)
    grouped: Dict[str, Polyline] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path} has no header row.")
        columns = {name.strip().lower(): name for name in reader.fieldnames}
        id_key = next((columns[c] for c in columns if c in {"taxi_id", "id", "vehicle_id", "cab"}), None)
        lat_key = next((columns[c] for c in columns if c in {"lat", "latitude", "y"}), None)
        lon_key = next((columns[c] for c in columns if c in {"lon", "lng", "long", "longitude", "x"}), None)
        if lat_key is None or lon_key is None:
            raise ValueError(f"Could not find coordinate columns in {path}: {reader.fieldnames}")
        for row in reader:
            try:
                lat = float(row[lat_key])
                lon = float(row[lon_key])
            except (TypeError, ValueError):
                continue
            key = str(row[id_key]) if id_key else "0"
            grouped.setdefault(key, []).append((lat, lon))
    return {k: v for k, v in grouped.items() if len(v) >= 2}


# --------------------------------------------------------------------------------------
# Mapping to the simulated grid
# --------------------------------------------------------------------------------------
def trajectories_to_paths(
    polylines: Sequence[Polyline],
    layout: TopologyLayout,
    max_samples_per_taxi: Optional[int] = None,
) -> List[List[int]]:
    """Collapse lat/lon polylines into ordered routes over the simulated grid."""
    all_points = [point for polyline in polylines for point in polyline]
    if not all_points:
        raise ValueError("The taxi dataset contains no points.")

    lats = [p[0] for p in all_points]
    lons = [p[1] for p in all_points]
    lat_min, lat_max = min(lats), max(lats)
    lon_min, lon_max = min(lons), max(lons)

    xs = sorted({cell.x for cell in layout.cells})
    ys = sorted({cell.y for cell in layout.cells})
    x_min, x_max = xs[0], xs[-1]
    y_min, y_max = ys[0], ys[-1]

    by_coordinate = {cell.coordinates: cell.index for cell in layout.cells}

    routes: List[List[int]] = []
    for polyline in polylines:
        points = polyline
        if max_samples_per_taxi and len(points) > max_samples_per_taxi:
            stride = int(math.ceil(len(points) / max_samples_per_taxi))
            points = points[::stride] + [polyline[-1]]

        route: List[int] = []
        for lat, lon in points:
            # Latitude grows northwards, so it is flipped to match the grid's y axis.
            nx = 0.0 if lon_max == lon_min else (lon - lon_min) / (lon_max - lon_min)
            ny = 0.0 if lat_max == lat_min else (lat - lat_min) / (lat_max - lat_min)
            x = int(round(x_min + nx * (x_max - x_min)))
            y = int(round(y_max - ny * (y_max - y_min)))
            cell_index = by_coordinate.get((x, y))
            if cell_index is None:
                continue
            if not route or route[-1] != cell_index:
                route.append(cell_index)
        if len(route) >= 2:
            routes.append(route)
    if not routes:
        raise ValueError("No taxi trajectory could be mapped onto the simulation grid.")
    return routes


def build_taxi_routes(
    config,
    layout: TopologyLayout,
    needed_cells: int,
    rng: random.Random,
) -> List[List[int]]:
    """Produce vehicle routes from the configured real dataset.

    Vehicles are sampled from the dataset and their routes are cycled until they are long
    enough to cover the whole simulation.
    """
    path = config.mobility.dataset_path
    if not path:
        raise ValueError("mobility.source='taxi' requires mobility.dataset_path.")

    candidate = Path(path)
    if candidate.is_file() and candidate.suffix.lower() == ".csv":
        try:
            grouped = load_taxi_csv_grouped(candidate)
            polylines = list(grouped.values())
        except ValueError:
            polylines = load_taxi_trajectories(candidate)
    else:
        polylines = load_taxi_trajectories(candidate)

    routes = trajectories_to_paths(polylines, layout)
    if not routes:
        raise ValueError("No usable taxi routes were produced.")

    chosen: List[List[int]] = []
    for index in range(config.mobility.vehicles):
        route = list(routes[index % len(routes)])
        while len(route) < needed_cells:
            route.extend(route[1:])
        chosen.append(route[:needed_cells])
    return chosen