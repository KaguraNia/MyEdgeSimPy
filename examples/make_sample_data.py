"""Generate small synthetic *stand-ins* for the real datasets.

They are tiny on purpose: they exist so that the DATA7 and taxi code paths can be exercised
end-to-end (and used as templates for the real files). Replace them with the real datasets.

    python examples/make_sample_data.py
"""

from __future__ import annotations

import csv
import math
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent


def make_sites(n_side: int = 5, center=(41.9028, 12.4964), spacing_deg: float = 0.006) -> None:
    """A jittered grid of base-station sites around Rome (DATA7 stand-in)."""
    rng = random.Random(11)
    rows = []
    index = 0
    for i in range(n_side):
        for j in range(n_side):
            index += 1
            lat = center[0] + (i - n_side / 2) * spacing_deg + rng.uniform(-0.001, 0.001)
            lon = center[1] + (j - n_side / 2) * spacing_deg + rng.uniform(-0.001, 0.001)
            rows.append({"id": index, "latitude": round(lat, 6), "longitude": round(lon, 6)})

    path = HERE / "data7_sites_sample.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["id", "latitude", "longitude"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {path} ({len(rows)} sites)")


def make_taxi(n_taxis: int = 3, points: int = 60) -> None:
    """A few taxi traces walking through the same area (Rome/SF stand-in)."""
    rng = random.Random(5)
    center = (41.9028, 12.4964)
    path = HERE / "taxi_sample.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["taxi_id", "timestamp", "lat", "lon"])
        for taxi in range(1, n_taxis + 1):
            lat, lon = center[0] + rng.uniform(-0.02, 0.02), center[1] + rng.uniform(-0.02, 0.02)
            heading = rng.uniform(0, 2 * math.pi)
            timestamp = 1_700_000_000
            for step in range(points):
                heading += rng.uniform(-0.4, 0.4)
                speed_deg = 0.00035
                lat += speed_deg * math.sin(heading)
                lon += speed_deg * math.cos(heading)
                timestamp += 15
                writer.writerow([taxi, timestamp, round(lat, 6), round(lon, 6)])
    print(f"wrote {path} ({n_taxis} taxis x {points} points)")


if __name__ == "__main__":
    make_sites()
    make_taxi()