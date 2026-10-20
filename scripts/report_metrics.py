"""Build the Step-2 metrics report from saved runs.

    python scripts/report_metrics.py --root results --out results/report

Outputs:
    metrics_summary.csv          one row per (dataset, strategy, speed)
    per_service.csv              one row per (dataset, strategy, service)
    main_tradeoff.png            overhead vs interruption
    per_service_interruption.png interruption broken down by service
    lead_time.png                lead time vs ready-before-handover
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from myedgesimpy.metrics.analysis import per_service_table, summarize_tree  # noqa: E402

STRATEGY_COLORS = {
    "reactive": "#d62728",
    "reactive_delta": "#ff7f0e",
    "proactive": "#1f77b4",
    "proactive_delta": "#2ca02c",
    "custom": "#7f7f7f",
}

STRATEGY_LABELS = {
    "reactive": "follow-me (full)",
    "reactive_delta": "follow-me (delta)",
    "proactive": "proactive (full)",
    "proactive_delta": "proactive (delta)",
    "custom": "custom",
}

SERVICE_LABELS = {
    "navigation": "navigation",
    "infotainment": "infotainment",
    "alert": "alert",
    "traffic_analytics": "traffic",
}


def _color(strategy: str) -> str:
    return STRATEGY_COLORS.get(strategy, "#333333")


def _label(strategy: str) -> str:
    return STRATEGY_LABELS.get(strategy, strategy)


def plot_tradeoff(frame: pd.DataFrame, output: Path) -> None:
    figure, axis = plt.subplots(figsize=(7.2, 4.8))
    markers = {"synthetic": "o", "sf": "s", "rome": "^", "sf_taxi": "s", "rome_taxi": "^"}
    for strategy, group in frame.groupby("strategy"):
        axis.scatter(
            group["overhead_ratio"],
            group["interruption_overall"] * 100.0,
            label=_label(strategy),
            color=_color(strategy),
            marker="o",
            s=55,
        )
        for _, row in group.iterrows():
            axis.annotate(row["dataset"], (row["overhead_ratio"], row["interruption_overall"] * 100.0), fontsize=7)
    axis.set_xlabel("Migration overhead (migration bytes / payload bytes)")
    axis.set_ylabel("Service interruption (%)")
    axis.set_title("Continuity vs. overhead")
    axis.grid(alpha=0.3)
    axis.legend(fontsize=8)
    figure.tight_layout()
    figure.savefig(output, dpi=200)
    plt.close(figure)


def plot_per_service(per_service: pd.DataFrame, output: Path) -> None:
    datasets = list(dict.fromkeys(per_service["dataset"]))
    strategies = list(dict.fromkeys(per_service["strategy"]))
    services = list(dict.fromkeys(per_service["service"]))

    figure, axes = plt.subplots(1, max(1, len(datasets)), figsize=(5.0 * max(1, len(datasets)), 4.2), squeeze=False)
    width = 0.8 / max(1, len(strategies))

    for axis, dataset in zip(axes[0], datasets):
        subset = per_service[per_service["dataset"] == dataset]
        positions = np.arange(len(services))
        for index, strategy in enumerate(strategies):
            values = []
            for service in services:
                row = subset[(subset["strategy"] == strategy) & (subset["service"] == service)]
                values.append(row["interruption"].iloc[0] * 100.0 if not row.empty else 0.0)
            axis.bar(
                positions + (index - (len(strategies) - 1) / 2) * width,
                values,
                width,
                color=_color(strategy),
                label=_label(strategy),
            )
        axis.set_xticks(positions)
        axis.set_xticklabels([SERVICE_LABELS.get(s, s) for s in services], rotation=15)
        axis.set_ylabel("Interruption (%)")
        axis.set_title(dataset)
        axis.grid(alpha=0.3, axis="y")
    axes[0][0].legend(fontsize=7)
    figure.tight_layout()
    figure.savefig(output, dpi=200)
    plt.close(figure)


def plot_lead_time(frame: pd.DataFrame, output: Path) -> None:
    datasets = list(dict.fromkeys(frame["dataset"]))
    strategies = list(dict.fromkeys(frame["strategy"]))
    positions = np.arange(len(datasets))
    width = 0.8 / max(1, len(strategies))

    figure, axis = plt.subplots(figsize=(8.2, 4.4))
    for index, strategy in enumerate(strategies):
        values = []
        for dataset in datasets:
            row = frame[(frame["dataset"] == dataset) & (frame["strategy"] == strategy)]
            values.append(row["ready_before_handover_pct"].iloc[0] if not row.empty else 0.0)
        axis.bar(
            positions + (index - (len(strategies) - 1) / 2) * width,
            values,
            width,
            label=_label(strategy),
            color=_color(strategy),
        )

    axis.set_xticks(positions)
    axis.set_xticklabels(datasets)
    axis.set_ylabel("Ready before handover (%)")
    axis.set_title("Does the migration finish before the vehicle arrives?")
    axis.grid(alpha=0.3, axis="y")
    axis.legend(fontsize=8)
    figure.tight_layout()
    figure.savefig(output, dpi=200)
    plt.close(figure)


def plot_time_breakdown(frame: pd.DataFrame, output: Path) -> None:
    """Stacked bars: share of migration time spent waiting / pulling / transferring.

    The phase mix is almost identical across strategies, so one bar per dataset (averaged
    across strategies) is clearer than four overlapping bars.
    """
    datasets = list(dict.fromkeys(frame["dataset"]))
    grouped = frame.groupby("dataset")[["waiting_ratio_mean", "pulling_ratio_mean", "state_ratio_mean"]].mean()
    grouped = grouped.reindex(datasets).fillna(0.0) * 100.0
    positions = np.arange(len(datasets))

    figure, axis = plt.subplots(figsize=(7.6, 4.4))
    waiting = grouped["waiting_ratio_mean"].to_numpy()
    pulling = grouped["pulling_ratio_mean"].to_numpy()
    state = grouped["state_ratio_mean"].to_numpy()
    axis.bar(positions, waiting, color="#9e9e9e", label="waiting")
    axis.bar(positions, pulling, bottom=waiting, color="#ff7f0e", label="pulling layers")
    axis.bar(positions, state, bottom=waiting + pulling, color="#1f77b4", label="state transfer")
    for index, dataset in enumerate(datasets):
        axis.text(index, 101.5, f"pull {pulling[index]:.0f}%", ha="center", fontsize=9)

    axis.set_ylim(0, 110)
    axis.set_xticks(positions)
    axis.set_xticklabels(datasets)
    axis.set_ylabel("Share of migration time (%)")
    axis.set_title("Where does migration time go? (mean across strategies)")
    axis.grid(alpha=0.3, axis="y")
    axis.legend(fontsize=8)
    figure.tight_layout()
    figure.savefig(output, dpi=200)
    plt.close(figure)


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--roots",
        nargs="+",
        default=[
            "results/synthetic_16x16_sweep",
            "results/sf_taxi_sweep",
            "results/rome_taxi_sweep",
        ],
        help="sweep directories to include",
    )
    parser.add_argument("--out", default="results/report")
    parser.add_argument("--speed", type=float, default=40.0)
    args = parser.parse_args()

    output = Path(args.out)
    output.mkdir(parents=True, exist_ok=True)

    frame = pd.concat([summarize_tree(root) for root in args.roots], ignore_index=True)
    if frame.empty:
        raise SystemExit(f"No runs found under {args.roots}")

    frame = frame[frame["speed_kmh"] == args.speed].copy()
    if frame.empty:
        raise SystemExit(f"No runs at {args.speed} km/h")

    per_service = pd.concat([per_service_table(root) for root in args.roots], ignore_index=True)
    per_service = per_service[per_service["speed_kmh"] == args.speed].copy()

    frame.to_csv(output / "metrics_summary.csv", index=False)
    per_service.to_csv(output / "per_service.csv", index=False)

    plot_tradeoff(frame, output / "main_tradeoff.png")
    plot_per_service(per_service, output / "per_service_interruption.png")
    plot_lead_time(frame, output / "lead_time.png")
    plot_time_breakdown(frame, output / "time_breakdown.png")

    columns = [
        "dataset",
        "strategy",
        "interruption_overall",
        "lead_mean_steps",
        "ready_before_handover_pct",
        "post_arrival_lag_mean_steps",
        "duration_over_dwell_mean",
        "redundant_rate",
        "cold_target_rate",
        "restore_steps_mean",
        "unfinished_rate",
        "bandwidth_time_per_handover",
        "concurrent_peak",
        "control_plane_flows_per_handover",
        "waiting_ratio_mean",
        "migration_mb",
        "overhead_ratio",
    ]
    available = [column for column in columns if column in frame.columns]
    print(frame[available].to_string(index=False))
    print(f"\nwrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
