"""Typed configuration objects and YAML loading for the simulator.

All experiment parameters live here so that a whole study can be reproduced from a
single YAML file (see ``configs/``).
"""

from __future__ import annotations

import copy
from dataclasses import MISSING, asdict, dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


# --------------------------------------------------------------------------------------
# Settings groups
# --------------------------------------------------------------------------------------
@dataclass
class SimulationSettings:
    """Time base of the simulation."""

    seed: int = 42
    tick_seconds: float = 1.0
    duration_steps: int = 1800
    warmup_steps: int = 0


@dataclass
class ServerProfile:
    """Capacity of every edge server attached to a base station."""

    model_name: str = "mec-standard"
    cpu: int = 128
    memory_mb: int = 262144
    disk_mb: int = 2097152
    max_concurrent_layer_downloads: int = 4


@dataclass
class TopologySettings:
    """Edge infrastructure geometry and link characteristics."""

    # "grid"  -> synthetic N x M cellular grid (default, fully reproducible)
    # "sites" -> real base-station sites (e.g. DATA7) loaded from a CSV file
    source: str = "grid"
    grid_x: int = 6
    grid_y: int = 6

    # Link delay in milliseconds (used directly by EdgeSimPy's path delay).
    link_delay_ms: float = 5.0
    # Link bandwidth in Mbps; converted to "MB per simulation step" when building the dataset.
    link_bandwidth_mbps: float = 200.0
    # Wireless (UE <-> base station) one-way delay in milliseconds.
    wireless_delay_ms: float = 2.0

    # Real-site topology (DATA7, or any CSV with id,latitude,longitude columns).
    sites_path: Optional[str] = None
    sites_k_neighbors: int = 3

    server: ServerProfile = field(default_factory=ServerProfile)

    # Base-station cell whose edge server hosts the container registry (image source).
    registry_cell: Optional[list] = None


@dataclass
class MobilitySettings:
    """How vehicles move and how fast."""

    # "synthetic" -> random taxi-like trips over the grid (default)
    # "taxi"      -> real taxi traces (Rome / San Francisco)
    source: str = "synthetic"
    dataset: str = "synthetic"  # "synthetic" | "rome" | "sf"
    dataset_path: Optional[str] = None

    vehicles: int = 12
    speed_kmh: float = 40.0
    cell_size_m: float = 500.0

    # Synthetic trip generation
    trip_min_cells: int = 3
    trip_max_cells: int = 8


@dataclass
class ServiceSettings:
    """Which MEC services are enabled and how their state evolves."""

    enabled: List[str] = field(
        default_factory=lambda: [
            "navigation",
            "infotainment",
            "alert",
            "traffic_analytics",
        ]
    )
    # Multiplier applied to every service's state growth rate.
    state_growth_factor: float = 1.0


@dataclass
class MigrationSettings:
    """Migration policy knobs (the core of the optimisation study)."""

    # Presets: "reactive", "reactive_delta", "proactive", "proactive_delta", "custom".
    # A preset is expanded into the flags below when the scenario is built.
    strategy: str = "reactive"

    # -- policy flags (set by the preset unless strategy == "custom") ---------------------
    # Start migrating before the handover happens, using a look-ahead on the vehicle path.
    predictive: bool = False
    # Transfer only the state delta accumulated since the last migration of that service.
    delta_state: bool = False
    # "per_node": a delta may only be sent to a node that already holds a valid base
    # snapshot. "global": legacy optimistic model (assumes the target has the base).
    base_model: str = "per_node"
    # Time to apply the received state and restore the service, in milliseconds per MB.
    restore_ms_per_mb: float = 5.0
    # Base maintenance: "none" or "neighbors" (replicate snapshots to adjacent nodes).
    base_maintenance: str = "none"
    base_sync_interval_steps: int = 600
    base_sync_mode: str = "delta"  # "full" | "delta"
    # "stop_and_copy" -> service is down during the whole transfer (baseline).
    # "pre_copy"      -> the source keeps serving during bulk transfer and only a short
    #                    "cutover" window is counted as an interruption.
    availability_model: str = "stop_and_copy"

    # How far ahead (in simulation steps) the policy looks for the next cell.
    lookahead_steps: int = 12
    # Steps of interruption charged for the final cutover under pre_copy.
    cutover_steps: int = 2

    # Skip a migration when the state to move is below this threshold (MB).
    min_transfer_mb: float = 0.0
    # Never migrate stateless services.
    only_stateful: bool = False
    # Refuse a migration when the target server lacks free capacity.
    capacity_guard: bool = True


@dataclass
class MetricsSettings:
    """Measurement configuration."""

    sla_latency_ms: float = 60.0
    sample_every_steps: int = 1
    # Include low-level per-flow records (useful for debugging, heavier to write).
    record_flow_details: bool = False


@dataclass
class OutputSettings:
    """Where results are written."""

    directory: str = "results"
    tag: str = "run"


@dataclass
class SimulationConfig:
    """Aggregates every settings group."""

    simulation: SimulationSettings = field(default_factory=SimulationSettings)
    topology: TopologySettings = field(default_factory=TopologySettings)
    mobility: MobilitySettings = field(default_factory=MobilitySettings)
    services: ServiceSettings = field(default_factory=ServiceSettings)
    migration: MigrationSettings = field(default_factory=MigrationSettings)
    metrics: MetricsSettings = field(default_factory=MetricsSettings)
    output: OutputSettings = field(default_factory=OutputSettings)

    # -- derived quantities --------------------------------------------------------------
    def speed_mps(self) -> float:
        return max(self.mobility.speed_kmh, 1e-9) * 1000.0 / 3600.0

    def ticks_per_cell(self) -> float:
        """Steps a vehicle needs to cross one cell at the configured speed."""
        return max(1.0, self.mobility.cell_size_m / self.speed_mps() / self.simulation.tick_seconds)

    def link_bandwidth_mb_per_step(self) -> float:
        """Convert link bandwidth to 'MB transferred per simulation step'."""
        return self.topology.link_bandwidth_mbps * self.simulation.tick_seconds / 8.0

    # -- (de)serialisation ---------------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SimulationConfig":
        return _merge_dataclass(cls, data or {})

    def copy(self) -> "SimulationConfig":
        return copy.deepcopy(self)

    def output_dir(self) -> Path:
        return Path(self.output.directory) / self.output.tag


def _merge_dataclass(cls, data: Dict[str, Any]):
    """Build a dataclass instance from a (possibly partial) nested dictionary."""
    kwargs: Dict[str, Any] = {}
    for f in fields(cls):
        if f.name not in data:
            continue
        value = data[f.name]
        if isinstance(value, dict):
            nested = None
            if f.default_factory is not MISSING:  # type: ignore[comparison-overlap]
                nested = f.default_factory()
            elif f.default is not MISSING and is_dataclass(f.default):
                nested = f.default
            if nested is not None and is_dataclass(nested):
                kwargs[f.name] = _merge_dataclass(type(nested), value)
                continue
        kwargs[f.name] = value
    return cls(**kwargs)


def load_config(path: str | Path) -> SimulationConfig:
    """Load a :class:`SimulationConfig` from a YAML file."""
    with open(path, "r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return SimulationConfig.from_dict(data)


def save_config(config: SimulationConfig, path: str | Path) -> None:
    """Persist a configuration to YAML (used for run reproducibility)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        yaml.safe_dump(config.to_dict(), handle, sort_keys=False)
