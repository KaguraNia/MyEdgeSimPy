"""Parameter sweeps, most importantly over the vehicle speed."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

import pandas as pd

from ..config import SimulationConfig
from .experiment import ExperimentResult, run_experiment


def run_sweep(
    base_config: SimulationConfig,
    speeds: Sequence[float],
    strategies: Sequence[str],
    output_dir: str | Path,
    *,
    save_runs: bool = True,
    save_dataset_file: bool = False,
) -> pd.DataFrame:
    """Run every (strategy, speed) combination and return the summary table."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    rows: List[Dict[str, Any]] = []
    for strategy in strategies:
        for speed in speeds:
            config = base_config.copy()
            config.migration.strategy = strategy
            config.mobility.speed_kmh = float(speed)
            config.output.directory = str(output_dir)
            config.output.tag = f"{strategy}_v{float(speed):g}"

            result: ExperimentResult = run_experiment(
                config, save=save_runs, save_dataset_file=save_dataset_file
            )
            row = dict(result.summary)
            row.pop("strategy_summary", None)
            row["strategy"] = strategy
            row["speed_kmh"] = float(speed)
            rows.append(row)

    frame = pd.DataFrame(rows)
    frame.to_csv(output_dir / "sweep_summary.csv", index=False)
    return frame


def sweep_metadata(base_config: SimulationConfig, speeds: Sequence[float], strategies: Sequence[str]) -> Dict[str, Any]:
    return {
        "base_config": base_config.to_dict(),
        "speeds": list(speeds),
        "strategies": list(strategies),
    }