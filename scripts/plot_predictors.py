"""Plot the predictor comparison (oracle / Markov / last-direction) on DATA7."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PREDICTORS = ["oracle", "markov", "last_direction"]
LABELS = {"oracle": "oracle (upper bound)", "markov": "1st-order Markov", "last_direction": "last direction"}
COLORS = {"oracle": "#2ca02c", "markov": "#1f77b4", "last_direction": "#ff7f0e"}


def main() -> int:
    predicted = pd.read_csv("results/predictor_comparison/comparison.csv")
    baselines = pd.read_csv("results/predictor_baselines/comparison.csv")

    figure, axes = plt.subplots(1, 4, figsize=(16, 4.0))
    positions = np.arange(len(PREDICTORS))

    for strategy, marker in (("proactive", "o"), ("proactive_delta", "s")):
        subset = predicted[predicted["strategy"] == strategy].set_index("predictor").reindex(PREDICTORS)
        label_suffix = " (delta)" if strategy.endswith("delta") else " (full)"
        for axis, column, scale in (
            (axes[0], "prediction_accuracy", 100.0),
            (axes[1], "interruption_pct", 1.0),
            (axes[2], "migration_gb", 1.0),
            (axes[3], "post_arrival_lag_mean_steps", 1.0),
        ):
            axis.plot(
                positions,
                subset[column].astype(float).to_numpy() * scale,
                marker=marker,
                color="#333333",
                alpha=0.8,
                label=f"proactive{label_suffix}",
            )

    baseline_value = {
        "interruption_pct": float(baselines[baselines["strategy"] == "reactive"]["interruption_pct"].iloc[0]),
        "migration_gb": float(baselines[baselines["strategy"] == "reactive"]["migration_gb"].iloc[0]),
        "post_arrival_lag_mean_steps": float(
            baselines[baselines["strategy"] == "reactive"]["post_arrival_lag_mean_steps"].iloc[0]
        ),
    }
    baseline_delta = {
        "interruption_pct": float(
            baselines[baselines["strategy"] == "reactive_delta"]["interruption_pct"].iloc[0]
        ),
        "migration_gb": float(baselines[baselines["strategy"] == "reactive_delta"]["migration_gb"].iloc[0]),
        "post_arrival_lag_mean_steps": float(
            baselines[baselines["strategy"] == "reactive_delta"]["post_arrival_lag_mean_steps"].iloc[0]
        ),
    }

    for axis, column in (
        (axes[1], "interruption_pct"),
        (axes[2], "migration_gb"),
        (axes[3], "post_arrival_lag_mean_steps"),
    ):
        axis.axhline(baseline_value[column], color="#d62728", linestyle="--", linewidth=1, label="reactive (full)")
        axis.axhline(
            baseline_delta[column], color="#9467bd", linestyle=":", linewidth=1, label="reactive (delta)"
        )

    axes[0].set_ylabel("Next-cell accuracy (%)")
    axes[1].set_ylabel("Service interruption (%)")
    axes[2].set_ylabel("Migrated data (GB)")
    axes[3].set_ylabel("Post-arrival lag (steps)")
    axes[0].set_title("Prediction accuracy")
    axes[1].set_title("Continuity")
    axes[2].set_title("Migration volume")
    axes[3].set_title("Catch-up lag")

    for axis in axes:
        axis.set_xticks(positions)
        axis.set_xticklabels([LABELS[p] for p in PREDICTORS], rotation=15, fontsize=8)
        axis.grid(alpha=0.3, axis="y")
    axes[0].legend(fontsize=7)
    figure.suptitle("DATA7: predictors for proactive migration (900 s, 40 km/h, 500 Mbps)")
    figure.tight_layout()
    output = Path("results/predictor_comparison/predictor_comparison.png")
    figure.savefig(output, dpi=200)
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
