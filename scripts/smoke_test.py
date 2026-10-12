"""End-to-end smoke test.

Builds a small scenario, runs the four migration strategies and checks the invariants the
prototype relies on. Run it after every change:

    python scripts/smoke_test.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from myedgesimpy.config import load_config  # noqa: E402
from myedgesimpy.runner import run_experiment  # noqa: E402
from myedgesimpy.scenario import build_scenario  # noqa: E402

VALID_COMPONENT_KEYS = {
    "NetworkSwitch",
    "NetworkLink",
    "BaseStation",
    "EdgeServer",
    "ContainerLayer",
    "ContainerImage",
    "ContainerRegistry",
    "Service",
    "Application",
    "User",
    "RandomDurationAndIntervalAccessPattern",
}


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"  ok  {message}")


def main() -> int:
    config = load_config(REPO_ROOT / "configs" / "small.yaml")
    config.simulation.duration_steps = 240

    print("1. scenario construction")
    scenario = build_scenario(config)
    check(set(scenario.dataset.keys()) == VALID_COMPONENT_KEYS, "dataset exposes only valid EdgeSimPy components")
    check(len(scenario.service_index) == config.mobility.vehicles * len(config.services.enabled), "one service per (vehicle, service)")
    check(all(len(t.cells) == config.simulation.duration_steps + 1 for t in scenario.traces), "every vehicle has a per-step cell trace")
    check(all(len(t.handover_steps) > 0 for t in scenario.traces), "every vehicle crosses at least one cell")
    check(len(scenario.dataset["EdgeServer"]) == scenario.layout.size, "one edge server per cell")

    print("2. running the strategies")
    results = {}
    for strategy in ("reactive", "reactive_delta", "proactive", "proactive_delta"):
        run_config = config.copy()
        run_config.migration.strategy = strategy
        results[strategy] = run_experiment(run_config, save=False).summary
        check(results[strategy]["migrations_started"] > 0, f"{strategy}: migrations were triggered")

    baseline = results["reactive"]
    delta = results["reactive_delta"]
    proactive = results["proactive"]

    print("3. invariants of the optimisation")
    check(
        delta["migration_mb_total"] < baseline["migration_mb_total"],
        "delta state transfers fewer bytes than full state",
    )
    check(
        proactive["service_interruption_ratio"] <= baseline["service_interruption_ratio"],
        "proactive + pre-copy does not increase interruptions",
    )
    check(
        baseline["sla_violation_ratio"] >= baseline["service_interruption_ratio"] - 1e-9,
        "SLA violations are at least as frequent as interruptions",
    )

    print("\nsummary")
    for strategy, summary in results.items():
        print(
            f"  {strategy:18s} interruption={summary['service_interruption_ratio'] * 100:6.2f}%  "
            f"migrated={summary['migration_mb_total']:10.1f} MB  "
            f"overhead={summary['overhead_ratio']:.2f}x"
        )

    print("\nALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())