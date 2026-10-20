"""The migration controller: the policy that EdgeSimPy calls at every simulation step.

EdgeSimPy invokes ``resource_management_algorithm(parameters)`` once per step, before the
agents are activated. That is the natural place to decide which service should be
provisioned or migrated, which is exactly what this controller does.

Responsibilities
----------------
1. Keep every service's ``state`` attribute in sync with the state-growth model.
2. Pick, for every vehicle, the edge server that should host its services
   (reactive: the current cell; proactive: the next cell within the look-ahead window).
3. Start migrations, honouring the capacity guard and the minimum-transfer threshold.
4. Apply the availability policy (stop-and-copy vs pre-copy + cutover).
5. Record every migration as an *observable event* (timestamp + source node + target node),
   which is the trace a later security study will try to exploit.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx

from edge_sim_py.components import BaseStation, EdgeServer, NetworkFlow, Service, User

from ..config import MigrationSettings, SimulationConfig
from ..scenario.builder import Scenario
from .strategies import resolve_strategy


class MigrationController:
    """Policy object used as EdgeSimPy's ``resource_management_algorithm``."""

    def __init__(self, scenario: Scenario, config: Optional[SimulationConfig] = None):
        self.scenario = scenario
        self.config = config or scenario.config
        self.settings: MigrationSettings = resolve_strategy(self.config.migration)

        # Runtime state
        self._bound = False
        self._bs_by_coordinates: Dict[tuple, Any] = {}
        self._server_by_cell: Dict[int, Any] = {}
        self._true_state: Dict[int, float] = {}
        self._last_synced: Dict[int, float] = {}
        # (service_id, node_id) -> size of the base snapshot stored on that node
        self._base_state: Dict[Tuple[int, int], float] = {}
        self._active_event: Dict[int, int] = {}
        # Extra steps after a migration completes: apply the state / restore the service
        self._restore_remaining: Dict[int, int] = {}
        self._forced_prev: set = set()
        # Background base-replication flows: flow id -> metadata
        self._base_syncs: Dict[int, Dict[str, Any]] = {}
        # Coordinated (per-vehicle) cutover bookkeeping for pre-copy migration
        self._services_by_vehicle: Dict[int, List[int]] = {}
        self._pending_by_vehicle: Dict[int, set] = defaultdict(set)
        self._vehicle_cutover: Dict[int, int] = {}

        # Results
        self.events: List[Dict[str, Any]] = []
        self.denials: List[Dict[str, Any]] = []
        self.counters: Dict[str, int] = defaultdict(int)

    # ----------------------------------------------------------------------------------
    # EdgeSimPy hook
    # ----------------------------------------------------------------------------------
    def __call__(self, parameters: Dict[str, Any]) -> None:
        step = int(parameters.get("current_step", 1))
        self.run_step(step)

    def run_step(self, step: int) -> None:
        self._bind()
        self._update_service_state(step)
        self._collect_finished_base_syncs()
        self._maybe_sync_bases(step)
        self._apply_availability_policy(charge_cutover=True)
        for service, target in self._select_migrations(step):
            self._start_migration(service, target, step)
        self._collect_finished_migrations(step)

    def post_step(self) -> None:
        """Re-assert the availability policy once EdgeSimPy's agents have run.

        Under pre-copy the bulk transfer must not count as an interruption. The restore
        window must also win over EdgeSimPy marking the service available when the state
        flow finishes. Both decisions happen after this controller has run for the step,
        so the policy is re-applied here without advancing any timer.
        """
        self._apply_availability_policy(charge_cutover=False)

    # ----------------------------------------------------------------------------------
    # Setup / helpers
    # ----------------------------------------------------------------------------------
    def _bind(self) -> None:
        if self._bound:
            return
        self._bs_by_coordinates = {tuple(bs.coordinates): bs for bs in BaseStation.all()}
        for bs in BaseStation.all():
            server = bs.edge_servers[0] if bs.edge_servers else None
            if server is not None:
                self._server_by_cell[bs.id] = server
        for service in Service.all():
            entry = self.scenario.service_index.get(service.id)
            if entry is not None:
                self._true_state[service.id] = entry["initial_state_mb"]
                self._last_synced[service.id] = 0.0
                if service.server is not None:
                    # The initial host already holds a valid base snapshot.
                    self._base_state[(service.id, service.server.id)] = float(service.state)
        for service_id, entry in self.scenario.service_index.items():
            self._services_by_vehicle.setdefault(entry["vehicle_id"], []).append(service_id)
        self._bound = True

    def _server_at(self, coordinates) -> Optional[Any]:
        bs = self._bs_by_coordinates.get(tuple(coordinates))
        if bs is None:
            return None
        return self._server_by_cell.get(bs.id)

    def _profile_of(self, service) -> Any:
        return self.scenario.profile_by_digest.get(service.image_digest)

    # ----------------------------------------------------------------------------------
    # 1. State growth
    # ----------------------------------------------------------------------------------
    def _update_service_state(self, step: int) -> None:
        for service in Service.all():
            profile = self._profile_of(service)
            if profile is None:
                continue
            grown = profile.state_mb + profile.state_growth_mb_per_step * max(0, step - 1)
            self._true_state[service.id] = grown
            if not service.being_provisioned:
                # The service is running normally: its state is simply the grown state.
                service.state = grown

    # ----------------------------------------------------------------------------------
    # 1b. Base maintenance (background replication)
    # ----------------------------------------------------------------------------------
    def _maybe_sync_bases(self, step: int) -> None:
        """Push base snapshots to adjacent nodes on a fixed schedule.

        A snapshot stored on a neighbour makes the next migration to that neighbour a
        warm target (delta instead of full state), but the background transfer itself
        consumes bandwidth and is counted in the overhead.
        """
        if self.settings.base_maintenance == "none":
            return

        interval = max(1, int(self.settings.base_sync_interval_steps))
        if (step - 1) % interval != 0:
            return

        for service in Service.all():
            origin = service.server
            if origin is None or service.being_provisioned:
                continue
            model = getattr(origin, "model", None)
            if model is None or model.topology is None:
                continue
            switch = getattr(origin.base_station, "network_switch", None)
            if switch is None:
                continue

            true_state = float(self._true_state.get(service.id, service.state))
            for neighbor_switch in model.topology.neighbors(switch):
                servers = getattr(neighbor_switch, "edge_servers", [])
                if not servers:
                    continue
                target = servers[0]
                if target.id == origin.id:
                    continue
                if any(
                    info["service_id"] == service.id and info["target_id"] == target.id
                    for info in self._base_syncs.values()
                ):
                    continue

                current_base = self._base_state.get((service.id, target.id))
                if self.settings.base_sync_mode == "delta" and current_base is not None:
                    amount = max(0.0, true_state - current_base)
                else:
                    amount = true_state
                if amount <= 1e-9:
                    continue

                path = nx.shortest_path(G=model.topology, source=switch, target=neighbor_switch)
                flow = NetworkFlow(
                    topology=model.topology,
                    source=origin,
                    target=target,
                    start=step,
                    path=path,
                    data_to_transfer=amount,
                    metadata={"type": "base_sync", "object": service},
                )
                model.initialize_agent(agent=flow)
                self._base_syncs[flow.id] = {
                    "service_id": service.id,
                    "target_id": target.id,
                    "snapshot_mb": true_state,
                    "bytes": amount,
                }
                self.counters["base_sync_started"] += 1
                self.counters["base_sync_mb"] += amount

    def _collect_finished_base_syncs(self) -> None:
        for flow_id, info in list(self._base_syncs.items()):
            flow = NetworkFlow.find_by_id(flow_id)
            if flow is None or flow.status == "finished":
                if flow is not None:
                    self._base_state[(info["service_id"], info["target_id"])] = info["snapshot_mb"]
                    self.counters["base_sync_completed"] += 1
                self._base_syncs.pop(flow_id, None)

    # ----------------------------------------------------------------------------------
    # 2. Availability policy
    # ----------------------------------------------------------------------------------
    def _apply_availability_policy(self, charge_cutover: bool = True) -> None:
        """Apply restore and cutover windows, then pre-copy bulk availability.

        ``charge_cutover=True`` advances the timers by one step; ``False`` only re-applies
        the current decision (used after EdgeSimPy's agents have run).
        """
        cutover_services = set()
        for vehicle_id in self._vehicle_cutover:
            cutover_services.update(self._services_by_vehicle.get(vehicle_id, []))
        forced = cutover_services | set(self._restore_remaining)

        # A service held down last step becomes usable as soon as both windows expire.
        for service_id in self._forced_prev - forced:
            service = Service.find_by_id(service_id)
            if service is not None and not service.being_provisioned:
                service._available = True

        for service_id in forced:
            service = Service.find_by_id(service_id)
            if service is not None:
                service._available = False

        if self.settings.availability_model == "pre_copy":
            # The source keeps serving during the bulk transfer, unless a restore or
            # cutover window explicitly holds the service down.
            for service in Service.all():
                if service.id not in forced and service.being_provisioned and service.server is not None:
                    service._available = True

        self._forced_prev = forced

        if not charge_cutover:
            return

        for service_id in list(self._restore_remaining):
            self._restore_remaining[service_id] -= 1
            if self._restore_remaining[service_id] <= 0:
                del self._restore_remaining[service_id]
        for vehicle_id in list(self._vehicle_cutover):
            self._vehicle_cutover[vehicle_id] -= 1
            if self._vehicle_cutover[vehicle_id] <= 0:
                del self._vehicle_cutover[vehicle_id]

    # ----------------------------------------------------------------------------------
    # 3. Target selection
    # ----------------------------------------------------------------------------------
    def _target_coordinates(self, user, step: int):
        trace = user.coordinates_trace
        if not trace:
            return user.coordinates

        # The user has already moved through indices 0 .. step-2; during this step it
        # will move to index step-1.
        current_index = max(0, min(step - 2, len(trace) - 1))
        current_cell = trace[current_index]

        if not self.settings.predictive:
            return current_cell

        lookahead = max(1, int(self.settings.lookahead_steps))
        for index in range(step - 1, min(len(trace), step - 1 + lookahead)):
            if trace[index] != current_cell:
                return trace[index]
        return current_cell

    def _select_migrations(self, step: int):
        candidates = []
        for user in User.all():
            if not user.applications:
                continue
            target_coordinates = self._target_coordinates(user, step)
            target_server = self._server_at(target_coordinates)
            if target_server is None:
                continue

            for application in user.applications:
                for service in application.services:
                    if service.being_provisioned:
                        continue
                    if service.server is not None and service.server.id == target_server.id:
                        continue

                    profile = self._profile_of(service)
                    if profile is None:
                        continue
                    if self.settings.only_stateful and profile.state_mb <= 0:
                        continue

                    candidates.append((service, target_server))
        return candidates

    # ----------------------------------------------------------------------------------
    # 4. Migration execution
    # ----------------------------------------------------------------------------------
    def _start_migration(self, service, target_server, step: int) -> None:
        profile = self._profile_of(service)
        true_state = self._true_state.get(service.id, getattr(service, "state", 0.0))

        cold_target = False
        base_mb: Optional[float] = None
        if self.settings.delta_state:
            if self.settings.base_model == "per_node":
                base_mb = self._base_state.get((service.id, target_server.id))
                if base_mb is None:
                    # The target has never hosted this service: a delta cannot rebuild it.
                    cold_target = True
                    to_transfer = true_state
                else:
                    to_transfer = max(0.0, true_state - base_mb)
            else:
                synced = self._last_synced.get(service.id, 0.0)
                to_transfer = max(0.0, true_state - synced)
            if to_transfer < self.settings.min_transfer_mb:
                self.counters["migrations_skipped_small_delta"] += 1
                return
        else:
            to_transfer = true_state

        if self.settings.capacity_guard and not target_server.has_capacity_to_host(service=service):
            self.denials.append(
                {
                    "step": step,
                    "service_id": service.id,
                    "vehicle_id": self._vehicle_of(service),
                    "service_key": profile.key if profile else None,
                    "target_server": target_server.id,
                    "reason": "insufficient_capacity",
                }
            )
            self.counters["migrations_denied_capacity"] += 1
            return

        origin_server = service.server
        missing_layers = self._missing_layers(target_server, service)
        image_cached = len(missing_layers) == 0
        image_pull_mb = sum(layer.size_mb for layer in missing_layers)
        if origin_server is not None:
            # The origin holds the live state at the moment the service leaves.
            self._base_state[(service.id, origin_server.id)] = true_state
        restore_ms = to_transfer * max(0.0, float(self.settings.restore_ms_per_mb))
        restore_steps = max(0, int(round(restore_ms / (self.config.simulation.tick_seconds * 1000.0))))
        service.state = to_transfer
        self._last_synced[service.id] = true_state
        service.provision(target_server=target_server)

        event = {
            "index": len(self.events),
            "service_id": service.id,
            "vehicle_id": self._vehicle_of(service),
            "service_key": profile.key if profile else None,
            "start_step": step,
            "end_step": None,
            "duration": None,
            "origin_server": origin_server.id if origin_server else None,
            "target_server": target_server.id,
            "origin_cell": self._cell_of_server(origin_server),
            "target_cell": self._cell_of_server(target_server),
            "state_mb": float(to_transfer),
            "snapshot_state_mb": float(true_state),
            "base_mb": base_mb,
            "cold_target": cold_target,
            "restore_steps": restore_steps,
            "predictive": bool(self.settings.predictive),
            "delta_state": bool(self.settings.delta_state),
            "availability_model": self.settings.availability_model,
            "image_cached": image_cached,
            "image_pull_mb": float(image_pull_mb),
            "layer_flows": len(missing_layers),
        }
        self.events.append(event)
        self._active_event[service.id] = event["index"]
        if cold_target:
            self.counters["migrations_cold_target"] += 1
        elif self.settings.delta_state:
            self.counters["migrations_warm_target"] += 1
        if event["vehicle_id"] is not None:
            self._pending_by_vehicle[event["vehicle_id"]].add(service.id)

    def _collect_finished_migrations(self, step: int) -> None:
        for service_id, event_index in list(self._active_event.items()):
            service = Service.find_by_id(service_id)
            if service is None:
                self._active_event.pop(service_id, None)
                continue
            migrations = service._Service__migrations
            if not migrations:
                continue
            record = migrations[-1]
            if record.get("end") is None:
                continue

            event = self.events[event_index]
            event["end_step"] = record["end"]
            event["duration"] = record["end"] - record["start"]
            event["waiting_steps"] = record.get("waiting_time", 0)
            event["pulling_steps"] = record.get("pulling_layers_time", 0)
            event["state_steps"] = record.get("migrating_service_state_time", 0)
            self._active_event.pop(service_id, None)
            self.counters["migrations_completed"] += 1

            # The target now holds the snapshot that was sent, so it becomes a warm
            # target for the next migration of this service.
            self._base_state[(service_id, event["target_server"])] = event["snapshot_state_mb"]
            if int(event.get("restore_steps", 0)) > 0:
                # Applying the state / restarting the service takes extra steps.
                self._restore_remaining[service_id] = int(event["restore_steps"])

            if self.settings.availability_model == "pre_copy":
                vehicle_id = event.get("vehicle_id")
                if vehicle_id is not None:
                    pending = self._pending_by_vehicle.get(vehicle_id)
                    if pending is not None:
                        pending.discard(service_id)
                        if not pending:
                            self._vehicle_cutover[vehicle_id] = max(0, int(self.settings.cutover_steps))

    # ----------------------------------------------------------------------------------
    # Small helpers
    # ----------------------------------------------------------------------------------
    def _vehicle_of(self, service) -> Optional[int]:
        entry = self.scenario.service_index.get(service.id)
        return entry["vehicle_id"] if entry else None

    @staticmethod
    def _cell_of_server(server) -> Optional[int]:
        if server is None:
            return None
        bs = getattr(server, "base_station", None)
        return bs.id if bs is not None else None

    @staticmethod
    def _image_cached(server, service) -> bool:
        """True when the target node already caches the service image (all layers)."""
        return any(image.digest == service.image_digest for image in server.container_images)

    def _missing_layers(self, target_server, service) -> List[Any]:
        """Layers that still have to be pulled to the target (including queued ones)."""
        profile = self._profile_of(service)
        if profile is None:
            return []
        cached = {layer.digest for layer in target_server.container_layers}
        cached |= {layer.digest for layer in target_server.waiting_queue}
        for flow in target_server.download_queue:
            obj = flow.metadata.get("object")
            if obj is not None and hasattr(obj, "digest"):
                cached.add(obj.digest)
        return [layer for layer in profile.layers if layer.digest not in cached]

    # ----------------------------------------------------------------------------------
    # Reporting
    # ----------------------------------------------------------------------------------
    def summary(self) -> Dict[str, Any]:
        settings = self.settings
        return {
            "strategy": settings.strategy,
            "predictive": settings.predictive,
            "delta_state": settings.delta_state,
            "availability_model": settings.availability_model,
            "lookahead_steps": settings.lookahead_steps,
            "cutover_steps": settings.cutover_steps,
            "migrations_started": len(self.events),
            "migrations_completed": self.counters.get("migrations_completed", 0),
            "migrations_denied_capacity": self.counters.get("migrations_denied_capacity", 0),
            "migrations_skipped_small_delta": self.counters.get("migrations_skipped_small_delta", 0),
            "migrations_cold_target": self.counters.get("migrations_cold_target", 0),
            "migrations_warm_target": self.counters.get("migrations_warm_target", 0),
            "base_sync_started": self.counters.get("base_sync_started", 0),
            "base_sync_completed": self.counters.get("base_sync_completed", 0),
            "base_sync_mb": round(self.counters.get("base_sync_mb", 0.0), 3),
            "restore_steps_total": sum(int(event.get("restore_steps", 0)) for event in self.events),
            "restore_steps_mean": round(
                sum(int(event.get("restore_steps", 0)) for event in self.events) / max(1, len(self.events)), 3
            ),
            "state_mb_requested": round(sum(event["state_mb"] for event in self.events), 3),
        }
