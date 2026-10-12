"""Vehicle mobility: how terminals cross cells and trigger edge-node handovers."""

from .paths import VehicleTrace, build_traces, replay_path
from .taxi import load_taxi_trajectories, trajectories_to_paths

__all__ = [
    "VehicleTrace",
    "build_traces",
    "replay_path",
    "load_taxi_trajectories",
    "trajectories_to_paths",
]