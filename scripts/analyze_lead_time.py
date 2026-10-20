"""Derive two missing migration metrics from saved runs.

For every migration we pair it with the handover it serves (same vehicle, same
source -> target cells) and compute:

* **lead time**: ``migration.start - handover.step``.
  Positive = the migration started before the vehicle crossed the cell boundary.
  Negative = it started after the handover (follow-me style).
* **ready before handover**: did the migration finish before the handover?
* **post-arrival lag**: if it finished after the handover, how many steps was the
  service still catching up after the vehicle had already arrived?

Usage:
    python scripts/analyze_lead_time.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

CASES = [
    ("Synthetic", Path("results/synthetic_16x16_sweep")),
    ("San Francisco", Path("results/sf_taxi_sweep")),
    ("Rome", Path("results/rome_taxi_sweep")),
]

STRATEGIES = ["reactive", "reactive_delta", "proactive", "proactive_delta"]


def analyze(run_directory: Path) -> dict:
    migrations = pd.read_csv(run_directory / "migrations.csv")
    handovers = pd.read_csv(run_directory / "handovers.csv")

    leads = []
    ready = 0
    lags = []
    total = 0

    for _, migration in migrations.iterrows():
        candidates = handovers[
            (handovers["vehicle_id"] == migration["vehicle_id"])
            & (handovers["source_cell"] == migration["origin_cell"])
            & (handovers["target_cell"] == migration["target_cell"])
        ]
        if candidates.empty:
            continue

        distances = (candidates["step"] - migration["start_step"]).abs()
        handover_step = int(candidates.loc[distances.idxmin(), "step"])
        total += 1
        leads.append(int(migration["start_step"] - handover_step))

        if pd.notna(migration["end_step"]):
            lag = max(0.0, float(migration["end_step"] - handover_step))
            lags.append(lag)
            if migration["end_step"] <= handover_step:
                ready += 1

    return {
        "migrations_matched": total,
        "lead_mean_steps": round(sum(leads) / len(leads), 1) if leads else None,
        "ready_before_handover_pct": round(100.0 * ready / total, 1) if total else None,
        "post_arrival_lag_mean_steps": round(sum(lags) / len(lags), 1) if lags else None,
        "post_arrival_lag_p95_steps": round(pd.Series(lags).quantile(0.95), 1) if lags else None,
    }


def main() -> int:
    rows = []
    for dataset, root in CASES:
        for strategy in STRATEGIES:
            run_directory = root / f"{strategy}_v40"
            if not run_directory.exists():
                continue
            row = {"dataset": dataset, "strategy": strategy}
            row.update(analyze(run_directory))
            rows.append(row)

    frame = pd.DataFrame(rows)
    print(frame.to_string(index=False))
    output = Path("results/lead_time_analysis.csv")
    frame.to_csv(output, index=False)
    print(f"\nwrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
