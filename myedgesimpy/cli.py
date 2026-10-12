"""Command line interface: ``python -m myedgesimpy <command>``."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, Optional, Sequence

from .config import SimulationConfig, load_config
from .services.catalog import CATALOG, get_profiles


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="myedgesimpy",
        description="MEC service-state migration simulator built on EdgeSimPy.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="run a single experiment")
    _add_common(run_parser)
    run_parser.add_argument("--strategy", help="migration strategy preset")
    run_parser.add_argument("--out", help="results directory (overrides config)")
    run_parser.add_argument("--tag", help="run tag (overrides config)")
    run_parser.add_argument("--save-dataset", action="store_true", help="also dump the EdgeSimPy dataset")

    sweep_parser = subparsers.add_parser("sweep", help="run a strategy x speed sweep")
    _add_common(sweep_parser)
    sweep_parser.add_argument("--speeds", default="15,30,45,60", help="comma separated speeds in km/h")
    sweep_parser.add_argument(
        "--strategies",
        default="reactive,reactive_delta,proactive,proactive_delta",
        help="comma separated strategy presets",
    )
    sweep_parser.add_argument("--out", default="results/sweep", help="output directory")

    plot_parser = subparsers.add_parser("plot", help="plot a sweep summary")
    plot_parser.add_argument("--sweep", required=True, help="path to sweep_summary.csv")
    plot_parser.add_argument("--out", help="figures directory")

    services_parser = subparsers.add_parser("services", help="print the MEC service catalogue")
    services_parser.set_defaults(config=None)

    inspect_parser = subparsers.add_parser("inspect", help="print scenario statistics without running")
    _add_common(inspect_parser)

    args = parser.parse_args(argv)

    if args.command == "services":
        return _command_services()
    if args.command == "plot":
        from .analysis import plot_sweep_csv

        written = plot_sweep_csv(args.sweep, args.out)
        for path in written:
            print(f"wrote {path}")
        return 0

    config = _load_and_override(args)

    if args.command == "inspect":
        return _command_inspect(config)
    if args.command == "run":
        return _command_run(config, save_dataset=args.save_dataset)
    if args.command == "sweep":
        return _command_sweep(config, args)
    return 1


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", required=True, help="path to a YAML configuration file")
    parser.add_argument("--speed", type=float, help="vehicle speed in km/h")
    parser.add_argument("--duration", type=int, help="simulation duration in steps")
    parser.add_argument("--vehicles", type=int, help="number of vehicles")


def _load_and_override(args) -> SimulationConfig:
    config = load_config(args.config)
    if getattr(args, "strategy", None):
        config.migration.strategy = args.strategy
    if getattr(args, "speed", None) is not None:
        config.mobility.speed_kmh = float(args.speed)
    if getattr(args, "duration", None) is not None:
        config.simulation.duration_steps = int(args.duration)
    if getattr(args, "vehicles", None) is not None:
        config.mobility.vehicles = int(args.vehicles)
    if getattr(args, "out", None) and args.command == "run":
        config.output.directory = args.out
    if getattr(args, "tag", None):
        config.output.tag = args.tag
    return config


def _command_run(config: SimulationConfig, save_dataset: bool) -> int:
    from .runner import run_experiment

    result = run_experiment(config, save=True, save_dataset_file=save_dataset)
    _print_summary(result.summary)
    print(f"\nArtefacts written to {config.output_dir()}")
    return 0


def _command_sweep(config: SimulationConfig, args) -> int:
    from .runner import run_sweep

    speeds = [float(value) for value in str(args.speeds).split(",") if value.strip()]
    strategies = [value.strip() for value in str(args.strategies).split(",") if value.strip()]
    frame = run_sweep(config, speeds, strategies, args.out)

    columns = [
        "strategy",
        "speed_kmh",
        "handovers",
        "migrations_started",
        "service_interruption_ratio",
        "mean_migration_duration_steps",
        "migration_mb_total",
        "overhead_ratio",
    ]
    available = [column for column in columns if column in frame.columns]
    print(frame[available].to_string(index=False))
    print(f"\nSweep summary written to {Path(args.out) / 'sweep_summary.csv'}")
    return 0


def _command_inspect(config: SimulationConfig) -> int:
    from .scenario import build_scenario

    scenario = build_scenario(config)
    summary = scenario.summary()
    print(json.dumps(summary, indent=2, default=str))
    print("\nVehicles:")
    for trace in scenario.traces[:10]:
        print(
            f"  vehicle {trace.vehicle_id}: start cell {trace.initial_cell}, "
            f"route length {len(trace.route)} cells, {len(trace.handover_steps)} handovers"
        )
    print("\nServices:")
    for profile in scenario.profiles:
        print(
            f"  {profile.key:20s} state={profile.state_mb:6.1f} MB "
            f"(+{profile.state_growth_mb_per_step:.2f} MB/step) image={profile.image_size_mb:6.1f} MB"
        )
    return 0


def _command_services() -> int:
    print(f"{'service':20s} {'state(MB)':>10s} {'growth':>8s} {'image(MB)':>10s} {'CPU':>4s} {'RAM(MB)':>8s}  what the terminal sends")
    for key, profile in CATALOG.items():
        row = profile.as_row()
        print(
            f"{key:20s} {row['state_mb']:10.1f} {row['state_growth_mb_per_step']:8.2f} "
            f"{row['image_size_mb']:10.1f} {row['cpu']:4d} {row['memory_mb']:8d}  {profile.terminal_sends}"
        )
    return 0


def _print_summary(summary) -> None:
    keys = [
        "strategy",
        "speed_kmh",
        "handovers",
        "migrations_started",
        "migrations_completed",
        "service_interruption_ratio",
        "mean_migration_duration_steps",
        "state_mb_total",
        "image_mb_total",
        "overhead_ratio",
        "mean_delay_ms",
        "sla_violation_ratio",
    ]
    print(json.dumps({key: summary.get(key) for key in keys}, indent=2, default=str))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())