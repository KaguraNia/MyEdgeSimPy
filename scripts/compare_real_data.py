"""Compare synthetic, San Francisco and Rome sweeps at the same speed.

Usage:
    python scripts/compare_real_data.py

Reads the three sweep summaries produced by the ``--out`` directories below and writes
``results/real_data_comparison.png``.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

SOURCES = {
    "Synthetic 16x16": Path("results/synthetic_16x16_sweep/sweep_summary.csv"),
    "San Francisco": Path("results/sf_taxi_sweep/sweep_summary.csv"),
    "Rome": Path("results/rome_taxi_sweep/sweep_summary.csv"),
}

STRATEGIES = {
    "reactive": ("follow-me (full)", "#d62728"),
    "reactive_delta": ("follow-me (delta)", "#ff7f0e"),
    "proactive": ("proactive (full)", "#1f77b4"),
    "proactive_delta": ("proactive (delta)", "#2ca02c"),
}


def main() -> int:
    frames = {}
    for dataset, path in SOURCES.items():
        if not path.exists():
            raise SystemExit(f"missing {path}; run the three sweeps first")
        frames[dataset] = pd.read_csv(path)

    figure, axes = plt.subplots(1, 2, figsize=(13, 4.8))
    datasets = list(frames)
    width = 0.2
    positions = np.arange(len(datasets))

    for index, (strategy, (label, color)) in enumerate(STRATEGIES.items()):
        interruption = []
        volume = []
        for dataset in datasets:
            row = frames[dataset][frames[dataset]["strategy"] == strategy].iloc[0]
            interruption.append(row["service_interruption_ratio"] * 100.0)
            volume.append(row["migration_mb_total"] / 1024.0)
        offset = (index - 1.5) * width
        axes[0].bar(positions + offset, interruption, width, label=label, color=color)
        axes[1].bar(positions + offset, volume, width, label=label, color=color)

    axes[0].set_ylabel("Service interruption (%)")
    axes[0].set_title("Continuity at 40 km/h")
    axes[1].set_ylabel("Migrated state + image (GB)")
    axes[1].set_title("Migration volume at 40 km/h")
    for axis in axes:
        axis.set_xticks(positions)
        axis.set_xticklabels(datasets)
        axis.grid(alpha=0.3, axis="y")
    axes[0].legend(fontsize=8)

    figure.tight_layout()
    output = Path("results/real_data_comparison.png")
    figure.savefig(output, dpi=200)
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
