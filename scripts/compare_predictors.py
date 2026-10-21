"""Compare trajectory predictors for proactive migration.

    python scripts/compare_predictors.py --config configs/data7.yaml --duration 900

Predictors: ``oracle`` (true future, upper bound), ``last_direction`` (geographic
extrapolation) and ``markov`` (first-order transitions trained leave-one-vehicle-out).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from myedgesimpy.config import load_config  # noqa: E402
from myedgesimpy.metrics.analysis import summarize_run  # noqa: E402
from myedgesimpy.runner import run_experiment  # noqa: E402


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default="configs/data7.yaml")
    parser.add_argument("--duration", type=int, default=900)
    parser.add_argument("--predictors", default="oracle,last_direction,markov")
    parser.add_argument("--strategies", default="proactive,proactive_delta")
    parser.add_argument("--out", default="results/predictor_comparison")
    args = parser.parse_args()

    output = Path(args.out)
    output.mkdir(parents=True, exist_ok=True)
    predictors = [item.strip() for item in args.predictors.split(",") if item.strip()]
    strategies = [item.strip() for item in args.strategies.split(",") if item.strip()]

    rows = []
    for predictor in predictors:
        for strategy in strategies:
            config = load_config(args.config)
            config.simulation.duration_steps = args.duration
            config.migration.strategy = strategy
            config.migration.predictor = predictor
            config.output.directory = str(output)
            config.output.tag = f"{predictor}__{strategy}"

            result = run_experiment(config, save=True)
            row = summarize_run(config.output_dir())
            strategy_summary = result.summary.get("strategy_summary", {})
            row.update(
                {
                    "predictor": predictor,
                    "prediction_accuracy": strategy_summary.get("prediction_accuracy"),
                    "predictions_total": strategy_summary.get("predictions_total"),
                    "interruption_pct": round(result.summary["service_interruption_ratio"] * 100.0, 2),
                    "migration_gb": round(result.summary["migration_mb_total"] / 1024.0, 1),
                }
            )
            rows.append(row)
            print(
                f"{predictor:14s} {strategy:18s} "
                f"acc={row['prediction_accuracy']} n={row['predictions_total']} "
                f"interrupt={row['interruption_pct']}% ready={row['ready_before_handover_pct']}% "
                f"lag={row['post_arrival_lag_mean_steps']} mb={row['migration_gb']}GB "
                f"overhead={row['overhead_ratio']}",
                flush=True,
            )

    frame = pd.DataFrame(rows)
    frame.to_csv(output / "comparison.csv", index=False)
    print(f"\nwrote {output / 'comparison.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
