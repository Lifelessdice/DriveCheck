# DriveCheck

I am building a Python workbench to investigate how sensor quality affects a simple collision-warning algorithm. **M1, M2 and all five technical M3 blocks are verified locally, with 131 tests passing overall.** The M3 study saves 28 fault-condition cases plus five separately evaluated latency diagnostics, with reproducible data, audits, reports and plots. Technical checks and my demonstrated understanding are recorded separately. M3's final commit/push and main integration remain learner-run steps; no remote CI result is claimed.

I work in the original project files using guided code and explanations. My assistant prepares tests and study documents, helps with requested fixes and runs bounded checks when I delegate them. Earlier assistant-created M1 implementation/artifacts have been archived locally; they are separate from my active code and learning evidence.

## Study and implemented model

The [M1 lesson](docs/lessons/m1-clean-movement.md) covers the implemented motion model. [M2](docs/lessons/m2-warning-and-report.md) adds the implemented report, clean-versus-delay result and age-limit investigation. I delegated that final experiment and requested a plain-language explanation; my independent interpretation remains unassessed. [M3](docs/lessons/m3-fault-suite.md) adds private random streams, individual faults, stop-and-go, boundary/regression tests and the integrated saved study. Its guided implementation includes the earlier targeted repairs described below. On 1 November 2026, assistant review of my saved final driver/tests and outputs required no product changes; seven new tests and all 131 project tests passed. The complete curriculum is indexed in [the study guide](docs/study-guide.md).

## Reproduce the M3 study

Use the existing project environment and a fresh output directory:

```powershell
Set-Location E:\DriveCheck
.\.venv\Scripts\python.exe -m unittest -v
.\.venv\Scripts\python.exe .\m3_study.py --output-dir .\outputs\m3-study\example-01
Start-Process .\outputs\m3-study\example-01\report.html
```

The driver refuses existing output folders. Its default seed base 100 maps to gap/closing/latency/dropout streams 101/102/103/104 in the main matrix. `--seed-base 200` changes that bundle; `--all-plots` renders all 33 cases instead of the 12 figures selected in advance. Neither option changes warning/scoring rules. A clean machine/environment reproduction remains M4 work.

The main matrix crosses four independent contact/non-contact fixtures with seven clean/low/strong single-fault profiles. Every profile has two positive and two negative episodes. The fixed-delay diagnostic uses a separate policy and summary. Each case retains truth identity, settings, full observations/audit/decisions, execution status, score and aligned errors. Shared truth snapshots, configuration, runtime/source provenance, artifact hashes, complete CSV/JSON summaries and a local HTML report accompany the case exports. Failed executions remain unscored in the declared denominator; a valid warning miss is a complete execution.

Observed main-matrix counts for seed base 100:

| Condition | Useful / 2 positives | Late / 2 positives | Missed / 2 positives | False warning / 2 negatives |
| --- | ---: | ---: | ---: | ---: |
| clean | 2 | 0 | 0 | 2 |
| noise_low | 2 | 0 | 0 | 2 |
| noise_strong | 2 | 0 | 0 | 2 |
| latency_low | 1 | 1 | 0 | 2 |
| latency_strong | 0 | 1 | 1 | 2 |
| dropout_low | 2 | 0 | 0 | 2 |
| dropout_strong | 2 | 0 | 0 | 1 |

Both clean negative episodes warn. Strong dropout suppresses one negative warning in this bundle; that does not establish improved reliability. Main policy remains TTC threshold 3 s, maximum age 1.25 s, pre-event window 4 s and useful lead at least 1 s, on the union of source ticks and in-horizon arrivals. The separate diagnostic reproduces useful/useful/late/late/missed under delays 0/1/1.5/2/2.5 s. These small synthetic counts and reused source-index random patterns are not independent-world or sensor-performance estimates.

Review of my saved `outputs/m3-study/run-a` and `run-b` found both complete at 33/33 cases, with all 164 files byte-identical between runs. Each run's 163 artifact hashes, configuration/source hashes and 181 contained local report references matched. Assistant review checked causal selection from the saved observation/decision rows and visually inspected all 12 default figures. Failure-retention/nonzero CLI status, report-failure machine-data retention, preflight, real plots for both motion families and render-only selection are covered by the seven new tests. The full assistant-run suite passed 131 tests in 47.831 s. No product edit, dependency installation or persistent study rewrite was needed for this review; it does not establish my independent understanding or cross-platform reproduction.

`faults.py` validates immutable single-fault settings, creates separate private seeded generators, and transforms ordered truth into observations plus an offline audit. Explicit-draw fixtures check arithmetic independently of a seed. Every source row reserves all four draws and receives an audit row, even when dropped; invalid values and overflow fail visibly. Missing observations preserve the decision schedule, and retained beyond-horizon arrivals remain distinct from dropout. Clean/fixed-delay compatibility with M2 and repeated causal replay are checked. This is synthetic model/test evidence, not measured sensor behaviour or independent learner mastery.

`stop_and_go.py` adds continuous braking, stationary hold, restart acceleration and cruise while ego speed stays prescribed. It emits the existing truth fields, so fault/replay/scoring integration uses the same observation contract. Independent fixtures give contact at 5 s for a 15 m initial gap and no contact through 8 s for an 18 m gap (minimum 2 m at 6 s). A 16 m gap tests tangent contact at 6 s. Continuous phase roots detect events missed by coarse samples; signed virtual paths continue after first contact without impact dynamics.

`m3_regression.py` runs a separate diagnostic with literal contact at 6 s, fixed half-second decisions and unchanged warning/scoring settings across latency conditions. Delays 0/1/1.5/2/2.5 s produce first warnings at 4/5/5.5/6/no time within the horizon: useful/useful/late/late/missed. In the missed case, the alarming reading arrives at 6.5 s while the latest available reading is still fresh but clear. Boundary tests also check arrival/age/window neighbours, older arrivals, causal noninterference, metric denominators and error alignment. `aligned_errors` accepts an optional offline truth callback while preserving its M1 default and full-horizon fresh-row MAEs.

At my request, the assistant repaired the Block 4 file layout: my boundary-test content had been saved under the helper filename, and the regression helper/test module were absent. It preserved the boundary tests byte-for-byte under `test_m3_boundaries.py` and restored the supplied helper and nine regression tests. My saved evaluator callback change was retained. Actual verification on 31 October 2026 passed all 20 Block 4 tests and the full 124-test suite. This is guided work with an explicitly requested assistant repair, not independent implementation or understanding evidence.

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

## Checked reading-age investigation

On 31 October I asked my assistant to run the final M2 experiment and explain the result. It copied the default into `configs/m2-age-075.json`, changing only `warning.max_age_s` from 1.25 s to 0.75 s. The default settings and earlier report were preserved.

```powershell
.\.venv\Scripts\python.exe .\drivecheck.py --config .\configs\m2-age-075.json --output-dir .\outputs\m2-age-075
```

The actual run completed **6/6 cases**, and the full suite passed **64 tests** again. The assistant checked all 40 artifact hashes, source/configuration hashes and 40 local references. Truth and observations match the default run in all six cases; clean decisions are identical. Delayed decisions start unavailable, then every selected reading is stale, with no warning and no eligible fresh-reading error average. Those null averages mean no eligible data, not zero error.

| Setting | Contact warning | Missed contacts | False-warning negative episodes |
| --- | --- | ---: | ---: |
| Clean, either age limit | Useful, lead 1.316625 s | 0/1 | 2/2 |
| Delay 1 s, age limit 1.25 s | Late, lead 0.316625 s | 0/1 | 2/2 |
| Delay 1 s, age limit 0.75 s | No warning | 1/1 | 0/2 |

In plain language: late information made the warning late. Refusing all information older than 0.75 s silenced every delayed warning, including the collision warning, because every delayed reading was already 1 s old on arrival. The reduction in false-warning episodes comes with a missed contact. These warnings do not change the cars' prescribed movement. This is a reproducible limitation of this small synthetic baseline, not an improvement claim or a recommended driving setting.

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

The supplied trajectory, observation, replay/TTC, independent-scoring, aligned-error and report checks pass, including the delegated changed-age experiment and saved M3 study. Negative gaps are virtual overlap of prescribed paths, with no impact response simulated. The existing M2 CLI is preserved; `m3_study.py` covers the bounded M3 matrix and separate diagnostic. Combined faults, a general configurable release command, clean-environment reproduction and remote CI remain later work. Error MAEs equally weight fresh decision rows over the full horizon, including virtual post-contact motion; arrival jitter changes row timing/counts. The diagnostic uses explicitly different settings from the main matrix and is not a claimed improvement or general benchmark. Extreme numeric inputs may fail explicitly rather than produce an unsupported result. Passing supplied tests or reading the explanation does not establish independent implementation or understanding.

The existing environment uses Python 3.14.7. The motion model uses the standard library; export plots use the retained Matplotlib installation and PNG verification uses Pillow. `requirements.txt` records the 12 installed runtime dependency versions and was checked against the environment. It is a version snapshot, not a wheel-hash lock or fresh-environment reproduction result. See [research and historical dependency decisions](docs/research.md). Fresh-environment/remote CI evidence remains later work.

I completed the original calculation, guided loop and first known-answer test with AI-assisted teaching/templates. The earlier assistant-created full M1 reference was archived when I chose to build in the original files; current lessons and targeted assistant fixes are attributed separately. The GitHub repository is public; no remote CI result is claimed. This is an offline simplified model, with no real-vehicle control or safety-validation claim.
