"""DATA7 mobility loader.

``scripts/prepare_data7.py`` writes a normalised trace table with columns
``taxi_id,time,cell_id``. This module converts those cell sequences into routes over the
prepared DATA7 topology.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

import pandas as pd

from ..topology.graph import TopologyLayout


def _column(frame: pd.DataFrame, candidates: set) -> str | None:
    columns = {str(name).strip().lower(): name for name in frame.columns}
    return next((columns[name] for name in columns if name in candidates), None)


def build_data7_routes(config, layout: TopologyLayout, needed_cells: int, rng) -> List[List[int]]:
    path = config.mobility.dataset_path
    if not path:
        raise ValueError("mobility.source='data7' requires mobility.dataset_path.")

    frame = pd.read_csv(path)
    taxi_col = _column(frame, {"taxi_id", "vehicle_id", "id"})
    time_col = _column(frame, {"time", "timestamp", "step"})
    cell_col = _column(frame, {"cell_id", "edge_id", "site_id", "id_cell"})
    if not all([taxi_col, time_col, cell_col]):
        raise ValueError(f"DATA7 trace needs taxi/time/cell columns: {list(frame.columns)}")

    frame = frame.sort_values([taxi_col, time_col])
    candidates: List[List[int]] = []
    for _, group in frame.groupby(taxi_col, sort=False):
        route: List[int] = []
        for cell_id in group[cell_col]:
            index = layout.site_id_to_index.get(str(cell_id))
            if index is None:
                continue
            if not route or route[-1] != index:
                route.append(index)
        if len(route) >= 2:
            candidates.append(route)

    if not candidates:
        raise ValueError("DATA7 produced no usable routes for the prepared topology.")

    if len(candidates) > config.mobility.vehicles:
        candidates = rng.sample(candidates, config.mobility.vehicles)

    routes: List[List[int]] = []
    for index in range(config.mobility.vehicles):
        route = list(candidates[index % len(candidates)])
        while len(route) < needed_cells:
            route.extend(route[1:])
        routes.append(route[:needed_cells])
    return routes
