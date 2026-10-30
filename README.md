# DriveCheck

I am building a Python workbench to investigate how sensor quality affects a simple collision-warning algorithm. **M1 clean motion and the default six-case M2 report are locally verified, with 64 tests passing.** One command now generates truth, clean or fixed-delay observations, causal warning decisions, independent event scores, aligned errors, plots and an offline comparison report. Technical checks and my demonstrated understanding are recorded separately.

I work in the original project files and implement/run the changes myself. My assistant prepares the explanations, guided code, tests and study documents. Earlier assistant-created M1 implementation/artifacts have been archived locally; they are separate from my active code and learning evidence.

## Study and implemented model

The [M1 lesson](docs/lessons/m1-clean-movement.md) covers the implemented motion model. I am now reviewing [M2](docs/lessons/m2-warning-and-report.md), including the implemented report and its clean-versus-delay result. My changed-setting exercise and explanation remain separate learning work. The complete curriculum is indexed in [the study guide](docs/study-guide.md). No duplicate practice implementation or environment restart is required.

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

Checks include simultaneous/overtaking arrivals, exact arrival/age/threshold boundaries, zero horizon, invalid clocks, TTC overflow and future-value noninterference. This is guided implementation with a targeted assistant repair and verification.

## Independent warning scoring

`evaluation.py` matches warning decision timestamps against independently specified contact events. Its experimental scoring policy uses a 4 s pre-contact window and a 1 s minimum useful lead, with inclusive boundaries. It distinguishes useful, late and missed contacts, warning activations versus true decision rows, and negative episodes with/without a warning. A negative means no reference contact within the declared horizon, not absence of eventual contact.

Per-condition summaries preserve planned, scored and unscored positive/negative counts and unsuccessful case IDs/statuses. Rates retain numerator and eligible scored denominator; a zero denominator produces null. Invalid completed scores are rejected instead of silently excluded. Reference `None` means no contact in the horizon; a numeric zero means contact at the start.

On 31 October 2026 I supplied five scoring errors and requested repair. My assistant reproduced them and moved the numeric horizon comparison inside the existing non-null reference guard in `evaluation.py`. Existing tests, replay and warning policy were unchanged. The focused scoring suite then passed **12 tests**, and the complete project suite passed **58 tests**. Integration fixtures check all three M1 cases under clean/one-second-delay conditions, including useful versus late braking warnings and the finite-horizon false-warning convention. The later report checkpoint below includes those results in saved artifacts.

Before the scoring Git checkpoint, I requested another review and explanatory comments. My assistant added neutral comments/docstrings to the scorer and metric tests, confirmed identical executable syntax trees excluding docstrings, and reran all 58 tests successfully. Matching rules, calculations and test assertions were preserved.

```powershell
.\.venv\Scripts\python.exe -m unittest -v test_evaluation
```

## Run the M2 comparison report

From the project folder, use the existing environment and a **new output directory** for each run:

```powershell
Set-Location 'E:\DriveCheck'
.\.venv\Scripts\python.exe -m unittest -v
.\.venv\Scripts\python.exe .\drivecheck.py --config .\configs\m2-experiment.json --output-dir .\outputs\m2-repeat
```

Open `outputs/m2-repeat/report.html` locally. If that directory already exists, choose another name; the runner rejects reuse before writing. `experiments.py` validates the configuration, enumerates all cases and retains failed/unscored rows. `reporting.py` saves local HTML/PNGs, CSV timelines, JSON results, effective settings and source/runtime provenance. A partial or failed run returns a nonzero CLI status. Generated outputs are ignored by Git.

On 31 October I supplied the saved report block and an import failure. My assistant renamed the misspelled `drivehceck.py` to `drivecheck.py` and corrected the helper name/parameter to `aligned_errors(decisions, scenario)`. It preserved test expectations, then ran **6 report tests and all 64 project tests successfully**. Its normal CLI run completed **6/6 cases** in `outputs/m2-first`. Read-back checks verified all 40 artifact hashes, all 40 local report references, configuration/source hashes and identical paired clean/delayed truth. All six timelines and three distinct truth plots were visually reviewed; endpoint markers at the right border are partly clipped, so CSVs retain the precise terminal values. Repeatability tests compare canonical CSV/JSON data in this environment.

The saved default result is:

| Scenario | Condition | First warning | Outcome | Matched lead | Gap MAE | Closing-speed MAE |
| --- | --- | ---: | --- | ---: | ---: | ---: |
| `constant_speed_original` | clean | 3 s | false-warning episode | — | 0 m | 0 m/s |
| `constant_speed_original` | delay 1 s | 4 s | false-warning episode | — | 5 m | 0 m/s |
| `lead_braking_contact` | clean | 2 s | useful | 1.316625 s | 0 m | 0 m/s |
| `lead_braking_contact` | delay 1 s | 3 s | late | 0.316625 s | 12.5 m | 3 m/s |
| `lead_braking_noncontact` | clean | 7 s | false-warning episode | — | 0 m | 0 m/s |
| `lead_braking_noncontact` | delay 1 s | 8 s | false-warning episode | — | 7.5 m | 2.5 m/s |

The one-second delay changes the contact warning from useful to late under the declared 1 s minimum lead. Neither condition misses that contact, but the delayed condition has **1/1 contacts without a useful warning**, compared with 0/1 clean. Each condition has 2/2 false-warning negative episodes under the finite-horizon convention. These three synthetic scenarios do not estimate real-world warning quality.

MAE means mean absolute error. It compares each fresh held reading with truth at the **decision time**, giving equal weight to eligible decision rows across the full horizon, including virtual post-contact motion. Delayed cases have one unavailable initial row each; stale/unavailable rows are counted and excluded, with null MAE when none are eligible. This is distinct from checking whether a delayed sensor copied its original measurement correctly.

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

The supplied trajectory, observation, replay/TTC, independent-scoring, aligned-error and report checks pass. Negative gaps are virtual overlap of prescribed paths, with no impact response simulated. Sensor support currently copies exact gap/closing-speed values with zero or fixed delivery delay. Noise/dropout, stop-and-go and the expanded fault suite belong to M3. My interpretation and changed-setting exercise remain pending; passing supplied tests does not establish independent implementation or understanding.

The existing environment uses Python 3.14.7. The motion model uses the standard library; export plots use the retained Matplotlib installation and PNG verification uses Pillow. `requirements.txt` records the 12 installed runtime dependency versions and was checked against the environment. It is a version snapshot, not a wheel-hash lock or fresh-environment reproduction result. See [research and historical dependency decisions](docs/research.md). Fresh-environment/remote CI evidence remains later work.

I completed the original calculation, guided loop and first known-answer test with AI-assisted teaching/templates. The earlier assistant-created full M1 reference was archived when I chose to build in the original files; current lessons and targeted assistant fixes are attributed separately. The GitHub repository is public; no remote CI result is claimed. This is an offline simplified model, with no real-vehicle control or safety-validation claim.
