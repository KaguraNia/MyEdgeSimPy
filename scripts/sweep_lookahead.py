"""Compare fixed look-ahead windows against the deadline-aware trigger.

The fixed values expose the old sensitivity to a hard-coded parameter. The
``deadline_aware`` row estimates the lead from state bytes, missing image layers,
bandwidth, restore and cutover, so its lead may differ on every migration.

Example:
    python scripts/sweep_lookahead.py configs/data7.yaml \
        --strategies proactive,proactive_delta --fixed 5 12 30 60
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from myedgesimpy.config import load_config  # noqa: E402
from myedgesimpy.runner import run_experiment  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("config", help="Base YAML configuration")
    parser.add_argument("--strategies", default="proactive,proactive_delta")
    parser.add_argument("--fixed", type=int, nargs="+", default=[5, 12, 30, 60])
    parser.add_argument("--safety-steps", type=float, default=None)
    parser.add_argument("--duration-steps", type=int, default=None)
    parser.add_argument("--output", default="results/lookahead_sweep/comparison.csv")
    args = parser.parse_args()

    base = load_config(args.config)
    if args.duration_steps is not None:
        base.simulation.duration_steps = args.duration_steps
    if args.safety_steps is not None:
        base.migration.lookahead_safety_steps = args.safety_steps

    rows = []
    for strategy in [item.strip() for item in args.strategies.split(",") if item.strip()]:
        runs = [("fixed", value) for value in args.fixed] + [("deadline_aware", None)]
        for mode, fixed_steps in runs:
            config = base.copy()
            config.migration.strategy = strategy
            config.migration.lookahead_mode = mode
            if fixed_steps is not None:
                config.migration.lookahead_steps = fixed_steps

            result = run_experiment(config, save=False)
            summary = result.summary
            strategy_summary = summary.get("strategy_summary", {})
            row = {
                "strategy": strategy,
                "lookahead_mode": mode,
                "lookahead_steps": fixed_steps,
                "lookahead_required_mean": strategy_summary.get("lookahead_required_mean"),
                "lookahead_required_max": strategy_summary.get("lookahead_required_max"),
                "interruption_pct": round(100.0 * summary["service_interruption_ratio"], 3),
                "migration_mb": round(summary["migration_mb_total"], 3),
                "overhead_ratio": round(summary["overhead_ratio"], 3),
                "ready_before_handover_pct": summary.get("ready_before_handover_pct"),
                "post_arrival_lag_mean_steps": summary.get("post_arrival_lag_mean_steps"),
                "duration_over_dwell_mean": summary.get("duration_over_dwell_mean"),
                "redundant_rate": summary.get("redundant_rate"),
            }
            rows.append(row)
            print(
                f"{strategy:18s} {mode:14s} lookahead={str(fixed_steps):>4s} "
                f"lead_mean={str(row['lookahead_required_mean']):>7s} "
                f"lead_max={str(row['lookahead_required_max']):>5s} "
                f"interrupt={row['interruption_pct']:6.2f}% "
                f"bytes={row['migration_mb']:10.1f} MB"
            )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
