"""Catalogue of the four MEC services used in the study.

Every service is described along the dimensions that matter for migration:

* **Terminal -> edge**: what the vehicle uploads every step (KB/step).
* **Edge compute**: the CPU/RAM the service occupies on the edge server.
* **Edge -> terminal**: the response payload returned to the vehicle (KB/step).
* **Migratable state**: how many MB of session/context state must follow the vehicle,
  and how quickly that state grows while the service runs (MB/step).

The container image is modelled as an ordered list of Docker-style layers so that
EdgeSimPy can reproduce the real cost of pulling an image to a new edge node. Only the
layers missing on the target node are transferred, which is exactly what EdgeSimPy
implements through container registries.

Units
-----
* sizes: megabytes (MB)
* demands: units of the ``mec-standard`` server profile (CPU units / MB of RAM)
* throughput: KB per simulation step
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class LayerSpec:
    """One container layer. Shared layers are what make image caching valuable."""

    digest: str
    size_mb: float
    instruction: str


@dataclass(frozen=True)
class ServiceProfile:
    """Static description of a MEC service."""

    key: str
    label: str
    cpu: int
    memory_mb: int
    state_mb: float
    state_growth_mb_per_step: float
    layers: Tuple[LayerSpec, ...]
    uplink_kb_per_step: float
    downlink_kb_per_step: float
    edge_compute_ms: float

    # Narrative fields (documentation / paper tables)
    terminal_sends: str
    edge_computes: str
    terminal_receives: str

    @property
    def image_digest(self) -> str:
        return f"sha256:{self.key}-image-v1"

    @property
    def image_name(self) -> str:
        return f"mec/{self.key}"

    @property
    def image_size_mb(self) -> float:
        return sum(layer.size_mb for layer in self.layers)

    @property
    def payload_kb_per_step(self) -> float:
        return self.uplink_kb_per_step + self.downlink_kb_per_step

    def as_row(self) -> Dict[str, object]:
        """Flat representation, handy for documentation tables and CSV exports."""
        return {
            "service": self.key,
            "label": self.label,
            "cpu": self.cpu,
            "memory_mb": self.memory_mb,
            "state_mb": round(self.state_mb, 3),
            "state_growth_mb_per_step": round(self.state_growth_mb_per_step, 4),
            "image_size_mb": round(self.image_size_mb, 1),
            "uplink_kb_per_step": self.uplink_kb_per_step,
            "downlink_kb_per_step": self.downlink_kb_per_step,
            "edge_compute_ms": self.edge_compute_ms,
        }


# --------------------------------------------------------------------------------------
# Shared layers
# --------------------------------------------------------------------------------------
BASE_OS = LayerSpec("sha256:base-os-22.04", 40.0, "FROM ubuntu:22.04")
BASE_PY = LayerSpec("sha256:base-runtime-python311", 120.0, "RUN pip install --no-cache-dir runtime")
BASE_MEDIA = LayerSpec("sha256:base-runtime-media", 180.0, "RUN apt-get install -y ffmpeg gstreamer")

NAV_APP = LayerSpec("sha256:nav-app", 60.0, "COPY ./navigation /opt/mec/navigation")
NAV_MAP = LayerSpec("sha256:nav-mapdata-regional", 150.0, "COPY ./mapdata /opt/mec/mapdata")

ALERT_APP = LayerSpec("sha256:alert-app", 25.0, "COPY ./alerts /opt/mec/alerts")
ALERT_CTX = LayerSpec("sha256:alert-context-schema", 20.0, "COPY ./context /opt/mec/context")

TRAFFIC_APP = LayerSpec("sha256:traffic-app", 45.0, "COPY ./traffic /opt/mec/traffic")
TRAFFIC_MODELS = LayerSpec("sha256:traffic-models", 90.0, "COPY ./models /opt/mec/models")

INFO_APP = LayerSpec("sha256:infotainment-app", 70.0, "COPY ./infotainment /opt/mec/infotainment")
INFO_CACHE = LayerSpec("sha256:infotainment-mediacache", 250.0, "COPY ./mediacache /opt/mec/mediacache")


# --------------------------------------------------------------------------------------
# The four services
# --------------------------------------------------------------------------------------
NAVIGATION = ServiceProfile(
    key="navigation",
    label="Navigation assistance",
    cpu=1,
    memory_mb=256,
    state_mb=5.0,
    state_growth_mb_per_step=0.010,
    layers=(BASE_OS, BASE_PY, NAV_APP, NAV_MAP),
    uplink_kb_per_step=1.0,
    downlink_kb_per_step=6.0,
    edge_compute_ms=8.0,
    terminal_sends="GPS fix, heading, partial route request",
    edge_computes="Route re-planning on a regional map graph, hazard overlay",
    terminal_receives="Turn-by-turn instructions and updated route segment",
)

INFOTAINMENT = ServiceProfile(
    key="infotainment",
    label="Infotainment streaming",
    cpu=2,
    memory_mb=1024,
    state_mb=200.0,
    state_growth_mb_per_step=0.150,
    layers=(BASE_OS, BASE_MEDIA, INFO_APP, INFO_CACHE),
    uplink_kb_per_step=5.0,
    downlink_kb_per_step=300.0,
    edge_compute_ms=12.0,
    terminal_sends="Playback position, quality hints, segment requests",
    edge_computes="Transcoding/segment selection, ad insertion, buffer management",
    terminal_receives="Video/audio segments and playlist updates",
)

ALERT = ServiceProfile(
    key="alert",
    label="Context-aware alerts",
    cpu=1,
    memory_mb=128,
    state_mb=3.0,
    state_growth_mb_per_step=0.005,
    layers=(BASE_OS, BASE_PY, ALERT_APP, ALERT_CTX),
    uplink_kb_per_step=0.5,
    downlink_kb_per_step=1.5,
    edge_compute_ms=5.0,
    terminal_sends="Local sensor snapshot, vehicle telemetry",
    edge_computes="Context matching against alert subscriptions, geo-fencing",
    terminal_receives="Alert notifications with severity and location",
)

TRAFFIC_ANALYTICS = ServiceProfile(
    key="traffic_analytics",
    label="Real-time traffic analytics",
    cpu=3,
    memory_mb=2048,
    state_mb=80.0,
    state_growth_mb_per_step=0.100,
    layers=(BASE_OS, BASE_PY, TRAFFIC_APP, TRAFFIC_MODELS),
    uplink_kb_per_step=20.0,
    downlink_kb_per_step=5.0,
    edge_compute_ms=20.0,
    terminal_sends="Probe samples (position, speed), camera/radar summaries",
    edge_computes="Spatio-temporal aggregation and short-horizon flow prediction",
    terminal_receives="Congestion index and predicted travel-time heat-map",
)


CATALOG: Dict[str, ServiceProfile] = {
    NAVIGATION.key: NAVIGATION,
    INFOTAINMENT.key: INFOTAINMENT,
    ALERT.key: ALERT,
    TRAFFIC_ANALYTICS.key: TRAFFIC_ANALYTICS,
}


def get_profiles(enabled: List[str], state_growth_factor: float = 1.0) -> List[ServiceProfile]:
    """Return the enabled service profiles, applying a state-growth multiplier."""
    import dataclasses

    profiles: List[ServiceProfile] = []
    for key in enabled:
        if key not in CATALOG:
            raise KeyError(f"Unknown MEC service '{key}'. Available: {sorted(CATALOG)}")
        profile = CATALOG[key]
        if state_growth_factor != 1.0:
            profile = dataclasses.replace(
                profile,
                state_growth_mb_per_step=profile.state_growth_mb_per_step * state_growth_factor,
            )
        profiles.append(profile)
    return profiles


@dataclass
class ImageSpec:
    """Aggregated view of a container image that must exist in the registry."""

    name: str
    digest: str
    tag: str
    layers: List[LayerSpec] = field(default_factory=list)

    @property
    def size_mb(self) -> float:
        return sum(layer.size_mb for layer in self.layers)


def build_images(profiles: List[ServiceProfile], include_registry_image: bool = True) -> List[ImageSpec]:
    """Build the list of container images (each carrying its deduplicated layers)."""
    images = [
        ImageSpec(
            name=profile.image_name,
            digest=profile.image_digest,
            tag="v1",
            layers=list(profile.layers),
        )
        for profile in profiles
    ]

    if include_registry_image:
        images.append(
            ImageSpec(
                name="registry",
                digest="sha256:registry-image-v1",
                tag="v1",
                layers=[BASE_OS, LayerSpec("sha256:registry-app", 90.0, "COPY ./registry /opt/registry")],
            )
        )
    return images