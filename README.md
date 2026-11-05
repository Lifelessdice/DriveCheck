# DriveCheck

I am building a Python workbench to investigate how sensor quality affects a simple collision-warning algorithm. **M4 is the accepted CPU baseline, supported by local clean-source/new-environment reproduction and actual Windows CI at the recorded M4 revision.** The workflow saves 76 main cases plus five separately evaluated latency diagnostics, full traces/audits and a local HTML report. The recorded M4 checks passed 169 tests locally and remotely. The C1 branch starts from that accepted head observed on local `main`; its newer local checks are recorded separately below. Learner understanding remains separate from technical acceptance.

I work in the original project files using guided code and explanations. My assistant prepares tests and study documents, helps with requested fixes and runs bounded checks when I delegate them. Earlier assistant-created M1 implementation/artifacts have been archived locally; they are separate from my active code and learning evidence.

## C1: completed comparison

After saving the [first estimator block](docs/lessons/c1-block1-state-estimates.md), I explicitly delegated the remaining C1 implementation, verification and local commits, then requested push and main integration. The assistant completed the shared-policy integration, frozen paired runner, offline report, independent evidence audit and clean-source/new-environment reproduction. **All five C1 technical blocks are complete, with hosted CI accepted on 5 November 2026; my independent explanation and M5 presentation remain separate.**

The comparison retains **76 development pairs, 76 separate evaluation pairs and five development diagnostics: 157 pairs / 314 method records**. Both methods receive identical causal observations, clocks and policies. The raw baseline stays the default. Evaluation uses distinct physical configurations and RNG streams selected before its outcomes were inspected.

| Evaluation metric | Raw | Age projection |
| --- | ---: | ---: |
| Useful / late / missed positives | 31 / 2 / 5, out of 38 | 31 / 2 / 5, out of 38 |
| False-warning negative episodes | 26/38 | 35/38 |

Gap MAE improved in 37 pairs, was unchanged in 38 and was unavailable in one. Better current-gap estimates did not improve positive outcome counts and produced nine additional finite-horizon false-warning episodes. The [complete investigation and walkthrough](docs/c1-investigation.md) explains every loss, seed variation, the horizon convention and the constant-speed diagnostic. No real-world safety or significance claim is made.

The final copied-source/hash-locked environment passed **222 tests in 88.287 s**, dependency checks and Ruff. All **55 source inputs**, **14 wheel/package pins**, and **1,424 generated files** matched the recorded reproduction; both independent audits checked **3,302 decision rows, 1,418 machine hashes, three plots and 1,102 local links**. A separate check matched all 243 raw decision/observation/truth files across the 81 saved M4 cases. The original environment and reports were preserved. [Hosted C1 CI](https://github.com/Lifelessdice/DriveCheck/actions/runs/42011728510) passed at `b293a5b`: 222 tests in 33.159 s, dependency checks, Ruff, the M4 report/audit and the complete C1 report/audit.

Generate and audit a report in a new output directory:

```powershell
.\.venv\Scripts\python.exe c1_compare.py --config configs/c1-comparison.json --output-dir outputs/c1-demo
.\.venv\Scripts\python.exe -m tools.verify_c1 outputs/c1-demo
```

Open `outputs/c1-demo/report/report.html`; use a new directory for another run. For a fresh source copy and environment, run `.\.venv\Scripts\python.exe -m tools.reproduce_c1`; optional `--wheelhouse` reuses a project-local wheel cache. See the [reproduction guide](docs/reproduction.md). The [causal integration lesson](docs/lessons/c1-block2-causal-integration.md) retains the detailed code explanation. Assistant implementation and tests do not establish learner mastery.

## Accepted M4 baseline

I saved the guided `release_config.py`, `test_m4_config.py` and `configs/m4-release.json`. Assistant review required no source changes; 14 focused configuration tests and all 145 project tests passed on 1 November 2026. The planner declares 76 pending main cases (38 contact/38 non-contact), preserving M3's native fault settings, jittered latency, seed-base mapping, policies and decision clock. These are inventory counts, not a new warning-results table.

The [first M4 block](docs/lessons/m4-block1-release-plan.md) explains the validated plan. I also saved the [machine-results execution block](docs/lessons/m4-block2-machine-results.md) and generated `outputs/m4-machine/run-a` and `run-b`. Assistant review required no source fixes; eight focused tests and all 153 project tests passed. Each saved run has 343 verified artifact hashes and 344 files; every file matches between runs. Causal traces, independent event scoring, full-horizon fresh-row MAEs and denominator accounting were checked. These are same-machine results, not clean-environment or remote CI evidence.

I saved the [offline-report/CLI block](docs/lessons/m4-block3-offline-report.md) and generated `outputs/m4-release/run-a` and `run-b`. Assistant review required no product fixes: 10 focused tests passed in 3.481 s and all 163 project tests passed in 20.382 s. Both runs complete 76 main cases plus five separate diagnostics. Each has 343 verified machine hashes, 356 package hashes, 357 files and 421 contained local report references; every file matches between runs. All 11 selected plots were individually inspected. Browser-rendered HTML layout was not verified.

The [failure study](docs/failure-study.md) and report show the saved fixed-delay useful→late→missed sequence, including the fresh but clear reading at 6 s and the alarming reading arriving at 6.5 s. `drivecheck.py` supports both M2 and M4; machine evidence and report-package status remain separate.

On 1 November I explicitly delegated the remaining M4 environment, reproduction and CI work to my assistant. It completed the lock/lint setup and reusable reproduction wrapper, removed four unused imports and prepared the Windows CI workflow. The original-environment suite passed 169 tests in 21.173 s; the copied-source/new-environment suite passed 169 tests in 19.545 s. All 42 copied input hashes and 14 installed package versions/wheel hashes match their records and lock. Both regenerated local 357-file reports match byte for byte, including all 11 PNGs from the earlier visual review; each retains 343 machine hashes, 356 package hashes and 421 contained links. Dependency consistency and lint pass. Three separate damaged/incomplete evidence controls fail as expected. See [the reproduction record and commands](docs/reproduction.md). These are assistant-performed checks; test durations do not measure learner study time or establish independent understanding.

[The Windows CI run](https://github.com/Lifelessdice/DriveCheck/actions/runs/41260971755) passed for feature-branch commit `e64b12baf4a4ba5e93a91e2b40541bb7c5df6ed4`: all 169 tests passed in 18.010 s, dependency/lint checks passed, and the full report audit verified 76 main plus five separate diagnostic cases, 343 machine hashes, 356 package hashes, 357 files, 11 plots and 421 local links. This is acceptance of the checked feature-branch revision, not a main merge or a claim of pixel identity across machines.

Observed M4 main results across bases 100/200/300:

| Condition | Positive / negative | Useful / late / missed | False-warning episodes |
| --- | ---: | ---: | ---: |
| clean | 2 / 2 | 2 / 0 / 0 | 2 / 2 |
| noise_low | 6 / 6 | 6 / 0 / 0 | 6 / 6 |
| noise_strong | 6 / 6 | 6 / 0 / 0 | 6 / 6 |
| latency_low | 6 / 6 | 5 / 1 / 0 | 6 / 6 |
| latency_strong | 6 / 6 | 2 / 2 / 2 | 4 / 6 |
| dropout_low | 6 / 6 | 6 / 0 / 0 | 6 / 6 |
| dropout_strong | 6 / 6 | 6 / 0 / 0 | 5 / 6 |

Clean is not triplicated under unused seeds. Scenarios/streams are shared across conditions; these are not independent real-road trials. Reduced negative warnings alone do not establish improvement when useful positive warnings are lost. The five fixed-delay diagnostic arms retain their own policy and summary.

## Reproduce the locked CPU release

From the existing project environment, one command creates a new environment, copies the explicit 42-file source/configuration/tooling/workflow inventory and runs both complete workflows:

```powershell
Set-Location 'E:\DriveCheck'
.\.venv\Scripts\python.exe -E -s -m tools.reproduce
```

With the project interpreter selected, the equivalent command is `python -E -s -m tools.reproduce`. Add `--wheelhouse <existing wheelhouse directory>` to reuse already downloaded wheels. Source filenames remain fixed; the wrapper automatically chooses a fresh `outputs/m4-environment/reproduction-<id>` evidence directory and prints its location. `reproduction.json` records status, hashes and any differing outputs. The existing environment must contain the recorded runtime dependencies for the baseline; [reproduction instructions](docs/reproduction.md) also cover a new checkout, cache reuse and individual report audits.

The supported hash-lock target is CPython 3.14.7 on Windows x64. Local reproduction uses a new source copy and package environment on the same machine; the linked CI run separately verifies a hosted Windows checkout. Other platforms and cross-machine pixel identity remain untested.

## Run the M4 offline report

Use the existing environment. This PowerShell block creates a fresh output name with a timestamp and random suffix; source/configuration filenames stay fixed. The CLI refuses an existing destination.

```powershell
Set-Location 'E:\DriveCheck'
$runId = '{0}-{1}' -f (Get-Date -Format 'yyyyMMdd-HHmmss'), ([guid]::NewGuid().ToString('N').Substring(0, 8))
$outputDir = Join-Path '.\outputs\m4-release' $runId
.\.venv\Scripts\python.exe .\drivecheck.py --config .\configs\m4-release.json --output-dir $outputDir
if ($LASTEXITCODE -ne 0) { throw 'M4 report failed; inspect the saved status and error.' }
Get-Content -LiteralPath (Join-Path $outputDir 'release-manifest.json') -TotalCount 25
```

The readable entry point is `report/report.html` inside that run folder. Keep the whole folder together for its relative evidence/image links. `manifest.json` describes machine execution; `release-manifest.json` is authoritative for report packaging, links and hashes. Local reproduction and remote CI have separate evidence linked above.

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

The driver refuses existing output folders. Its default seed base 100 maps to gap/closing/latency/dropout streams 101/102/103/104 in the main matrix. `--seed-base 200` changes that bundle; `--all-plots` renders all 33 cases instead of the 12 figures selected in advance. Neither option changes warning/scoring rules. M4's complete reproduction workflow above is verified on this machine; a fresh OS or another platform remains untested.

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

The supplied trajectory, observation, replay/TTC, independent-scoring, aligned-error and report checks pass, including the delegated changed-age experiment and saved M3/M4 studies. Negative gaps are virtual overlap of prescribed paths, with no impact response simulated. The M2 CLI remains supported; `drivecheck.py` also dispatches the configurable M4 matrix and report, while `m3_study.py` preserves the bounded M3 study. Local clean-source/new-environment reproduction and the linked Windows CI run pass; combined faults and cross-platform validation remain outside that evidence. Error MAEs equally weight fresh decision rows over the full horizon, including virtual post-contact motion; arrival jitter changes row timing/counts. The diagnostic uses explicitly different settings from the main matrix and is not a claimed improvement or general benchmark. Extreme numeric inputs may fail explicitly rather than produce an unsupported result. Passing supplied tests or reading the explanation does not establish independent implementation or understanding.

The original environment uses Python 3.14.7. The motion model uses the standard library; export plots use Matplotlib and PNG verification uses Pillow. `requirements.txt` records 12 runtime versions; `requirements-lock.txt` binds their selected wheel bytes plus pip 26.2.1 and Ruff 0.14.0. All 14 packages were installed and checked in the new environment and the linked Windows CI job. See [reproduction instructions and evidence](docs/reproduction.md) and [research/dependency decisions](docs/research.md). The verified lock target is Windows x64/CPython 3.14.7.

I completed the original calculation, guided loop and first known-answer test with AI-assisted teaching/templates. The earlier assistant-created full M1 reference was archived when I chose to build in the original files; current lessons, targeted fixes and delegated M4 implementation/verification are attributed separately. The public feature branch has the verified CI result linked above; integration into main remains separate. This is an offline simplified model, with no real-vehicle control or safety-validation claim.
