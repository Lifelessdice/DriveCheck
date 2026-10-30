# DriveCheck

I am building a Python workbench to investigate how sensor quality affects a simple collision-warning algorithm. **M1 clean motion and M2's observation, causal-replay and TTC-warning blocks are verified.** The active project generates checked truth data, configuration and labelled plots for three study cases, creates separate clean or fixed-delay observations, and produces warning decisions using only arrived readings. Independent scoring and the first comparison report remain M2 work. Technical checks and my demonstrated understanding are recorded separately.

I work in the original project files and implement/run the changes myself. My assistant prepares the explanations, guided code, tests and study documents. Earlier assistant-created M1 implementation/artifacts have been archived locally; they are separate from my active code and learning evidence.

## Study and implemented model

The [M1 lesson](docs/lessons/m1-clean-movement.md) covers the implemented motion model. I am now following [M2](docs/lessons/m2-warning-and-report.md), with observations, replay and the TTC policy implemented. The complete curriculum is indexed in [the study guide](docs/study-guide.md). No duplicate practice implementation or environment restart is required.

`motion.py` contains my original gap function, constant-speed and lead-braking trajectories, immutable scenario/truth records and analytic contact-event detection. `scenarios.py` pairs each case with independently specified reference values. `m1.py` checks those values and exports full truth CSVs, JSON configuration/provenance and PNG plots, with artifact hashes in a run manifest. Following the supplied lessons, I added these modules and tests, with targeted assistant fixes/review.

On 28 October 2026 my assistant ran all **24 tests successfully**, verified my saved study outputs against their configuration, source and artifact hashes, and visually inspected all three plots. Integration tests also check a failed reference, rejected output destinations and repeated exports with identical hashes on this machine. This is guided implementation with assistant verification; my explanation and independent transfer remain separate learning evidence.

The braking contact fixture has an independently calculated event at `sqrt(11) = 3.3166247903554 s`, between its saved 3 s and 4 s rows. A separate fixture remains non-contact through 8 s but contacts at 10 s if extended. Contact labels therefore apply to the declared horizon. Phase endpoint rounding uses 32 ULPs of the actual endpoint time scale.

## Sensor observations: first M2 block

`observations.py` defines immutable readings with scenario/sample IDs, measurement time, arrival time, gap in metres and closing speed in m/s. The fixed-delay adapter copies numeric truth values into new records and changes arrival time only. It preserves truth, source IDs and storage order. Context checks reject duplicate IDs/times, mixed scenarios and measurements beyond the declared horizon; delivery after the horizon remains a valid logged observation. Signed gap/closing speed, empty streams and missing IDs have explicit treatment.

For the braking-contact case, a reading measured at 2 s contains gap 17.5 m and closing speed 10 m/s. With one-second latency it arrives at 3 s, when its measurement age is 1 s. Replay enforces this availability boundary before passing a reading to the warning policy.

On 30 October 2026 my assistant inspected the saved supplied-code implementation, ran `python -m unittest -v test_m2` (**10 tests, OK**) and the full `python -m unittest -v` suite (**34 tests, OK**) through the project interpreter. A separate direct check confirmed the known delayed reading, unchanged truth, unordered source preservation, beyond-horizon delivery and rejected computed-arrival overflow. No product code/tests were edited for verification. This supports the bounded observation contract, not complete M2 acceptance or independent design/mastery.

At my subsequent request, the assistant added neutral technical comments/docstrings to the observation module and its tests. Before/after syntax-tree checks, excluding docstrings, confirmed identical executable structure; all 34 tests passed again. These documentation edits explain the existing behaviour and do not add replay or warning functionality.

```powershell
.\.venv\Scripts\python.exe -m unittest -v test_m2
```

## Causal replay and TTC warnings

`replay.py` builds a decision clock from scheduled sample times and in-horizon arrivals, validates its endpoints/order, and consumes all arrived records before each decision. It selects the greatest measurement time, so an older packet arriving later cannot replace newer information. `ReplayResult` holds the decision timeline and ignored-old/beyond-horizon arrival counts; offline consumers use `result.decisions`.

`warning_policy.py` uses only the selected observation and decision time. The baseline holds measured values without extrapolation. Its experimental settings are a TTC threshold of 3 s and maximum observation age of 1.25 s, both inclusive. Unavailable/stale states retain an explicit reason and null TTC; fresh nonpositive gap warns with TTC zero; positive gap with nonpositive closing speed has no finite TTC. These settings are study conventions, not driving recommendations.

On 30 October 2026 I supplied a failing replay run and requested a fix. My assistant reproduced nine errors and repaired the endpoint comparison, missing strict-time-order guard and misspelled `latest` initialization in `replay.py`; public parameter spellings were aligned with the supplied interface. The existing warning policy, observations and all test assertions were unchanged. The focused replay/policy suite then passed **12 tests**, and the complete project suite passed **46 tests**, both through the project interpreter. Existing fixtures verify first warnings at 2, 2.5 and 3 s for latency 0, 0.5 and 1 s, respectively; these are timing checks, not a scored performance report.

```powershell
.\.venv\Scripts\python.exe -m unittest -v test_replay
```

Checks include simultaneous/overtaking arrivals, exact arrival/age/threshold boundaries, zero horizon, invalid clocks, TTC overflow and future-value noninterference. This is guided implementation with a targeted assistant repair and verification. Independent reference-event scoring and a complete clean-versus-delay report remain pending.

## Run the existing baseline

Use the existing project environment from PowerShell:

```powershell
Set-Location 'E:\DriveCheck'
.\.venv\Scripts\python.exe .\motion.py
.\.venv\Scripts\python.exe -m unittest -v
.\.venv\Scripts\python.exe .\m1.py
```

The console table is:

```text
time_s,gap_m
0.0,30.0
1.0,25.0
2.0,20.0
3.0,15.0
4.0,10.0
```

Both vehicles move forward on the same axis. Bumper gap is the distance from the ego front to the lead rear. The ego travels at 20 m/s and the lead at 15 m/s, so the original 30 m gap decreases by 5 m each second. After two seconds, separate travel distances give `30 + 30 - 40 = 20 m`, the fixed answer in the original test.

Five samples at one-second spacing span four seconds because the initial state is included. My first `outputs/constant_speed.csv` snapshot is preserved. Generated outputs are ignored by Git.

The M1 command writes three CSV/JSON/PNG sets and `manifest.json` to `outputs/m1-study/`:

| Case | Rows | Horizon | First contact within horizon | Final gap |
| --- | ---: | ---: | ---: | ---: |
| `constant_speed_original` | 5 | 4 s | None | 10 m |
| `lead_braking_contact` | 6 | 5 s | 3.3166247903554 s | -32.5 m |
| `lead_braking_noncontact` | 9 | 8 s | None | 20 m |

Each sidecar records SI units, bumper-axis/sign conventions, sampling/horizon rules, independent and computed answers, source/test/requirements hashes, installed versions and no randomness. A successful run has manifest status `complete` with matching artifact hashes; a failed run can leave older files in a reused folder, so file existence alone is insufficient.

## Current limits and attribution

The supplied trajectory, contact/non-contact, export, observation and replay/TTC checks pass. Negative gaps are virtual overlap of prescribed paths, with no impact response simulated. Sensor support currently copies exact gap/closing-speed values with zero or fixed delivery delay. Independent scoring and the complete clean-versus-delay report remain unimplemented; noise/dropout and the expanded fault suite belong to M3. Passing supplied tests does not establish independent implementation or understanding.

The existing environment uses Python 3.14.7. The motion model uses the standard library; export plots use the retained Matplotlib installation and PNG verification uses Pillow. `requirements.txt` records the 12 installed runtime dependency versions and was checked against the environment. It is a version snapshot, not a wheel-hash lock or fresh-environment reproduction result. See [research and historical dependency decisions](docs/research.md). Fresh-environment/remote CI evidence remains later work.

I completed the original calculation, guided loop and first known-answer test with AI-assisted teaching/templates. The earlier assistant-created full M1 reference was archived when I chose to build in the original files; current lessons and targeted assistant fixes are attributed separately. The GitHub repository is public; no remote CI result is claimed. This is an offline simplified model, with no real-vehicle control or safety-validation claim.
