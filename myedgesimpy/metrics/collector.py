"""Collects the metrics the study cares about.

Two families of metrics are produced:

**Continuity (the user's experience)**
    * service interruption: fraction of vehicle-steps in which at least one MEC service of
      the vehicle was not available,
    * total downtime experienced by the fleet,
    * end-to-end request delay (and its violations of the delay SLA).

**Cost (the operator's bill)**
    * number of migrations and their latency breakdown (queueing, image pulling, state),
    * bytes moved for state and for image layers,
    * network utilisation, used as a proxy for control-plane overhead,
    * overhead ratio = migration bytes / application payload bytes.

**Observable side-channel (ground truth for the security study)**
    Every migration is logged as ``(step, source node, target node, bytes)``. That is
    precisely the information an external attacker could observe, so the security phase can
    replay trajectory-inference attacks directly on this log.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from edge_sim_py.components import NetworkFlow, NetworkLink, Service, User

from ..config import SimulationConfig
from ..scenario.builder import Scenario


@dataclass
class MetricsCollector:
    """Per-step sampler plus the end-of-run aggregation."""

    scenario: Scenario
    config: SimulationConfig
    controller: Any

    step_samples: List[Dict[str, Any]] = field(default_factory=list)
    handovers: List[Dict[str, Any]] = field(default_factory=list)
    flows: Dict[int, Dict[str, Any]] = field(default_factory=dict)

    _last_cell: Dict[int, Optional[int]] = field(default_factory=dict)
    _bound: bool = False

    # ----------------------------------------------------------------------------------
    # EdgeSimPy hook (called through MECSimulator.monitor)
    # ----------------------------------------------------------------------------------
    def bind(self) -> None:
        for user in User.all():
            self._last_cell[user.id] = user.base_station.id if user.base_station else None
        self._bound = True

    def sample(self, sim) -> None:
        step = int(sim.schedule.steps)
        if not self._bound:
            self.bind()

        # Let the policy re-assert availability now that the agents have been activated.
        self.controller.post_step()

        self._track_handovers(step)
        self._track_flows(step)

        every = max(1, int(self.config.metrics.sample_every_steps))
        if step % every != 0:
            return

        users = list(User.all())
        services = list(Service.all())

        unavailable = [service for service in services if not getattr(service, "_available", True)]
        servers_with_unavailable = {self._server_of(service) for service in unavailable}

        interrupted_vehicles = 0
        delays: List[float] = []
        sla_violations = 0
        sla = float(self.config.metrics.sla_latency_ms)

        for user in users:
            interrupted = any(
                not getattr(service, "_available", True)
                for application in user.applications
                for service in application.services
            )
            if interrupted:
                # A service that is not available has an infinite response delay, so it
                # always violates the delay SLA.
                interrupted_vehicles += 1
                sla_violations += 1
                continue

            for application in user.applications:
                value = user.delays.get(str(application.id))
                if value is None:
                    continue
                if isinstance(value, float) and (value == float("inf") or value != value):
                    sla_violations += 1
                    continue
                delays.append(float(value))
                if value > sla:
                    sla_violations += 1

        migrations_in_flight = sum(1 for service in services if service.being_provisioned)

        state_flows = 0
        layer_flows = 0
        bytes_in_flight = 0.0
        for flow in NetworkFlow.all():
            if flow.status != "active":
                continue
            flow_type = flow.metadata.get("type")
            if flow_type == "service_state":
                state_flows += 1
            elif flow_type == "layer":
                layer_flows += 1
            bytes_in_flight += float(flow.data_to_transfer or 0.0)

        links = list(NetworkLink.all())
        link_capacity = sum(float(link["bandwidth"]) for link in links) or 1.0
        link_demand = sum(float(link["bandwidth_demand"]) for link in links)

        self.step_samples.append(
            {
                "step": step,
                "vehicles": len(users),
                "services": len(services),
                "services_unavailable": len(unavailable),
                "servers_with_unavailable": len(servers_with_unavailable),
                "vehicles_interrupted": interrupted_vehicles,
                "migrations_in_flight": migrations_in_flight,
                "state_flows_active": state_flows,
                "layer_flows_active": layer_flows,
                "bytes_in_flight_mb": round(bytes_in_flight, 4),
                "mean_delay_ms": round(sum(delays) / len(delays), 3) if delays else None,
                "max_delay_ms": round(max(delays), 3) if delays else None,
                "sla_violations": sla_violations,
                "link_utilisation": round(link_demand / link_capacity, 5),
            }
        )

    # ----------------------------------------------------------------------------------
    # Internals
    # ----------------------------------------------------------------------------------
    def _track_handovers(self, step: int) -> None:
        for user in User.all():
            base_station = user.base_station
            current = base_station.id if base_station else None
            previous = self._last_cell.get(user.id)
            if previous is not None and current is not None and current != previous:
                self.handovers.append(
                    {
"step": step,
                        "vehicle_id": user.id,
                        "source_cell": previous,
                        "target_cell": current,
                    }
                )
            self._last_cell[user.id] = current

    def _track_flows(self, step: int) -> None:
        for flow in NetworkFlow.all():
            if flow.id in self.flows:
                continue
            self.flows[flow.id] = {
                "flow_id": flow.id,
                "type": flow.metadata.get("type"),
                "service_id": getattr(flow.metadata.get("object"), "id", None),
                "start": flow.start,
                "seen_at_step": step,
                "data_mb": float(flow.data_to_transfer),
                "source": getattr(flow.source, "id", None),
                "target": getattr(flow.target, "id", None),
            }

    @staticmethod
    def _server_of(service) -> Optional[int]:
        return service.server.id if service.server else None

    # ----------------------------------------------------------------------------------
    # Aggregation
    # ----------------------------------------------------------------------------------
    def finalize(self, duration_steps: int) -> Dict[str, Any]:
        events = self.controller.events
        completed = [event for event in events if event.get("end_step") is not None]

        durations = [event["duration"] for event in completed]
        state_steps = [event.get("state_steps", 0) for event in completed]
        pulling_steps = [event.get("pulling_steps", 0) for event in completed]

        state_bytes = sum(event["state_mb"] for event in events)
        image_bytes = sum(event.get("image_pull_mb", 0.0) for event in events)

        payload_kb_per_step = sum(
            profile.payload_kb_per_step for profile in self.scenario.profiles
        )
        vehicles = len(self.scenario.traces)
        payload_mb = payload_kb_per_step * vehicles * duration_steps / 1024.0

        total_vehicle_steps = max(1, vehicles * duration_steps)
        interrupted_steps = sum(sample["vehicles_interrupted"] for sample in self.step_samples)
        unavailable_service_steps = sum(sample["services_unavailable"] for sample in self.step_samples)

        delays = [sample["mean_delay_ms"] for sample in self.step_samples if sample["mean_delay_ms"] is not None]
        sla_violations = sum(sample["sla_violations"] for sample in self.step_samples)

        handovers_per_vehicle = (
            len(self.handovers) / vehicles if vehicles else 0.0
        )
        minutes = max(1e-9, duration_steps * self.config.simulation.tick_seconds / 60.0)

        summary = {
            "strategy": self.controller.settings.strategy,
            "speed_kmh": self.config.mobility.speed_kmh,
            "duration_steps": duration_steps,
            "vehicles": vehicles,
            "cells": self.scenario.layout.size,
            "services": len(self.scenario.service_index),
            # -- continuity --
            "handovers": len(self.handovers),
            "handovers_per_vehicle": round(handovers_per_vehicle, 3),
            "migrations_started": len(events),
            "migrations_completed": len(completed),
            "service_interruption_ratio": round(interrupted_steps / total_vehicle_steps, 6),
            "unavailable_service_ratio": round(
                unavailable_service_steps / max(1, len(self.scenario.service_index) * duration_steps), 6
            ),
            "mean_delay_ms": round(sum(delays) / len(delays), 3) if delays else None,
            "sla_violation_ratio": round(sla_violations / total_vehicle_steps, 6),
            # -- cost --
            "mean_migration_duration_steps": round(sum(durations) / len(durations), 3) if durations else None,
            "p95_migration_duration_steps": round(_percentile(durations, 95), 3) if durations else None,
            "mean_state_transfer_steps": round(sum(state_steps) / len(state_steps), 3) if state_steps else None,
            "mean_layer_pull_steps": round(sum(pulling_steps) / len(pulling_steps), 3) if pulling_steps else None,
            "state_mb_total": round(state_bytes, 3),
            "image_mb_total": round(image_bytes, 3),
            "migration_mb_total": round(state_bytes + image_bytes, 3),
            "payload_mb_total": round(payload_mb, 3),
            "overhead_ratio": round((state_bytes + image_bytes) / payload_mb, 6) if payload_mb > 0 else None,
            "mean_link_utilisation": round(
                sum(sample["link_utilisation"] for sample in self.step_samples) / max(1, len(self.step_samples)), 6
            ),
            "migrations_denied_capacity": self.controller.counters.get("migrations_denied_capacity", 0),
            "migrations_skipped_small_delta": self.controller.counters.get("migrations_skipped_small_delta", 0),
            "migrations_per_vehicle_minute": round(len(events) / vehicles / minutes, 4) if vehicles else None,
        }
        return summary

    # ----------------------------------------------------------------------------------
    def observable_trace(self) -> List[Dict[str, Any]]:
        """What an attacker could see: when a migration happened and between which nodes."""
        return sorted(
            (
                {
                    "step": event["start_step"],
                    "source_node": event["origin_cell"],
                    "target_node": event["target_cell"],
                    "bytes": round(event["state_mb"], 3),
                }
                for event in self.controller.events
            ),
            key=lambda entry: entry["step"],
        )


def _percentile(values: List[float], percentile: float) -> float:
    if not values:
        return float("nan")
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(round((percentile / 100.0) * (len(ordered) - 1))))
    return ordered[index]