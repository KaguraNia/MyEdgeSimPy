"""Post-hoc metrics derived from a run's CSV artefacts.

Every metric here is meant to support a decision:

===============  ==========================================================
metric           decision it informs
===============  ==========================================================
per-service      which services are worth migrating
interruption
migration bytes  who dominates the cost
lead time        how early to start migrating
ready-before     whether the migration beats the handover
post-arrival lag how long the user is still catching up after arrival
duration/dwell   whether the system can keep up at this speed
redundant rate   which migrations are wasted (stale target / ping-pong)
===============  ==========================================================
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from ..config import load_config
from ..services.catalog import get_profiles


def _load(run_directory: Path) -> Tuple[Dict[str, Any], Any, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    summary = json.loads((run_directory / "summary.json").read_text(encoding="utf-8"))
    config = load_config(run_directory / "config.yaml")
    migrations = pd.read_csv(run_directory / "migrations.csv")
    handovers = pd.read_csv(run_directory / "handovers.csv")
    service_path = run_directory / "service_timeseries.csv"
    services = pd.read_csv(service_path) if service_path.exists() and service_path.stat().st_size > 0 else pd.DataFrame()
    return summary, config, migrations, handovers, services


def _handovers_by_vehicle(handovers: pd.DataFrame) -> Dict[int, List[Tuple[int, int, int]]]:
    grouped: Dict[int, List[Tuple[int, int, int]]] = {}
    for row in handovers.itertuples(index=False):
        grouped.setdefault(int(row.vehicle_id), []).append(
            (int(row.step), int(row.source_cell), int(row.target_cell))
        )
    for events in grouped.values():
        events.sort()
    return grouped


def _migration_flags(
    migrations: pd.DataFrame,
    handovers: pd.DataFrame,
) -> pd.DataFrame:
    """Attach the handover served by each migration and flag wasted migrations."""
    by_vehicle = _handovers_by_vehicle(handovers)

    target_steps: List[Optional[int]] = []
    next_steps: List[Optional[int]] = []
    for row in migrations.itertuples():
        events = by_vehicle.get(int(row.vehicle_id), [])
        candidates = [event for event in events if event[1] == row.origin_cell and event[2] == row.target_cell]
        if not candidates:
            target_steps.append(None)
            next_steps.append(None)
            continue
        target = min(candidates, key=lambda event: abs(event[0] - row.start_step))
        target_steps.append(target[0])
        future = [event[0] for event in events if event[0] > target[0]]
        next_steps.append(min(future) if future else None)

    frame = migrations.copy()
    frame["target_handover_step"] = target_steps
    frame["next_handover_step"] = next_steps
    frame["lead"] = frame["start_step"] - frame["target_handover_step"]
    frame["ready_before"] = (frame["end_step"] <= frame["target_handover_step"]).fillna(False)
    frame["post_arrival_lag"] = (frame["end_step"] - frame["target_handover_step"]).clip(lower=0)
    frame["state_start_step"] = (
        frame["start_step"] + frame["waiting_steps"].fillna(0) + frame["pulling_steps"].fillna(0)
    )
    frame["incomplete"] = frame["end_step"].isna()
    frame["stale_target"] = (
        frame["next_handover_step"].notna()
        & frame["end_step"].notna()
        & (frame["end_step"] > frame["next_handover_step"])
    )

    # A "ping-pong" is a reverse migration that starts *before the previous migration
    # could finish*. A taxi legitimately driving A -> B -> A is not counted: only a
    # bounce that gains the user nothing is waste.
    pingpong = pd.Series(False, index=frame.index)
    for _, group in frame.groupby(["vehicle_id", "service_key"], sort=False):
        previous = None
        for index, row in group.sort_values("start_step").iterrows():
            previous_duration = previous["duration"] if previous is not None else None
            if (
                previous is not None
                and row["origin_cell"] == previous["target_cell"]
                and row["target_cell"] == previous["origin_cell"]
                and pd.notna(previous_duration)
                and row["start_step"] - previous["start_step"] <= max(1.0, float(previous_duration))
            ):
                pingpong.loc[index] = True
            previous = row
    frame["pingpong"] = pingpong
    # ``incomplete`` here means "still in flight when the simulation ended"; it is a
    # censoring artefact, not waste, so it is reported separately.
    frame["redundant"] = frame[["stale_target", "pingpong"]].any(axis=1)
    return frame


def _concurrency_stats(
    migrations: pd.DataFrame,
    start_column: str,
    end_column: str,
    duration_steps: int,
) -> Tuple[Optional[float], Optional[int]]:
    """Mean (over all simulated steps) and peak number of concurrent migrations."""
    active: Dict[int, int] = {}
    for row in migrations.itertuples():
        start = int(getattr(row, start_column))
        end = getattr(row, end_column)
        if pd.isna(end):
            duration = getattr(row, "duration")
            end = start + (int(duration) if pd.notna(duration) else 0)
        end = int(end)
        if end < start:
            continue
        for step in range(start, end + 1):
            active[step] = active.get(step, 0) + 1
    if not active:
        return None, None
    mean = sum(active.values()) / max(1, int(duration_steps))
    return round(mean, 3), max(active.values())


def summarize_run(run_directory: str | Path) -> Dict[str, Any]:
    """Compute the flat metric row for one saved run."""
    run_directory = Path(run_directory)
    payload, config, migrations, handovers, services = _load(run_directory)
    summary = payload["summary"]
    dwell = config.ticks_per_cell()
    frame = _migration_flags(migrations, handovers)
    durations = frame["duration"].dropna()
    concurrent_mean, concurrent_peak = _concurrency_stats(
        frame, "start_step", "end_step", summary["duration_steps"]
    )
    state_concurrent_mean, state_concurrent_peak = _concurrency_stats(
        frame, "state_start_step", "end_step", summary["duration_steps"]
    )

    row: Dict[str, Any] = {
        "dataset": config.mobility.dataset if config.mobility.source in {"taxi", "data7"} else "synthetic",
        "source": config.mobility.source,
        "strategy": summary["strategy"],
        "speed_kmh": summary["speed_kmh"],
        "vehicles": summary["vehicles"],
        "handovers": summary["handovers"],
        "migrations": len(frame),
        "migrations_per_handover": round(len(frame) / summary["handovers"], 3) if summary["handovers"] else None,
        "migration_mb": summary["migration_mb_total"],
        "base_sync_mb": summary.get("base_sync_mb_total", 0.0),
        "total_transfer_mb": summary.get("total_transfer_mb", summary["migration_mb_total"]),
        "overhead_ratio": summary["overhead_ratio"],
        "interruption_overall": summary["service_interruption_ratio"],
        "lead_mean_steps": round(float(frame["lead"].mean()), 2) if frame["lead"].notna().any() else None,
        "ready_before_handover_pct": round(100.0 * float(frame["ready_before"].mean()), 2),
        "post_arrival_lag_mean_steps": round(float(frame["post_arrival_lag"].mean()), 2),
        "post_arrival_lag_p95_steps": round(float(frame["post_arrival_lag"].quantile(0.95)), 2),
        "duration_over_dwell_mean": round(float(durations.mean() / dwell), 4) if len(durations) else None,
        "duration_over_dwell_p95": round(float(durations.quantile(0.95) / dwell), 4) if len(durations) else None,
        "pingpong_rate": round(float(frame["pingpong"].mean()), 4),
        "stale_target_rate": round(float(frame["stale_target"].mean()), 4),
        "unfinished_rate": round(float(frame["incomplete"].mean()), 4),
        "redundant_rate": round(float(frame["redundant"].mean()), 4),
        "cold_target_rate": round(float(frame["cold_target"].mean()), 4) if "cold_target" in frame else None,
        "restore_steps_mean": round(float(frame["restore_steps"].mean()), 3) if "restore_steps" in frame else None,
        # -- Step 3: resource-time and concurrency ------------------------------------
        "bandwidth_time_mb_s": round(
            float(
                (frame["state_mb"] * frame["state_steps"].fillna(0)).sum()
                + (frame["image_pull_mb"].fillna(0) * frame["pulling_steps"].fillna(0)).sum()
            ),
            1,
        ),
        "bandwidth_time_per_handover": round(
            float(
                (frame["state_mb"] * frame["state_steps"].fillna(0)).sum()
                + (frame["image_pull_mb"].fillna(0) * frame["pulling_steps"].fillna(0)).sum()
            )
            / max(1, summary["handovers"]),
            1,
        ),
        "concurrent_mean": concurrent_mean,
        "concurrent_peak": concurrent_peak,
        "state_concurrent_mean": state_concurrent_mean,
        "state_concurrent_peak": state_concurrent_peak,
        "control_plane_flows": int(len(frame) + frame.get("layer_flows", pd.Series(dtype=float)).fillna(0).sum()),
        "control_plane_flows_per_handover": round(
            (len(frame) + frame.get("layer_flows", pd.Series(dtype=float)).fillna(0).sum())
            / max(1, summary["handovers"]),
            3,
        ),
        "waiting_ratio_mean": round(
            float((frame["waiting_steps"].fillna(0) / frame["duration"].replace(0, pd.NA)).mean()), 4
        ),
        "pulling_ratio_mean": round(
            float((frame["pulling_steps"].fillna(0) / frame["duration"].replace(0, pd.NA)).mean()), 4
        ),
        "state_ratio_mean": round(
            float((frame["state_steps"].fillna(0) / frame["duration"].replace(0, pd.NA)).mean()), 4
        ),
    }

    if not services.empty:
        per_service = services.groupby("service_key")["interrupted"].mean()
        for key, value in per_service.items():
            row[f"interrupt_{key}"] = round(float(value), 4)

    profiles = {profile.key: profile for profile in get_profiles(config.services.enabled, config.services.state_growth_factor)}
    bytes_by_service = frame.groupby("service_key").apply(
        lambda group: float(group["state_mb"].sum() + group["image_pull_mb"].sum()), include_groups=False
    )
    for key, value in bytes_by_service.items():
        row[f"mb_{key}"] = round(float(value), 1)
        profile = profiles.get(key)
        if profile is not None:
            payload_mb = profile.payload_kb_per_step * summary["vehicles"] * summary["duration_steps"] / 1024.0
            row[f"overhead_{key}"] = round(float(value) / payload_mb, 3) if payload_mb else None

    return row


def summarize_tree(root: str | Path) -> pd.DataFrame:
    """Summarise every run directory found under ``root``."""
    root = Path(root)
    rows = []
    # Sweeps write ``root/<strategy>_v<speed>/summary.json``; a plain results folder may
    # nest one more level. Accept both layouts.
    summary_files = sorted(set(root.glob("*/summary.json")) | set(root.glob("*/*/summary.json")))
    for summary_file in summary_files:
        run_directory = summary_file.parent
        if not (run_directory / "migrations.csv").exists():
            continue
        try:
            rows.append(summarize_run(run_directory))
        except Exception as error:  # noqa: BLE001 - keep going, report the bad run
            print(f"[skip] {run_directory}: {type(error).__name__}: {error}")
    return pd.DataFrame(rows)


def per_service_table(root: str | Path) -> pd.DataFrame:
    """Long table: one row per (dataset, strategy, service)."""
    frame = summarize_tree(root)
    rows = []
    for _, row in frame.iterrows():
        for column in frame.columns:
            if not column.startswith("interrupt_"):
                continue
            service = column[len("interrupt_") :]
            rows.append(
                {
                    "dataset": row["dataset"],
                    "strategy": row["strategy"],
                    "speed_kmh": row["speed_kmh"],
                    "service": service,
                    "interruption": row.get(f"interrupt_{service}"),
                    "migration_mb": row.get(f"mb_{service}"),
                    "overhead_ratio": row.get(f"overhead_{service}"),
                }
            )
    return pd.DataFrame(rows)
