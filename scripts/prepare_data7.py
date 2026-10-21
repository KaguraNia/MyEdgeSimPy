"""Prepare DATA7 for MyEdgeSimPy.

DATA7 is a long table of (vehicle, time, nearby cell, distance) observations. This script:

1. keeps the nearest cell for every (vehicle, time);
2. selects the ``--cells`` cells that cover the most observations (MORA uses 30 gNBs);
3. remaps every observation to its nearest selected cell;
4. writes ``cells.csv`` (id, latitude, longitude) and ``traces.csv``
   (taxi_id, time, cell_id) for vehicles with at least ``--min-samples`` samples.

Usage:
    python scripts/prepare_data7.py \
        --raw data/raw/data7/extracted/dist/dataset.csv \
        --out data/raw/data7/prepared --cells 30 --min-samples 300
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

EARTH_RADIUS_M = 6_371_000.0


def haversine_m(lat1, lon1, lat2, lon2):
    lat1 = np.radians(lat1)
    lon1 = np.radians(lon1)
    lat2 = np.radians(lat2)
    lon2 = np.radians(lon2)
    a = np.sin((lat1 - lat2) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon1 - lon2) / 2) ** 2
    return 2 * EARTH_RADIUS_M * np.arcsin(np.sqrt(a))


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--raw", required=True)
    parser.add_argument("--out", default="data/raw/data7/prepared")
    parser.add_argument("--cells", type=int, default=30)
    parser.add_argument("--min-samples", type=int, default=300)
    args = parser.parse_args()

    raw = Path(args.raw)
    output = Path(args.out)
    output.mkdir(parents=True, exist_ok=True)

    frame = pd.read_csv(
        raw,
        usecols=[
            "cell_id",
            "cell_lat",
            "cell_lon",
            "time",
            "vehicle_id",
            "vehicle_lat",
            "vehicle_lon",
            "distance",
        ],
    )
    print(f"raw rows={len(frame)} cells={frame.cell_id.nunique()} vehicles={frame.vehicle_id.nunique()}")

    nearest = frame.loc[frame.groupby(["vehicle_id", "time"])["distance"].idxmin()].copy()
    print(f"nearest observations={len(nearest)}")

    frequency = nearest["cell_id"].value_counts()
    selected_ids = frequency.head(args.cells).index.tolist()
    cells = (
        frame[frame["cell_id"].isin(selected_ids)]
        .drop_duplicates("cell_id")[["cell_id", "cell_lat", "cell_lon"]]
        .sort_values("cell_id")
        .reset_index(drop=True)
    )
    print(
        f"selected cells={len(cells)} coverage={100.0 * frequency.head(args.cells).sum() / len(nearest):.1f}%"
    )

    cell_ids = cells["cell_id"].to_numpy()
    cell_lat = cells["cell_lat"].to_numpy()
    cell_lon = cells["cell_lon"].to_numpy()
    distances = haversine_m(
        nearest["vehicle_lat"].to_numpy()[:, None],
        nearest["vehicle_lon"].to_numpy()[:, None],
        cell_lat[None, :],
        cell_lon[None, :],
    )
    nearest["selected_cell"] = cell_ids[distances.argmin(axis=1)]

    counts = nearest.groupby("vehicle_id").size()
    keep = counts[counts >= args.min_samples].index
    traces = nearest[nearest["vehicle_id"].isin(keep)][["vehicle_id", "time", "selected_cell"]]
    traces = traces.rename(columns={"vehicle_id": "taxi_id", "selected_cell": "cell_id"})
    traces = traces.sort_values(["taxi_id", "time"])

    cells.rename(columns={"cell_id": "id", "cell_lat": "latitude", "cell_lon": "longitude"}).to_csv(
        output / "cells.csv", index=False
    )
    traces.to_csv(output / "traces.csv", index=False)

    changed = traces.groupby("taxi_id")["cell_id"].diff().ne(0)
    handovers = changed.groupby(traces["taxi_id"]).sum()
    summary = {
        "raw_rows": int(len(frame)),
        "nearest_observations": int(len(nearest)),
        "selected_cells": int(len(cells)),
        "vehicles_kept": int(len(keep)),
        "trace_rows": int(len(traces)),
        "handovers_per_vehicle": {
            "mean": round(float(handovers.mean()), 2),
            "median": round(float(handovers.median()), 2),
            "max": int(handovers.max()),
        },
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"wrote {output / 'cells.csv'} and {output / 'traces.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
