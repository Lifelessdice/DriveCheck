# CARLA export import and CPU replay

The adapter maps a versioned JSON export into DriveCheck's longitudinal replay pipeline. Import and replay run on the existing CPU environment. Both examples are **hand-authored synthetic fixtures**. Actual CARLA capture compatibility remains unverified. [Contact example](../examples/carla/contact.json) · [Non-contact example](../examples/carla/noncontact.json)

The supported input format is `drivecheck.carla-export.v1`, a DriveCheck JSON interchange contract. A future capture tool must produce this format and be checked against a simulator run.

## Run the examples

Run these commands from the prepared checkout in PowerShell. Choose fresh output directories for repeat runs.

```powershell
Set-Location 'E:\DriveCheck'
.\.venv\Scripts\python.exe carla_replay.py --input examples/carla/contact.json --config configs/carla-replay.json --output-dir outputs/carla-contact-example
if ($LASTEXITCODE -ne 0) { throw 'Contact replay failed; inspect saved evidence.' }
.\.venv\Scripts\python.exe carla_replay.py --input examples/carla/noncontact.json --config configs/carla-replay.json --output-dir outputs/carla-noncontact-example
if ($LASTEXITCODE -ne 0) { throw 'Non-contact replay failed; inspect saved evidence.' }
Invoke-Item -LiteralPath .\outputs\carla-contact-example\report.html
```

The fixture configuration uses 1 s latency, a 1 s TTC warning threshold, a 1.25 s freshness limit, a 4 s pre-contact matching window and a minimum useful lead of 1 s. This is a separate experiment from the frozen C1 comparison.

The contact fixture has gaps of 10, 5 and 0 m at normalized times 0, 1 and 2 s, with closing speed 5 m/s and a declared pair collision at 2 s. With the configured latency, raw first warns at 2 s (late, zero lead). Age projection first warns at 1 s (useful, 1 s lead). The opening fixture has gaps of 10, 15 and 20 m and closing speed −5 m/s. Both methods stay clear.

## Input contract

All objects reject unknown keys. JSON loading rejects duplicate keys, non-finite numbers, booleans in numeric fields and malformed shapes. [Importer](../carla_import.py) · [Known-answer tests](../test_carla_import.py)

| Top-level field | Meaning |
| --- | --- |
| `schema_version` | Exactly `drivecheck.carla-export.v1` |
| `scenario_id` | Safe lowercase identifier for the episode |
| `provenance` | Source kind, declared CARLA version, map/capture identifiers, fixed step or null, complete collision-sensor coverage declaration |
| `units` | `position` in `m`, `velocity` in `m/s`, and `time` in `s` |
| `axis` | Fixed horizontal unit vector defining positive travel direction |
| `actors` | Distinct positive integer `ego` and `lead` IDs |
| `frames` | Ordered world-space states for the two actors at captured frame IDs and elapsed simulation times |
| `collisions` | Ego collision events, including frame/time and the other actor ID |

The exporter declares `kind` as either `synthetic-contract-fixture` or `carla-simulator`, supplies `carla_version`, `map_name` and `capture_id` as nonempty strings, and sets `fixed_delta_seconds` to a positive number or null. The importer requires `collision_sensor_complete` to be true so the event stream can support negative episode scoring. Source declarations are unauthenticated.

Every frame contains `frame`, `elapsed_seconds`, `ego` and `lead`. Each actor state contains `location_m`, `forward`, `velocity_mps` and eight distinct `bbox_world_vertices_m`. All three-vectors are finite. Frame IDs and elapsed times increase strictly. When `fixed_delta_seconds` is declared, elapsed differences must agree with frame increments. Otherwise irregular sample times are retained.

The JSON contract checks heading and axis unit length, and axis horizontality, within `1e-9`. Exporters must normalize lower precision direction vectors. Fixed step comparisons use `1e-9` absolute seconds and `1e-9` relative tolerance. Collision timestamp matching allows `1e-9` seconds only after strict captured time bounds have been checked.

## Geometry and clocks

The importer projects all eight world-space box vertices onto the declared axis. Ego front is the largest ego projection and lead rear the smallest lead projection. Gap is lead rear minus ego front. Closing speed is ego projected speed minus lead projected speed. The first ego-front coordinate becomes the position origin and the first captured simulation timestamp becomes time zero. Original frame IDs and elapsed times remain in the frame map.

The default mapping accepts at most 5° heading error, 0.5 m lateral or height departure from the first ego reference, and 0.5 m/s lateral speed. It rejects reversing and boxes with negligible projected length, width or height. Use it for approximately straight, aligned following episodes.

The importer preserves the original samples. At decision times between captured frames, offline error metrics use piecewise linear interpolation of bumper positions and speeds. Gap and closing speed are derived from that approximate state. Queries are limited to the captured horizon and each fresh decision row has equal weight.

Each collision entry contains `frame`, `elapsed_seconds`, `actor_id` and `other_actor_id`. The event frame must be captured, its timestamp must match, and `actor_id` must identify ego. The first event with the lead as `other_actor_id` supplies the independent contact reference. Other events are counted as ignored diagnostics. An empty set of qualifying events means no recorded pair contact **within the captured horizon**. Event timing has frame resolution, and projected box separation can differ from contact in the physics engine.

## Replay and evidence

Imported actor state supplies **simulated sensor readings**. The shared fault injector adds the configured noise, latency or dropout. Raw and age projection receive identical observations and decision times through the existing arrival queue, freshness gate, TTC rule and scorer. The warning path uses only arrived observations. Offline evaluation alone interpolates actor state.

Each run retains the exact source and configuration bytes, hashes, effective settings, truth, frame mapping, observations, fault records, per-method decisions and the original and used state. Results and the manifest retain method failures. Missing and stale estimates are counted and excluded from error averages. A local HTML report summarizes outcomes and links to the machine-readable evidence and plot.

The CLI accepts project-contained input/configuration paths and a fresh destination under `outputs/`. Validation happens before creating it. Existing destinations, source overwrites and redirected paths outside the allowed tree are rejected. Outputs are local generated artifacts and stay ignored by Git.

## Requirements for a future simulator capture

A capture tool must use the actor transform from the same frame to obtain world vertices of the actor-relative bounding box. Snapshot positions, forward directions, velocities and vertices must describe the same tick. [CARLA 0.9.16 Python API](https://carla.readthedocs.io/en/0.9.16/python_api/)

Capture settings must record the simulation step, synchrony and physics substeps. The collision sensor can report several collisions in one frame. A capture tool must drain and account for all events before declaring complete coverage. [Synchrony and time step](https://carla.readthedocs.io/en/0.9.16/adv_synchrony_timestep/) · [Collision sensor](https://carla.readthedocs.io/en/0.9.16/ref_sensors/#collision-detector)

A future capture tool needs an isolated client environment compatible with its selected CARLA release. The first real capture should verify box projection, frame timing and event coverage against the recorded simulator data.
