# Real taxi datasets

The simulator accepts real taxi traces through `mobility.source: taxi`.
Raw files are **not** committed (they are large); this folder only documents how to obtain
and prepare them.

## 1. San Francisco (cabspotting)

- **What it is:** GPS traces of San Francisco taxis. One file per taxi, one sample per line.
- **Raw format:** `latitude longitude occupancy unix_timestamp`

  ```
  37.75153 -122.39447 0 1211033530
  ```

- **Public mirror used here:** `ogozuacik/cabspotting_case_study` on GitHub
  (`cabspottingdata/new_*.txt`, 537 files).
- **Official/original source:** the Cabspotting project (EPFL/CRAWDAD `epfl/mobility`).
  Use the official copy for publication; the mirror is only a convenience.

Prepare 12 taxis:

```bash
python scripts/prepare_taxi_data.py sf \
    --raw data/raw/sf_cabspotting \
    --out data/raw/sf_taxi.csv \
    --taxis 12
```

## 2. Rome (CRAWDAD roma/taxi)

- **What it is:** GPS traces of ~320 Rome taxis over 30 days (February 2014).
- **Raw format:** comma-separated with a header.

  ```
  DriveNo,Date and Time,Latitude,Longitude
  156,2014-02-01 00:00:00.739166+01,41.883670807,12.487777710
  ```

- **Public mirror used here:** `thule100402/rome-taxi-mobility-analysis`
  (Git LFS file `data/taxi.csv.zip`, 325 MB compressed, 1.3 GB extracted).
- **Official/original source:** CRAWDAD `roma/taxi` (Bracciale et al.).

The file spans 30 days. Idle gaps between days would create unrealistic jumps, so the
preparation script keeps a **single day** (the busiest by default) and the taxis with the
most samples on that day:

```bash
python scripts/prepare_taxi_data.py rome \
    --raw data/raw/rome_taxi/taxi.csv \
    --out data/raw/rome_taxi/rome_subset.csv \
    --taxis 40
```

The default run picks **2014-02-21** (1,032,339 samples) and keeps 40 taxis
(192,047 samples) in roughly one minute.

## 3. DATA7 (Pisa)

- **What it is:** real OpenCellID cellular-tower positions plus SUMO-generated vehicle
  trajectories in Pisa, Italy.
- **Source:** Zenodo `10.5281/zenodo.7806928`, file `dataset.tar.gz` (5.5 MB).
- **Raw columns:** `cell_id, cell_lat, cell_lon, time, vehicle_lat, vehicle_lon,
  vehicle_id, distance`.
- **Important:** the tower positions are real; the vehicle trajectories are synthetic
  (SUMO), not real GPS.

Download and prepare the 30-gNB subset used by MORA:

```bash
curl -L -o data/raw/data7/dataset.tar.gz \
    "https://zenodo.org/api/records/7806928/files/dataset.tar.gz/content"
python -c "import tarfile; tarfile.open('data/raw/data7/dataset.tar.gz').extractall('data/raw/data7/extracted')"

python scripts/prepare_data7.py \
    --raw data/raw/data7/extracted/dist/dataset.csv \
    --out data/raw/data7/prepared --cells 30 --min-samples 300
```

`prepare_data7.py` keeps the nearest tower for every (vehicle, time), selects the 30
towers that cover the most observations (54.6%), remaps every vehicle to its nearest
selected tower, and writes:

- `cells.csv` — `id, latitude, longitude`
- `traces.csv` — `taxi_id, time, cell_id`

It keeps 162 vehicles with at least 300 samples (about 10 handovers each in the raw trace).
The simulation config is `configs/data7.yaml`.

## 4. What the simulator does with a trace

1. **Map to the grid.** Latitude/longitude are linearly mapped onto the configured
   `grid_x × grid_y` cells (the latitude axis is flipped so north is up).
2. **Collapse repeated cells.** Consecutive samples in the same cell are merged, giving an
   ordered *route*.
3. **Replay at the configured speed.** The route is expanded into one cell per simulation
   step using `ticks_per_cell = cell_size_m / (speed × tick)`.

Consequences worth knowing:

- `cell_size_m` must match the geography implied by the mapping. For example, the SF
  bounding box is roughly 45 km across; with a 16×16 grid, one cell is about 2.8 km, so
  `cell_size_m: 2800` is consistent.
- Timestamps are **not** used by the replay. Only the order of the route matters; the speed
  sweep re-times the same route deliberately.
- Rome keeps one day to avoid overnight jumps. Multi-day traces would need explicit gap
  splitting.

## 5. Configurations

- `configs/sf_taxi.yaml` — 12 SF taxis, 16×16 grid, 2.8 km cells.
- `configs/rome_taxi.yaml` — 12 Rome taxis (from the 40-taxi subset), 16×16 grid, 2.1 km cells.
- `configs/synthetic_16x16.yaml` — synthetic control with the same topology as SF.
- `configs/data7.yaml` — 30 real DATA7 gNBs + SUMO mobility.

Run:

```bash
python -m myedgesimpy inspect --config configs/sf_taxi.yaml
python -m myedgesimpy run --config configs/sf_taxi.yaml
python -m myedgesimpy sweep --config configs/rome_taxi.yaml \
    --speeds 20,40,60 --strategies reactive,reactive_delta,proactive,proactive_delta
```
