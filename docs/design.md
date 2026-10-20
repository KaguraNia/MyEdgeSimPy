# Design of the MyEdgeSimPy prototype

This document describes how the MEC migration scenario is mapped onto EdgeSimPy, the exact
execution order of a simulation step, and every modelling assumption that a reader of the
resulting paper should be able to check.

---

## 1. Component map

| EdgeSimPy component | Role in MyEdgeSimPy |
|---|---|
| `BaseStation` | One per coverage cell. Owns the `wireless_delay` and is the attachment point of vehicles. |
| `NetworkSwitch` | One per cell; the vertex of the inter-node transport graph. |
| `NetworkLink` | Fibre link between adjacent cells; carries `delay` (ms) and `bandwidth` (MB per step). |
| `EdgeServer` | One per cell; hosts the MEC service instances and the container cache. |
| `ContainerRegistry` | Hosted on one server; the source from which service images are pulled. |
| `ContainerLayer` / `ContainerImage` | Docker-style image model: only layers missing on the target are transferred. |
| `Service` | One instance per (vehicle, MEC service). Migrating it *is* migrating the user's session state. |
| `Application` | One per vehicle; groups the four services the vehicle consumes. |
| `User` | The vehicle. Its `coordinates_trace` drives mobility and handovers. |
| `RandomDurationAndIntervalAccessPattern` | Makes the vehicle request its application continuously. |
| `Topology` | The NetworkX graph built from the switches and links. |

Everything else (time progression, agent activation order, bandwidth sharing, flow
progress) is untouched EdgeSimPy behaviour.

---

## 2. Dataset construction

`myedgesimpy/scenario/builder.py` writes the EdgeSimPy input dictionary directly
(`attributes` + `relationships` per component) instead of relying on a hand-written JSON
file. This keeps the scenario reproducible from the configuration and easy to diff, and it
still lets `Simulator.initialize()` perform all the object/relationship wiring.

Key points:

* **Identifiers.** Edge servers, base stations and switches share the id `cell_index + 1`;
  services, applications, users and layers have their own sequences.
* **Coordinates must be tuples.** EdgeSimPy attaches a user to a base station by exact
  coordinate equality (`BaseStation.find_by(coordinates=...)`), so cell coordinates are
  stored as tuples both in the trace and on the base stations. A JSON round-trip turns both
  into lists, which is still self-consistent.
* **Warm start.** The servers of the initially occupied cells are pre-seeded with the layers
  and image objects of the services they host, and the services are created with
  `_available = True` and `server` already set. The simulation therefore starts from a
  running system; no placement transient contaminates the measurements.
* **Bandwidth units.** `bandwidth` is expressed in *MB per simulation step*
  (`link_bandwidth_mbps * tick_seconds / 8`), so `data_to_transfer` (MB) divided by the
  achieved bandwidth is a transfer time in steps, i.e. seconds when the tick is 1 s.

---

## 3. Execution order inside one simulation step

1. `MigrationController.run_step(step)` (EdgeSimPy's `resource_management_algorithm`)
   * update every service's `state` from the state-growth model,
   * apply the availability policy (pre-copy keeps the source serving),
   * select migration targets and call `service.provision(target_server)`,
   * detect migrations that finished in the previous step and charge the cutover window.
2. `DefaultScheduler.step()` — unmodified EdgeSimPy order:
   * `EdgeServer.step()`: pick layers from the waiting queue and start download flows,
   * `Service.step()`: advance the migration state machine, create the state flow,
   * `Topology.step()`: re-run the max-min fair bandwidth allocation,
   * `NetworkFlow.step()`: advance flows, release links, finish transfers,
   * `User.step()`: move to the next cell, reattach to the base station, recompute delays,
   * `ContainerRegistry.step()` and the remaining passive agents.
3. `MigrationController.post_step()` (invoked from the metrics collector): re-assert the
   availability policy after EdgeSimPy flipped `_available` during the state-flow creation.
4. `MetricsCollector.sample()`: record handovers, new flows, availability, delays and link
   utilisation.

---

## 4. Migration lifecycle

```
decision ──► provision()            status = "waiting"
              │                     (target pulls missing image layers from the registry)
              ├──► status = "pulling_layers"
              │
              ├──► status = "migrating_service_state"   (NetworkFlow carries service.state)
              │        └── stop-and-copy: the service is unavailable here
              │            pre-copy:       the controller keeps it available, and a single
              │                            coordinated cutover is charged afterwards
              └──► status = "finished"    service moves to the target server, user routes recomputed
```

Total migration latency is decomposed by EdgeSimPy into `waiting_time`,
`pulling_layers_time` and `migrating_service_state_time`; the collector reports all three
plus the end-to-end duration. Only the *state* phase consumes the migratable state; image
pulling is amortised by the container cache.

---

## 5. State model

Each service has:

* `state_mb` - the size of the session state at t = 0,
* `state_growth_mb_per_step` - how fast the state grows while the service runs,
* `image layers` - the immutable part, cached on the nodes that already ran the service.

At every step the controller sets `service.state = state_mb + growth * (step - 1)`, except
while the service is being provisioned (otherwise the size being transferred would change
mid-flight). The delta strategy instead sends only the change since the target's base.

Base snapshots are tracked per `(service, node)`:

* a **warm** target already holds a base: only `current - base` is sent;
* a **cold** target has no base: the full state is sent;
* when a migration completes, the target's base becomes the snapshot that was sent;
* when a service leaves a node, that node keeps the live state at departure as its base.

After the transfer the target still has to apply the state and restart the service:

```
restore_steps = round(transferred_mb * restore_ms_per_mb / tick_ms)
```

Those steps are added to the unavailable window.

Optional base maintenance (`base_maintenance: neighbors`) replicates snapshots to adjacent
nodes on a fixed schedule. Its background flows consume bandwidth and are included in the
reported overhead. It is implemented but currently shelved while transfer-layer work
continues.

---

## 6. Availability policy

| Policy | During bulk transfer | After the transfer |
|---|---|---|
| `stop_and_copy` (baseline) | EdgeSimPy marks the service unavailable as soon as the state flow is created | available as soon as it finishes |
| `pre_copy` | the controller keeps `_available = True` (the source node keeps serving) | one coordinated `cutover_steps` window per vehicle, once all of its services are in place |

The coordinated cutover (rather than one window per service) models *make-before-break*
handover: the vehicle is interrupted once per handover, not once per service.

---

## 7. Metric definitions

| Metric | Definition |
|---|---|
| `service_interruption_ratio` | (# vehicle-steps with >= 1 unavailable service) / (vehicles x duration) |
| `unavailable_service_ratio` | (# service-steps unavailable) / (services x duration) |
| `sla_violation_ratio` | (# vehicle-steps with a delay above the SLA or with an unavailable service) / (vehicles x duration) |
| `mean_migration_duration_steps` | mean `end - start` of completed migrations |
| `state_mb_total` | sum of the state bytes requested by all migrations |
| `image_mb_total` | sum of the image bytes pulled because the target had no cached copy |
| `overhead_ratio` | `(state + image + base-sync bytes) / payload bytes served` |
| `overhead_migration_only` | `(state + image) / payload` (excludes base maintenance) |
| `mean_link_utilisation` | mean over steps of (sum of link demand) / (sum of link capacity) |
| `interrupt_<service>` | interruption ratio for one MEC service |
| `lead_mean_steps` | `migration.start - served_handover.step` (negative = before the handover) |
| `ready_before_handover_pct` | share of migrations that finish before the served handover |
| `post_arrival_lag_*` | steps between the handover and the migration finishing after arrival |
| `duration_over_dwell_*` | migration duration / cell dwell time |
| `cold_target_rate` | share of migrations whose target had no base |
| `restore_steps_mean` | mean extra steps to apply the state and restart the service |
| `bandwidth_time_mb_s` | sum of `state_mb x state_steps + image_mb x pulling_steps` |
| `concurrent_peak` | maximum number of migrations active in the same step |
| `control_plane_flows_per_handover` | (migrations + pulled layers) / handovers |
| `waiting_ratio_mean` | waiting time / migration duration |

---

## 8. Assumptions and limitations

1. **Image caching is warm at t = 0** on the initially occupied nodes.
2. **Linear state growth**; the growth factor is configurable per service.
3. **Pre-copy interruption is policy-defined.** EdgeSimPy natively sets `_available = False`
   when the state flow is created, which happens *after* the controller ran for that step;
   this produces a one-step modelling artefact in the pre-copy strategy that `post_step()`
   repairs before the measurement is taken.
4. **The look-ahead is an oracle.** `_target_coordinates()` reads the true trace, so proactive
   results are an upper bound on what a perfect trajectory predictor would achieve. A real
   predictor must be plugged in at this point and its accuracy swept.
5. **Byte accounting is analytic** (state + missing layers), not sampled from network flows.
   `image_pull_mb` is the sum of the layers still missing on the target, not the whole image.
6. **Delay is sampled from EdgeSimPy.** `User.delays` is only recomputed when the vehicle
   moves or when a migration finishes, so `mean_delay_ms` aggregates the available
   (non-interrupted) configurations; interruptions are counted directly from `_available`.
7. **One registry** is used as the image source. Multi-registry placement is a natural
   extension (EdgeSimPy already supports several registries).
8. **Delta requires a per-node base.** A cold target receives the full state; the old
   "delta is always cheap" assumption has been removed.
9. **Restore cost is linear in the transferred bytes** (`restore_ms_per_mb`) and is added
   to the unavailable window.
10. **Base maintenance is off by default.** `base_maintenance: neighbors` replicates
    snapshots to adjacent nodes and counts the background traffic in `overhead_ratio`;
    this path is implemented but shelved for now.

---

## 9. Extension points

| Goal | Where to change |
|---|---|
| New migration policy (timing / volume / coordinator) | `migration/strategies.py` (add a preset) and `migration/controller.py` |
| Trajectory predictor | override `MigrationController._target_coordinates()` |
| New mobility source (dataset, model) | `mobility/paths.py`, `mobility/taxi.py` |
| New topology (DATA7, other cities) | `topology/graph.py` |
| New MEC service | `services/catalog.py` (the catalogue is the single source of truth) |
| Security mechanisms (obfuscation, batching, padding) | a new layer around `MigrationController`; the observable side-channel is already logged |
| New metrics | `metrics/collector.py` (`sample()` for per-step, `finalize()` for aggregates) |
| New figures | `analysis/plots.py` |
