"""Run one migration experiment end-to-end.

Pipeline: configuration -> scenario (topology + mobility + services) -> EdgeSimPy model
-> migration controller -> metrics -> artefacts on disk.

The simulator is a thin subclass of EdgeSimPy's ``Simulator`` that replaces the default
monitoring routine with the domain-specific :class:`MetricsCollector`. Everything else
(time model, agent activation order, network flow scheduling) stays exactly as EdgeSimPy
implements it.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from edge_sim_py import Simulator

from ..config import SimulationConfig, save_config
from ..metrics import MetricsCollector
from ..migration import MigrationController
from ..scenario import Scenario, build_scenario, save_dataset


class MECSimulator(Simulator):
    """EdgeSimPy simulator whose monitoring hook feeds our metrics collector."""

    def __init__(self, collector: Optional[MetricsCollector] = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._collector = collector

    def monitor(self) -> None:  # noqa: D102 - overrides EdgeSimPy's monitoring
        if self._collector is not None:
            self._collector.sample(self)


@dataclass
class ExperimentResult:
    """Everything a single run produces."""

    summary: Dict[str, Any]
    step_samples: List[Dict[str, Any]]
    migrations: List[Dict[str, Any]]
    handovers: List[Dict[str, Any]]
    denials: List[Dict[str, Any]]
    observable_trace: List[Dict[str, Any]]
    scenario_summary: Dict[str, Any]
    config: Dict[str, Any]
    scenario: Optional[Scenario] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.summary,
            "scenario": self.scenario_summary,
            "config": self.config,
            "migrations": self.migrations,
            "handovers": self.handovers,
            "denials": self.denials,
            "observable_trace": self.observable_trace,
        }

    def save(self, directory: str | Path, save_dataset_file: bool = False) -> Path:
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)

        with open(directory / "summary.json", "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "summary": self.summary,
                    "scenario": self.scenario_summary,
                    "config": self.config,
                },
                handle,
                indent=2,
                default=str,
            )

        with open(directory / "observable_migration_trace.json", "w", encoding="utf-8") as handle:
            json.dump(self.observable_trace, handle, indent=2, default=str)

        _write_csv(directory / "metrics_timeseries.csv", self.step_samples)
        _write_csv(directory / "migrations.csv", self.migrations)
        _write_csv(directory / "handovers.csv", self.handovers)
        _write_csv(directory / "capacity_denials.csv", self.denials)

        config_path = directory / "config.yaml"
        if self.scenario is not None:
            save_config(self.scenario.config, config_path)
            if save_dataset_file:
                save_dataset(self.scenario.dataset, directory / "dataset.json")
        return directory


def _write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    import pandas as pd

    if not rows:
        path.write_text("", encoding="utf-8")
        return
    pd.DataFrame(rows).to_csv(path, index=False)


def run_experiment(
    config: SimulationConfig,
    *,
    save: bool = True,
    save_dataset_file: bool = False,
) -> ExperimentResult:
    """Build the scenario, run the simulation and return the measured results."""
    random.seed(config.simulation.seed)

    scenario = build_scenario(config)
    controller = MigrationController(scenario)
    collector = MetricsCollector(scenario=scenario, config=config, controller=controller)

    duration = int(config.simulation.duration_steps)
    simulator = MECSimulator(
        collector=collector,
        tick_duration=config.simulation.tick_seconds,
        tick_unit="seconds",
        stopping_criterion=lambda model: model.schedule.steps >= duration,
        resource_management_algorithm=controller,
        resource_management_algorithm_parameters={"controller": controller},
        dump_interval=float("inf"),
    )

    simulator.initialize(input_file=scenario.dataset)
    collector.bind()
    simulator.run_model()

    summary = collector.finalize(duration_steps=duration)
    summary["strategy_summary"] = controller.summary()

    result = ExperimentResult(
        summary=summary,
        step_samples=collector.step_samples,
        migrations=controller.events,
        handovers=collector.handovers,
        denials=controller.denials,
        observable_trace=collector.observable_trace(),
        scenario_summary=scenario.summary(),
        config=config.to_dict(),
        scenario=scenario,
    )

    if save:
        result.save(config.output_dir(), save_dataset_file=save_dataset_file)
    return result