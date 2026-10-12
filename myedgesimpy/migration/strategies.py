"""Named migration strategies.

A strategy is the combination of three independent decisions, which is what the study
needs to isolate:

``predictive``
    *When* to migrate. ``False`` (reactive) waits until the vehicle has already changed
    cell and then moves the state. ``True`` (proactive) looks ahead on the vehicle route
    and starts the transfer *before* the handover, so the state is already in place when
    the vehicle arrives.

``delta_state``
    *How much* to move. ``False`` sends the whole session state at every migration.
    ``True`` sends only the bytes that changed since the last migration of that service
    (the "dirty" part of the state).

``availability_model``
    *How* the transfer affects the user. ``stop_and_copy`` keeps EdgeSimPy's native
    semantics: the service is down while its state is in flight, which is the baseline.
    ``pre_copy`` keeps the source serving during the bulk transfer and charges only a
    short ``cutover_steps`` interruption at the end.
"""

from __future__ import annotations

import copy
from typing import Dict

from ..config import MigrationSettings

PRESETS: Dict[str, Dict[str, object]] = {
    # Baseline: migrate after the handover, full state, service down during transfer.
    "reactive": {
        "predictive": False,
        "delta_state": False,
        "availability_model": "stop_and_copy",
    },
    # Same timing as the baseline, but only the state delta is transferred.
    "reactive_delta": {
        "predictive": False,
        "delta_state": True,
        "availability_model": "stop_and_copy",
    },
    # Look-ahead migration with pre-copy (service stays up during bulk transfer).
    "proactive": {
        "predictive": True,
        "delta_state": False,
        "availability_model": "pre_copy",
    },
    # Everything combined.
    "proactive_delta": {
        "predictive": True,
        "delta_state": True,
        "availability_model": "pre_copy",
    },
}


def resolve_strategy(settings: MigrationSettings) -> MigrationSettings:
    """Return a copy of the migration settings with the named preset expanded."""
    resolved = copy.deepcopy(settings)
    if resolved.strategy == "custom":
        return resolved

    if resolved.strategy not in PRESETS:
        raise ValueError(
            f"Unknown migration strategy '{resolved.strategy}'. "
            f"Available: {sorted(PRESETS)} or 'custom'."
        )

    for key, value in PRESETS[resolved.strategy].items():
        setattr(resolved, key, value)
    return resolved