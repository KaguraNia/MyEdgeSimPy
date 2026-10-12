"""Vehicle routes and their expansion into a per-step cell trace.

The simulator needs, for every vehicle, the cell it occupies at *every* simulation step.
Two inputs are supported:

* a **route** (an ordered list of cell indices) that is replayed at a speed-dependent
  dwell time per cell, or
* a **real trace** (from the Rome/San Francisco taxi datasets) that is first collapsed
  into a route and then replayed the same way.

Replaying a route at a configurable dwell time is what makes the mobility-speed sweep
meaningful: the same taxi route is driven at 15, 30, 60 km/h, which changes how often the
vehicle crosses a cell and therefore how often the service state must migrate.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from ..topology.graph import TopologyLayout


@dataclass
class VehicleTrace:
    """A single vehicle: its route plus the expanded per-step cell trace."""

    vehicle_id: int
    route: List[int]
    cells: List[tuple]
    source: str = "synthetic"

    @property
    def handover_steps(self) -> List[int]:
        """Steps at which the vehicle changes cell (1-based, aligned with the trace)."""
        steps = []
        for step in range(1, len(self.cells)):
            if self.cells[step] != self.cells[step - 1]:
                steps.append(step)
        return steps

    @property
    def initial_cell(self) -> tuple:
        return self.cells[0]


def replay_path(
    layout: TopologyLayout,
    route: Sequence[int],
    ticks_per_cell: float,
    duration_steps: int,
) -> List[tuple]:
    """Expand a route into one cell coordinate per simulation step.

    ``ticks_per_cell`` is derived from the vehicle speed and the cell size, so a slower
    sweep produces a longer dwell time in each cell.
    """
    if not route:
        raise ValueError("A vehicle route must contain at least one cell.")

    ticks = max(1, int(round(ticks_per_cell)))
    expanded: List[tuple] = []
    for index in route:
        expanded.extend([layout.cell(index).coordinates] * ticks)

    total = duration_steps + 1
    if len(expanded) < total:
        # The vehicle reached the end of its route; it keeps circulating in the last cell.
        expanded.extend([expanded[-1]] * (total - len(expanded)))
    return expanded[:total]


def build_synthetic_routes(
    layout: TopologyLayout,
    n_vehicles: int,
    rng: random.Random,
    needed_cells: int,
    trip_min_cells: int = 3,
    trip_max_cells: int = 8,
) -> List[List[int]]:
    """Generate taxi-like routes: a sequence of trips between random destinations."""
    routes: List[List[int]] = []
    for _ in range(n_vehicles):
        current = rng.randrange(layout.size)
        route = [current]
        while len(route) < needed_cells:
            destination = _pick_destination(layout, rng, current, trip_min_cells, trip_max_cells)
            leg = layout.shortest_path(current, destination)
            route.extend(leg[1:])
            current = destination
        routes.append(route[:needed_cells])
    return routes


def _pick_destination(
    layout: TopologyLayout,
    rng: random.Random,
    current: int,
    trip_min_cells: int,
    trip_max_cells: int,
) -> int:
    best = None
    for _ in range(40):
        candidate = rng.randrange(layout.size)
        hops = len(layout.shortest_path(current, candidate)) - 1
        if trip_min_cells <= hops <= trip_max_cells:
            return candidate
        if best is None or abs(hops - trip_max_cells) < abs(best[0] - trip_max_cells):
            best = (hops, candidate)
    return best[1] if best else rng.randrange(layout.size)


def build_traces(config, layout: TopologyLayout, rng: Optional[random.Random] = None) -> List[VehicleTrace]:
    """Build the per-step cell trace of every vehicle according to the configuration."""
    rng = rng or random.Random(config.simulation.seed)
    ticks_per_cell = config.ticks_per_cell()
    duration = config.simulation.duration_steps
    needed_cells = int(math.ceil((duration + 1) / max(1, ticks_per_cell))) + 2

    mobility = config.mobility
    if mobility.source == "taxi":
        from .taxi import build_taxi_routes

        routes = build_taxi_routes(config, layout, needed_cells, rng)
    elif mobility.source == "synthetic":
        routes = build_synthetic_routes(
            layout,
            n_vehicles=mobility.vehicles,
            rng=rng,
            needed_cells=needed_cells,
            trip_min_cells=mobility.trip_min_cells,
            trip_max_cells=mobility.trip_max_cells,
        )
    else:
        raise ValueError(f"Unknown mobility source '{mobility.source}' (use 'synthetic' or 'taxi').")

    traces = [
        VehicleTrace(
            vehicle_id=index,
            route=route,
            cells=replay_path(layout, route, ticks_per_cell, duration),
            source=mobility.source,
        )
        for index, route in enumerate(routes)
    ]
    return traces