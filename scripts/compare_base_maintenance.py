"""Compare delta migration with and without neighbour base replication.

    python scripts/compare_base_maintenance.py

Reads the 40 km/h SF/Rome runs and writes ``results/base_maintenance_comparison.csv``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

CASES = {
    "sf": {
        "no_maintenance": Path("results/sf_taxi_sweep/reactive_delta_v40/summary.json"),
        "neighbours": Path("results/sf_taxi_maintenance/summary.json"),
    },
    "rome": {
        "no_maintenance": Path("results/rome_taxi_sweep/reactive_delta_v40/summary.json"),
        "neighbours": Path("results/rome_taxi_maintenance/summary.json"),
    },
}


def row(dataset: str, mode: str, path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    summary = payload["summary"]
    strategy = summary.get("strategy_summary", {})
    return {
        "dataset": dataset,
        "base_maintenance": mode,
        "interruption_pct": round(100.0 * summary["service_interruption_ratio"], 2),
        "state_image_gb": round(summary["migration_mb_total"] / 1024.0, 1),
        "base_sync_gb": round(summary.get("base_sync_mb_total", 0.0) / 1024.0, 1),
        "total_transfer_gb": round(summary.get("total_transfer_mb", summary["migration_mb_total"]) / 1024.0, 1),
        "overhead_ratio": round(summary["overhead_ratio"], 2),
        "cold_targets": strategy.get("migrations_cold_target", 0),
        "warm_targets": strategy.get("migrations_warm_target", 0),
    }


def main() -> int:
    rows = []
    for dataset, modes in CASES.items():
        for mode, path in modes.items():
            if path.exists():
                rows.append(row(dataset, mode, path))
            else:
                print(f"[missing] {path}")

    frame = pd.DataFrame(rows)
    print(frame.to_string(index=False))
    output = Path("results/base_maintenance_comparison.csv")
    frame.to_csv(output, index=False)
    print(f"\nwrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
