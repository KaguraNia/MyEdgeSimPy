"""Build an EdgeSimPy input dataset from a configuration and a set of vehicle traces.

Design notes
------------
EdgeSimPy loads a scenario from a JSON-like dictionary with two groups per component:
``attributes`` (scalars) and ``relationships`` (references to other components). This
module builds that dictionary directly, which keeps the scenario fully reproducible and
easy to diff, while still letting EdgeSimPy own the simulation mechanics.

Modelling choices worth knowing about
-------------------------------------

* **One service instance per (vehicle, MEC service).** A vehicle's session state at the
  edge is naturally per-user, so the four MEC services of vehicle ``v`` are four
  ``Service`` instances that live on the edge server of the cell the vehicle occupies.
  Migrating that instance is exactly "migrating the user's session state".
* **One edge server per cell.** The vehicle is attached to the base station of its cell,
  and the local edge server is the natural migration target.
* **Image layers are pre-seeded on the servers that are initially occupied**, so the
  simulation starts from a warm state (the services are already running). Only
  *subsequent* migrations pay for pulling layers that are not cached on the target node
  -- which is precisely the effect that container image caching has in reality.
* **Link bandwidth is expressed in MB per simulation step** (converted from Mbps), so
  ``data_to_transfer`` (in MB) divided by bandwidth gives a transfer time in steps, i.e.
  a migration interruption measured in seconds when the tick is 1 s.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ..config import SimulationConfig
from ..mobility.paths import VehicleTrace, build_traces
from ..services.catalog import ImageSpec, ServiceProfile, build_images
from ..topology.graph import TopologyLayout, build_layout

# Keys understood by EdgeSimPy's dataset loader (they must match component class names).
COMPONENT_KEYS = [
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
]


@dataclass
class Scenario:
    """A fully-built scenario: the EdgeSimPy dataset plus the metadata we need later."""

    config: SimulationConfig
    layout: TopologyLayout
    traces: List[VehicleTrace]
    profiles: List[ServiceProfile]
    images: List[ImageSpec]
    dataset: Dict[str, List[Dict[str, Any]]]
    # service_id -> {"vehicle_id", "key", "profile"}
    service_index: Dict[int, Dict[str, Any]]
    # digest -> ServiceProfile
    profile_by_digest: Dict[str, ServiceProfile]
    registry_cell: Tuple[int, int]

    def summary(self) -> Dict[str, Any]:
        layout = self.layout.summary()
        return {
            "topology": layout,
            "vehicles": len(self.traces),
            "services": sum(len(t.vehicle_services) for t in [] ) if False else len(self.service_index),
            "images": len(self.images),
            "registry_cell": list(self.registry_cell),
            "link_bandwidth_mb_per_step": round(self.config.link_bandwidth_mb_per_step(), 3),
            "ticks_per_cell": round(self.config.ticks_per_cell(), 2),
            "speed_kmh": self.config.mobility.speed_kmh,
            "handovers": [len(t.handover_steps) for t in self.traces],
        }

    def save(self, directory: str | Path) -> Path:
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        return save_dataset(self.dataset, directory / "dataset.json")


@dataclass
class _ServerState:
    """Bookkeeping for one edge server while the dataset is being assembled."""

    cell_index: int
    layers: Dict[str, int] = field(default_factory=dict)      # layer digest -> id
    images: Dict[str, int] = field(default_factory=dict)      # image digest -> id
    services: List[int] = field(default_factory=list)         # service ids
    registries: List[int] = field(default_factory=list)       # registry ids
    disk_demand: float = 0.0
    cpu_demand: float = 0.0
    memory_demand: float = 0.0


def build_dataset(
    config: SimulationConfig,
    layout: TopologyLayout,
    traces: Sequence[VehicleTrace],
    profiles: Sequence[ServiceProfile],
) -> Tuple[Dict[str, List[Dict[str, Any]]], Dict[str, Any]]:
    """Assemble the EdgeSimPy dataset plus a metadata dictionary."""
    images = build_images(list(profiles))
    image_by_digest = {image.digest: image for image in images}
    profile_by_digest = {profile.image_digest: profile for profile in profiles}

    dataset: Dict[str, List[Dict[str, Any]]] = {key: [] for key in COMPONENT_KEYS}

    n_cells = layout.size
    servers: List[_ServerState] = [_ServerState(cell_index=i) for i in range(n_cells)]

    link_bandwidth = config.link_bandwidth_mb_per_step()
    link_delay = config.topology.link_delay_ms
    wireless_delay = config.topology.wireless_delay_ms
    server_profile = config.topology.server

    counters = defaultdict(int)

    def new_id(component: str) -> int:
        counters[component] += 1
        return counters[component]

    def ensure_image(cell_index: int, image: ImageSpec) -> None:
        """Make sure a server caches all layers of an image (Docker-style)."""
        server = servers[cell_index]
        for layer in image.layers:
            if layer.digest in server.layers:
                continue
            layer_id = new_id("ContainerLayer")
            server.layers[layer.digest] = layer_id
            server.disk_demand += layer.size_mb
            dataset["ContainerLayer"].append(
                {
                    "attributes": {
                        "id": layer_id,
                        "digest": layer.digest,
                        "size": layer.size_mb,
                        "instruction": layer.instruction,
                    },
                    "relationships": {
                        "server": {"class": "EdgeServer", "id": cell_index + 1},
                    },
                }
            )
        if image.digest not in server.images:
            image_id = new_id("ContainerImage")
            server.images[image.digest] = image_id
            dataset["ContainerImage"].append(
                {
                    "attributes": {
                        "id": image_id,
                        "name": image.name,
                        "tag": image.tag,
                        "digest": image.digest,
                        "layers_digests": [layer.digest for layer in image.layers],
                        "architecture": "amd64",
                    },
                    "relationships": {
                        "server": {"class": "EdgeServer", "id": cell_index + 1},
                    },
                }
            )

    # ----------------------------------------------------------------------------------
    # Container registry (image source for later migrations)
    # ----------------------------------------------------------------------------------
    registry_coordinates = tuple(config.topology.registry_cell or layout.cells[0].coordinates)
    registry_cell_index = layout.index_of(registry_coordinates)  # type: ignore[arg-type]
    registry_server_id = registry_cell_index + 1

    for image in images:
        ensure_image(registry_cell_index, image)

    registry_id = new_id("ContainerRegistry")
    servers[registry_cell_index].registries.append(registry_id)
    servers[registry_cell_index].cpu_demand += 2
    servers[registry_cell_index].memory_demand += 2048
    dataset["ContainerRegistry"].append(
        {
            "attributes": {
                "id": registry_id,
                "cpu_demand": 2,
                "memory_demand": 2048,
                "available": True,
            },
            "relationships": {"server": {"class": "EdgeServer", "id": registry_server_id}},
        }
    )

    # ----------------------------------------------------------------------------------
    # Services, applications, access patterns and users
    # ----------------------------------------------------------------------------------
    service_index: Dict[int, Dict[str, Any]] = {}
    users_by_base_station: Dict[int, List[int]] = defaultdict(list)
    access_duration = config.simulation.duration_steps

    for trace in traces:
        vehicle_id = trace.vehicle_id
        initial_cell_index = layout.index_of(trace.initial_cell)
        initial_server_id = initial_cell_index + 1
        server_state = servers[initial_cell_index]

        service_ids: List[int] = []
        for profile in profiles:
            ensure_image(initial_cell_index, image_by_digest[profile.image_digest])

            service_id = new_id("Service")
            service_ids.append(service_id)
            server_state.services.append(service_id)
            server_state.cpu_demand += profile.cpu
            server_state.memory_demand += profile.memory_mb

            dataset["Service"].append(
                {
                    "attributes": {
                        "id": service_id,
                        "label": f"{profile.key}@veh{vehicle_id}",
                        "state": profile.state_mb,
                        "_available": True,
                        "cpu_demand": profile.cpu,
                        "memory_demand": profile.memory_mb,
                        "image_digest": profile.image_digest,
                    },
                    "relationships": {
                        "server": {"class": "EdgeServer", "id": initial_server_id},
                    },
                }
            )
            service_index[service_id] = {
                "vehicle_id": vehicle_id,
                "key": profile.key,
                "profile": profile,
                "initial_state_mb": profile.state_mb,
            }

        application_id = new_id("Application")
        user_id = new_id("User")

        dataset["Application"].append(
            {
                "attributes": {"id": application_id, "label": f"vehicle-{vehicle_id}"},
                "relationships": {
                    "services": [{"class": "Service", "id": sid} for sid in service_ids],
                    "users": [{"class": "User", "id": user_id}],
                },
            }
        )

        # Each service points back at its application.
        for entry in dataset["Service"]:
            if entry["attributes"]["id"] in service_ids:
                entry["relationships"]["application"] = {"class": "Application", "id": application_id}

        access_pattern_id = new_id("RandomDurationAndIntervalAccessPattern")
        dataset["RandomDurationAndIntervalAccessPattern"].append(
            {
                "attributes": {
                    "id": access_pattern_id,
                    "duration_values": [access_duration],
                    "interval_values": [0],
                    "history": [
                        {
                            "start": 1,
                            "end": access_duration,
                            "duration": access_duration,
                            "waiting_time": 0,
                            "access_time": 0,
                            "interval": 0,
                            "next_access": access_duration + 1,
                        }
                    ],
                },
                "relationships": {
                    "user": {"class": "User", "id": user_id},
                    "app": {"class": "Application", "id": application_id},
                },
            }
        )

        dataset["User"].append(
            {
                "attributes": {
                    "id": user_id,
                    "coordinates": trace.initial_cell,
                    "coordinates_trace": [tuple(cell) for cell in trace.cells],
                    "delays": {str(application_id): None},
                    "delay_slas": {str(application_id): config.metrics.sla_latency_ms},
                    "communication_paths": {},
                    "making_requests": {
                        str(application_id): {str(step): True for step in range(1, access_duration + 2)}
                    },
                    "mobility_model_parameters": {},
                },
                "relationships": {
                    "access_patterns": {
str(application_id): {
                            "class": "RandomDurationAndIntervalAccessPattern",
                            "id": access_pattern_id,
                        }
                    },
                    "mobility_model": "pathway",
                    "applications": [{"class": "Application", "id": application_id}],
                    "base_station": {"class": "BaseStation", "id": initial_server_id},
                },
            }
        )

        users_by_base_station[initial_cell_index].append(user_id)

    # ----------------------------------------------------------------------------------
    # Base stations, network switches and links
    # ----------------------------------------------------------------------------------
    link_ids_by_cell: Dict[int, List[int]] = defaultdict(list)
    for a, b in layout.links:
        link_id = new_id("NetworkLink")
        link_ids_by_cell[a].append(link_id)
        link_ids_by_cell[b].append(link_id)
        dataset["NetworkLink"].append(
            {
                "attributes": {
                    "id": link_id,
                    "delay": link_delay,
                    "bandwidth": link_bandwidth,
                    "bandwidth_demand": 0,
                    "active": True,
                },
                "relationships": {
                    "topology": {"class": "Topology", "id": 1},
                    "active_flows": [],
                    "applications": [],
                    "nodes": [
                        {"class": "NetworkSwitch", "id": a + 1},
                        {"class": "NetworkSwitch", "id": b + 1},
                    ],
                },
            }
        )

    for cell in layout.cells:
        cell_index = cell.index
        node_id = cell_index + 1

        dataset["BaseStation"].append(
            {
                "attributes": {
                    "id": node_id,
                    "coordinates": cell.coordinates,
                    "wireless_delay": wireless_delay,
                },
                "relationships": {
                    "users": [{"class": "User", "id": uid} for uid in users_by_base_station[cell_index]],
                    "edge_servers": [{"class": "EdgeServer", "id": node_id}],
                    "network_switch": {"class": "NetworkSwitch", "id": node_id},
                },
            }
        )

        dataset["NetworkSwitch"].append(
            {
                "attributes": {
                    "id": node_id,
                    "coordinates": cell.coordinates,
                    "active": True,
                    "power_model_parameters": {},
                },
                "relationships": {
                    "power_model": None,
                    "edge_servers": [{"class": "EdgeServer", "id": node_id}],
                    "links": [{"class": "NetworkLink", "id": lid} for lid in link_ids_by_cell[cell_index]],
                    "base_station": {"class": "BaseStation", "id": node_id},
                },
            }
        )

        server = servers[cell_index]
        dataset["EdgeServer"].append(
            {
                "attributes": {
                    "id": node_id,
                    "available": True,
                    "model_name": server_profile.model_name,
                    "cpu": server_profile.cpu,
                    "memory": server_profile.memory_mb,
                    "disk": server_profile.disk_mb,
                    "cpu_demand": server.cpu_demand,
                    "memory_demand": server.memory_demand,
                    "disk_demand": server.disk_demand,
                    "coordinates": cell.coordinates,
                    "max_concurrent_layer_downloads": server_profile.max_concurrent_layer_downloads,
                    "active": True,
                    "power_model_parameters": {},
                },
                "relationships": {
                    "power_model": None,
                    "base_station": {"class": "BaseStation", "id": node_id},
                    "network_switch": {"class": "NetworkSwitch", "id": node_id},
                    "services": [{"class": "Service", "id": sid} for sid in server.services],
                    "container_layers": [
                        {"class": "ContainerLayer", "id": lid} for lid in server.layers.values()
                    ],
                    "container_images": [
                        {"class": "ContainerImage", "id": iid} for iid in server.images.values()
                    ],
                    "container_registries": [
                        {"class": "ContainerRegistry", "id": rid} for rid in server.registries
                    ],
                },
            }
        )

    metadata = {
        "service_index": service_index,
        "profile_by_digest": profile_by_digest,
        "registry_cell": registry_coordinates,
        "registry_server_id": registry_server_id,
        "image_by_digest": image_by_digest,
    }
    return dataset, metadata


def build_scenario(config: SimulationConfig) -> Scenario:
    """End-to-end scenario construction: topology -> mobility -> EdgeSimPy dataset."""
    layout = build_layout(config)
    traces = build_traces(config, layout)
    profiles = _profiles(config)
    dataset, metadata = build_dataset(config, layout, traces, profiles)

    return Scenario(
        config=config,
        layout=layout,
        traces=traces,
        profiles=profiles,
        images=build_images(list(profiles)),
        dataset=dataset,
        service_index=metadata["service_index"],
        profile_by_digest=metadata["profile_by_digest"],
        registry_cell=metadata["registry_cell"],
    )


def _profiles(config: SimulationConfig) -> List[ServiceProfile]:
    from ..services.catalog import get_profiles

    return get_profiles(config.services.enabled, config.services.state_growth_factor)


def save_dataset(dataset: Dict[str, Any], path: str | Path) -> Path:
    """Write the dataset to JSON (EdgeSimPy can load it back with ``initialize``)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(dataset, handle, indent=2)
    return path