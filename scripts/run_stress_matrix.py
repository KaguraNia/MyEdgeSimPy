"""Run the bandwidth/load x speed x strategy stress matrix on the SF traces.

Scenario envelope (documented as a sensitivity range, not a single measured value):

    constrained  100 Mbps,  12 vehicles
    typical      500 Mbps,  12 vehicles
    good        1000 Mbps,  12 vehicles
    high load    500 Mbps,  30 vehicles
    worst        100 Mbps,  30 vehicles

Speeds: 20, 40, 60, 90 km/h. Strategies: the four migration presets.

Usage:
    python scripts/run_stress_matrix.py --out results/stress_sf
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from myedgesimpy.config import load_config  # noqa: E402
from myedgesimpy.metrics.analysis import summarize_run  # noqa: E402
from myedgesimpy.runner import run_experiment  # noqa: E402

SCENARIOS = [
    ("constrained", 100, 12),
    ("typical", 500, 12),
    ("good", 1000, 12),
    ("high_load", 500, 30),
    ("worst", 100, 30),
]

SPEEDS = [20.0, 40.0, 60.0, 90.0]

STRATEGIES = ["reactive", "reactive_delta", "proactive", "proactive_delta"]

COLORS = {
    "reactive": "#d62728",
    "reactive_delta": "#ff7f0e",
    "proactive": "#1f77b4",
    "proactive_delta": "#2ca02c",
}

LABELS = {
    "reactive": "follow-me (full)",
    "reactive_delta": "follow-me (delta)",
    "proactive": "proactive (full)",
    "proactive_delta": "proactive (delta)",
}


def plot_panels(frame: pd.DataFrame, column: str, ylabel: str, title: str, output: Path, percent: bool = False, hline=None) -> None:
    scenarios = list(dict.fromkeys(frame["scenario"]))
    figure, axes = plt.subplots(1, len(scenarios), figsize=(4.0 * len(scenarios), 4.2), sharey=True, squeeze=False)
    for axis, scenario in zip(axes[0], scenarios):
        subset = frame[frame["scenario"] == scenario]
        for strategy in STRATEGIES:
            values = subset[subset["strategy"] == strategy].sort_values("speed_kmh")
            if values.empty:
                continue
            y = values[column] * (100.0 if percent else 1.0)
            axis.plot(values["speed_kmh"], y, marker="o", label=LABELS[strategy], color=COLORS[strategy])
        if hline is not None:
            axis.axhline(hline, color="#555555", linestyle="--", linewidth=1)
        axis.set_title(scenario, fontsize=9)
        axis.set_xlabel("speed (km/h)")
        axis.grid(alpha=0.3)
    axes[0][0].set_ylabel(ylabel)
    axes[0][0].legend(fontsize=6.5)
    figure.suptitle(title)
    figure.tight_layout()
    figure.savefig(output, dpi=200)
    plt.close(figure)


def plot_tradeoff(frame: pd.DataFrame, output: Path) -> None:
    figure, axis = plt.subplots(figsize=(8.2, 4.8))
    scenarios = list(dict.fromkeys(frame["scenario"]))
    markers = dict(zip(scenarios, ["o", "s", "^", "D", "v"]))
    for scenario in scenarios:
        subset = frame[frame["scenario"] == scenario]
        for strategy in STRATEGIES:
            values = subset[subset["strategy"] == strategy]
            if values.empty:
                continue
            axis.scatter(
                values["overhead_ratio"],
                values["interruption_overall"] * 100.0,
                marker=markers[scenario],
                color=COLORS[strategy],
                s=45,
                alpha=0.85,
            )
    for strategy in STRATEGIES:
        axis.scatter([], [], marker="o", color=COLORS[strategy], label=LABELS[strategy])
    for scenario, marker in markers.items():
        axis.scatter([], [], marker=marker, color="#333333", label=scenario)
    axis.set_xlabel("Migration overhead (bytes / payload bytes)")
    axis.set_ylabel("Service interruption (%)")
    axis.set_title("Stress matrix: continuity vs. overhead")
    axis.grid(alpha=0.3)
    axis.legend(fontsize=7, ncol=2)
    figure.tight_layout()
    figure.savefig(output, dpi=200)
    plt.close(figure)


def critical_speeds(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (scenario, strategy), group in frame.groupby(["scenario", "strategy"]):
        group = group.sort_values("speed_kmh")
        over_one = group[group["duration_over_dwell_mean"] >= 1.0]
        over_one_p95 = group[group["duration_over_dwell_p95"] >= 1.0]
        over_half = group[group["interruption_overall"] >= 0.5]
        rows.append(
            {
                "scenario": scenario,
                "strategy": strategy,
                "first_speed_duration_over_dwell_ge_1": over_one["speed_kmh"].min() if not over_one.empty else None,
                "first_speed_duration_over_dwell_p95_ge_1": over_one_p95["speed_kmh"].min()
                if not over_one_p95.empty
                else None,
                "first_speed_interruption_ge_50pct": over_half["speed_kmh"].min() if not over_half.empty else None,
            }
        )
    return pd.DataFrame(rows)


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default="results/stress_sf")
    parser.add_argument("--duration", type=int, default=1800)
    parser.add_argument("--plot-only", action="store_true", help="reuse stress_summary.csv")
    args = parser.parse_args()

    output = Path(args.out)
    output.mkdir(parents=True, exist_ok=True)
    partial = output / "stress_summary.partial.csv"

    rows = []
    start = time.time()
    total = len(SCENARIOS) * len(SPEEDS) * len(STRATEGIES)
    done = 0

    if args.plot_only:
        frame = pd.read_csv(output / "stress_summary.csv")
        rows = frame.to_dict("records")
    else:
        for scenario, bandwidth, vehicles in SCENARIOS:
            for speed in SPEEDS:
                for strategy in STRATEGIES:
                    config = load_config("configs/sf_taxi.yaml")
                    config.topology.link_bandwidth_mbps = bandwidth
                    config.mobility.vehicles = vehicles
                    config.mobility.speed_kmh = speed
                    config.simulation.duration_steps = args.duration
                    config.migration.strategy = strategy
                    config.output.directory = str(output)
                    config.output.tag = f"{scenario}__{strategy}__v{speed:g}"

                    result = run_experiment(config, save=True)
                    row = summarize_run(config.output_dir())
                    row["scenario"] = scenario
                    row["bandwidth_mbps"] = bandwidth
                    row["vehicles"] = vehicles
                    rows.append(row)

                    done += 1
                    frame = pd.DataFrame(rows)
                    frame.to_csv(partial, index=False)
                    print(
                    f"[{done}/{total}] {scenario} {bandwidth}Mbps {vehicles}veh "
                    f"{speed:g}km/h {strategy}: "
                    f"interrupt={row['interruption_overall'] * 100:.1f}% "
                    f"dur/dwell={row['duration_over_dwell_mean']} "
                    f"overhead={row['overhead_ratio']} "
                    f"elapsed={time.time() - start:.0f}s",
                    flush=True,
                    )

    frame = pd.DataFrame(rows)
    frame.to_csv(output / "stress_summary.csv", index=False)
    critical_speeds(frame).to_csv(output / "critical_speeds.csv", index=False)

    plot_panels(
        frame,
        "interruption_overall",
        "Service interruption (%)",
        "Interruption vs. speed under each scenario",
        output / "interruption_vs_speed_by_scenario.png",
        percent=True,
    )
    plot_panels(
        frame,
        "duration_over_dwell_mean",
        "Migration duration / cell dwell",
        "Can the migration keep up with the vehicle? (dashed = 1)",
        output / "duration_over_dwell_by_scenario.png",
        hline=1.0,
    )
    plot_panels(
        frame,
        "duration_over_dwell_p95",
        "P95 migration duration / cell dwell",
        "Tail: can the slowest migrations keep up? (dashed = 1)",
        output / "duration_over_dwell_p95_by_scenario.png",
        hline=1.0,
    )
    plot_tradeoff(frame, output / "tradeoff.png")

    print(f"\nwrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
