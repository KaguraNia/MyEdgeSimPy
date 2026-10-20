"""Prepare real taxi traces for the simulator.

Two raw formats are supported:

San Francisco (cabspotting)
    A directory of per-taxi files, one row per sample::

        37.75153 -122.39447 0 1211033530
        latitude longitude occupancy unix_timestamp

Rome (CRAWDAD roma/taxi)
    One large CSV with a header::

        DriveNo,Date and Time,Latitude,Longitude
        156,2014-02-01 00:00:00.739166+01,41.883670807,12.487777710

The Rome file spans 30 days. Cars that are idle for hours would otherwise produce
unrealistic jumps, so the script keeps a single day (the busiest one by default) and
the taxis with the most samples on that day.

Both commands write a normalised CSV with columns::

    taxi_id,timestamp,lat,lon

Usage:
    python scripts/prepare_taxi_data.py rome --raw data/raw/rome_taxi/taxi.csv \
        --out data/raw/rome_taxi/rome_subset.csv --taxis 40

    python scripts/prepare_taxi_data.py sf --raw data/raw/sf_cabspotting \
        --out data/raw/sf_taxi.csv --taxis 40
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path


def _norm(value: str) -> str:
    return value.strip().lower().replace("_", " ").replace("-", " ")


def _pick(columns: dict, candidates: set) -> str | None:
    for key, original in columns.items():
        if key in candidates:
            return original
    return None


def prepare_rome(raw: Path, out: Path, taxis: int, date: str | None) -> None:
    with raw.open("r", encoding="utf-8-sig", errors="ignore", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise SystemExit(f"{raw} has no header")
        columns = {_norm(name): name for name in reader.fieldnames}
        id_key = _pick(columns, {"driveno", "drive no", "driver id", "driver", "taxi id", "id"})
        time_key = _pick(columns, {"date and time", "timestamp", "time", "datetime"})
        lat_key = _pick(columns, {"latitude", "lat", "y"})
        lon_key = _pick(columns, {"longitude", "lon", "lng", "x"})
        if not all([id_key, time_key, lat_key, lon_key]):
            raise SystemExit(f"Could not find required columns in {raw}: {reader.fieldnames}")

        # Pass 1: how many samples per (date, taxi)?
        per_date = Counter()
        per_taxi_date = Counter()
        for row in reader:
            stamp = (row.get(time_key) or "").strip()
            if len(stamp) < 10:
                continue
            day = stamp[:10]
            taxi = (row.get(id_key) or "").strip()
            per_date[day] += 1
            per_taxi_date[(taxi, day)] += 1

    if not per_date:
        raise SystemExit("No usable rows found")

    chosen_day = date or per_date.most_common(1)[0][0]
    selected = [
        taxi
        for (taxi, day), count in per_taxi_date.most_common()
        if day == chosen_day and count >= 100
    ][:taxis]
    if not selected:
        raise SystemExit(f"No taxi has enough samples on {chosen_day}")
    selected_set = set(selected)

    out.parent.mkdir(parents=True, exist_ok=True)
    written = Counter()
    with raw.open("r", encoding="utf-8-sig", errors="ignore", newline="") as handle, out.open(
        "w", encoding="utf-8", newline=""
    ) as sink:
        reader = csv.DictReader(handle)
        writer = csv.writer(sink)
        writer.writerow(["taxi_id", "timestamp", "lat", "lon"])
        for row in reader:
            stamp = (row.get(time_key) or "").strip()
            taxi = (row.get(id_key) or "").strip()
            if len(stamp) < 10 or stamp[:10] != chosen_day or taxi not in selected_set:
                continue
            try:
                lat = float(row[lat_key])
                lon = float(row[lon_key])
            except (TypeError, ValueError):
                continue
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                continue
            writer.writerow([taxi, stamp, f"{lat:.7f}", f"{lon:.7f}"])
            written[taxi] += 1

    print(f"date={chosen_day} (busiest: {per_date[chosen_day]} samples)")
    print(f"taxis={len(written)} samples={sum(written.values())} -> {out}")
    for taxi, count in written.most_common(5):
        print(f"  taxi {taxi}: {count} samples")


def prepare_sf(raw: Path, out: Path, taxis: int) -> None:
    files = sorted(raw.glob("*.txt"))
    if not files:
        raise SystemExit(f"No .txt files in {raw}")

    out.parent.mkdir(parents=True, exist_ok=True)
    written = Counter()
    with out.open("w", encoding="utf-8", newline="") as sink:
        writer = csv.writer(sink)
        writer.writerow(["taxi_id", "timestamp", "lat", "lon"])
        for file in files:
            if len(written) >= taxis:
                break
            taxi_id = file.stem
            blocks = []
            with file.open("r", encoding="utf-8", errors="ignore") as handle:
                for line in handle:
                    parts = line.split()
                    if len(parts) < 4:
                        continue
                    try:
                        lat, lon, _occupancy, stamp = (
                            float(parts[0]),
                            float(parts[1]),
                            parts[2],
                            parts[3],
                        )
                    except ValueError:
                        continue
                    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                        continue
                    blocks.append([taxi_id, stamp, f"{lat:.7f}", f"{lon:.7f}"])
            if blocks:
                writer.writerows(blocks)
                written[taxi_id] = len(blocks)

    print(f"taxis={len(written)} samples={sum(written.values())} -> {out}")
    for taxi, count in written.most_common(5):
        print(f"  taxi {taxi}: {count} samples")


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="dataset", required=True)

    rome = sub.add_parser("rome")
    rome.add_argument("--raw", required=True)
    rome.add_argument("--out", required=True)
    rome.add_argument("--taxis", type=int, default=40)
    rome.add_argument("--date", default=None)

    sf = sub.add_parser("sf")
    sf.add_argument("--raw", required=True)
    sf.add_argument("--out", required=True)
    sf.add_argument("--taxis", type=int, default=40)

    args = parser.parse_args()
    if args.dataset == "rome":
        prepare_rome(Path(args.raw), Path(args.out), args.taxis, args.date)
    else:
        prepare_sf(Path(args.raw), Path(args.out), args.taxis)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
