"""Figures for the speed sweep and the strategy comparison.

All figures are written as PNG files so they can be dropped straight into a paper draft.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Optional

import matplotlib

matplotlib.use("Agg")  # headless-safe
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

STRATEGY_LABELS = {
    "reactive": "Reactive (baseline)",
    "reactive_delta": "Reactive + delta state",
    "proactive": "Proactive + pre-copy",
    "proactive_delta": "Proactive + delta + pre-copy",
    "custom": "Custom",
}

COLORS = {
    "reactive": "#d62728",
    "reactive_delta": "#ff7f0e",
    "proactive": "#1f77b4",
    "proactive_delta": "#2ca02c",
    "custom": "#7f7f7f",
}


def _label(strategy: str) -> str:
    return STRATEGY_LABELS.get(strategy, strategy)


def _color(strategy: str) -> str:
    return COLORS.get(strategy, "#333333")


def _series(frame: pd.DataFrame, column: str, strategy: str) -> pd.DataFrame:
    if column not in frame.columns:
        return frame.iloc[0:0]
    subset = frame[frame["strategy"] == strategy].copy()
    subset = subset[["speed_kmh", column]].dropna()
    return subset.sort_values("speed_kmh")


def plot_sweep(frame: pd.DataFrame, output_dir: str | Path) -> List[Path]:
    """Produce the standard figure set and return the written paths."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    strategies = list(dict.fromkeys(frame["strategy"].tolist()))
    written: List[Path] = []

    written.append(
        _line_figure(
            frame,
            strategies,
            column="service_interruption_ratio",
            ylabel="Service interruption ratio",
            title="Continuity vs. vehicle speed",
            output=output_dir / "interruption_vs_speed.png",
            percent=True,
        )
    )

    written.append(
        _line_figure(
            frame,
            strategies,
            column="mean_migration_duration_steps",
            ylabel="Mean migration duration (steps)",
            title="Migration latency vs. vehicle speed",
            output=output_dir / "migration_duration_vs_speed.png",
        )
    )

    written.append(
        _line_figure(
            frame,
            strategies,
            column="migration_mb_total",
            ylabel="State + image bytes migrated (MB)",
            title="Migration volume vs. vehicle speed",
            output=output_dir / "migration_volume_vs_speed.png",
        )
    )

    written.append(
        _line_figure(
            frame,
            strategies,
            column="sla_violation_ratio",
            ylabel="Delay-SLA violation ratio",
            title="Delay SLA compliance vs. vehicle speed",
            output=output_dir / "sla_violations_vs_speed.png",
            percent=True,
        )
    )

    written.append(_pareto_figure(frame, strategies, output_dir / "pareto_continuity_vs_cost.png"))

    # Bar chart of the components at the highest speed (worst case).
    max_speed = float(frame["speed_kmh"].max())
    written.append(
        _bar_figure(
            frame[frame["speed_kmh"] == max_speed],
            strategies,
            output=output_dir / f"strategy_comparison_v{max_speed:g}.png",
        )
    )
    return written


def _line_figure(
    frame: pd.DataFrame,
    strategies: List[str],
    *,
    column: str,
    ylabel: str,
    title: str,
    output: Path,
    percent: bool = False,
) -> Path:
    figure, axis = plt.subplots(figsize=(7.2, 4.4))
    for strategy in strategies:
        subset = _series(frame, column, strategy)
        if subset.empty:
            continue
        values = subset[column] * (100.0 if percent else 1.0)
        axis.plot(subset["speed_kmh"], values, marker="o", label=_label(strategy), color=_color(strategy))
    axis.set_xlabel("Vehicle speed (km/h)")
    axis.set_ylabel(ylabel + (" (%)" if percent else ""))
    axis.set_title(title)
    axis.grid(alpha=0.3)
    axis.legend(fontsize=8)
    figure.tight_layout()
    figure.savefig(output, dpi=200)
    plt.close(figure)
    return output


def _pareto_figure(frame: pd.DataFrame, strategies: List[str], output: Path) -> Path:
    figure, axis = plt.subplots(figsize=(7.2, 4.8))
    for strategy in strategies:
        subset = frame[frame["strategy"] == strategy].dropna(
            subset=["overhead_ratio", "service_interruption_ratio"]
        )
        if subset.empty:
            continue
        axis.scatter(
            subset["overhead_ratio"] * 100.0,
            subset["service_interruption_ratio"] * 100.0,
            label=_label(strategy),
            color=_color(strategy),
            s=45,
        )
        for _, row in subset.iterrows():
            axis.annotate(f"{row['speed_kmh']:g}", (row["overhead_ratio"] * 100.0, row["service_interruption_ratio"] * 100.0), fontsize=7)
    axis.set_xlabel("Migration overhead ratio (% of payload bytes)")
    axis.set_ylabel("Service interruption ratio (%)")
    axis.set_title("Cost vs. continuity trade-off (labels = speed in km/h)")
    axis.grid(alpha=0.3)
    axis.legend(fontsize=8)
    figure.tight_layout()
    figure.savefig(output, dpi=200)
    plt.close(figure)
    return output


def _bar_figure(frame: pd.DataFrame, strategies: List[str], output: Path) -> Path:
    metrics = {
        "service_interruption_ratio": "Interruption (%)",
        "mean_migration_duration_steps": "Migration time (steps)",
        "migration_mb_total": "Migrated (MB)",
    }
    available = [key for key in metrics if key in frame.columns]
    figure, axes = plt.subplots(1, len(available), figsize=(4.2 * len(available), 4.2))
    if len(available) == 1:
        axes = [axes]

    for axis, column in zip(axes, available):
        values = []
        labels = []
        colors = []
        for strategy in strategies:
            row = frame[frame["strategy"] == strategy]
            if row.empty:
                continue
            value = row.iloc[0][column]
            if value is None or (isinstance(value, float) and math.isnan(value)):
                continue
            if column == "service_interruption_ratio":
                value = value * 100.0
            values.append(value)
            labels.append(strategy)
            colors.append(_color(strategy))
        axis.bar(range(len(values)), values, color=colors)
        axis.set_xticks(range(len(values)))
        axis.set_xticklabels(labels, rotation=20, ha="right", fontsize=8)
        axis.set_title(metrics[column])
        axis.grid(alpha=0.3, axis="y")
    figure.tight_layout()
    figure.savefig(output, dpi=200)
    plt.close(figure)
    return output


def plot_sweep_csv(csv_path: str | Path, output_dir: Optional[str | Path] = None) -> List[Path]:
    """Convenience wrapper: read ``sweep_summary.csv`` and produce the figures."""
    csv_path = Path(csv_path)
    frame = pd.read_csv(csv_path)
    output_dir = Path(output_dir) if output_dir else csv_path.parent / "figures"
    return plot_sweep(frame, output_dir)