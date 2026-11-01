# My DriveCheck study guide

The sections below are complete study-ready lessons that I follow at my own pace. My assistant prepares explanations, guided code, meaningful exercises, commands, expected checks and debugging guidance; I implement and run the project. I can work through a full block without replying between commands and ask for help whenever I need it.

Current technical checkpoint, 1 November 2026: M4's technical checks are accepted on `feature/m4-reproducible-release`, including actual [environment/reproduction checks](reproduction.md) and Windows CI. I explicitly delegated the remaining M4 setup/reproduction/CI to my assistant. Both local suites pass 169 tests (21.173 s and 19.545 s); 42 copied inputs and 14 package pins/wheel hashes match. The two local 76-main/five-diagnostic reports have 357 byte-identical files, 343 machine hashes, 356 package hashes, 421 contained links and 11 PNGs matching the inspected figures. Negative evidence controls reject damage/incompleteness. Browser layout and independent understanding remain unverified; integration into `main` has not been performed.

[The Windows CI run](https://github.com/Lifelessdice/DriveCheck/actions/runs/41260971755) passed for feature-branch commit `e64b12baf4a4ba5e93a91e2b40541bb7c5df6ed4`: all 169 tests passed in 18.010 s, dependency/lint checks passed, and the full report audit verified 76 main plus five separate diagnostic cases, 343 machine hashes, 356 package hashes, 357 files, 11 plots and 421 local links. The result is revision-specific; learner understanding and main integration remain separate.

I work in the original project files, without a required duplicate practice implementation. At my request on 27 October, the earlier assistant M1 reference was archived and learner work restored; subsequent guided M1–M3 work has its own recorded acceptance. Keep the current code/environment and observed checkpoints rather than restoring that historical starting point. Reference runs alone do not establish my understanding.

## Section order

| Section | Complete lesson | What I work toward |
| --- | --- | --- |
| M1 | [Clean movement](lessons/m1-clean-movement.md) | Clean truth, braking/contact and non-contact fixtures, saved data and plot |
| M2 | [Warning and first report](lessons/m2-warning-and-report.md) | Causal readings, time to collision, independent scoring and a first report |
| M3 | [Fault suite](lessons/m3-fault-suite.md) | Noise, latency, dropout, stop-and-go and regression cases |
| M4 | [Reproducible CPU release](lessons/m4-reproducible-release.md) | Complete experiments, CLI/report, failure study, environment and CI |
| C1 | [Fair comparison](lessons/c1-fair-comparison.md) | One evidence-led comparison with separate tuning and evaluation |
| M5 | [Portfolio and demo](lessons/m5-portfolio-and-demo.md) | Honest explanations, results, demonstration and review |

All six complete lesson documents are ready. The lesson sequence, worked fixtures, shared fault/seed adapters, comparison counts/metrics and local links have been reviewed. I start with M1 and work through each section at my own pace, asking questions when useful. A ready lesson does not mean its project code, checks or learning criteria are complete. M0's recorded foundation work is retained; I do not restart setup.

## Shared interfaces and later proposals

M1–M3 implement the truth/observation/replay/warning/scoring contracts. `drivecheck.py` now dispatches M2 to `experiments.py` and M4 to `release_runner.py` followed by `release_report.py`; M3 keeps its accepted separate study driver. Machine execution and report-package manifests have distinct responsibilities. The current M4 blocks supersede historical aliases, seed mappings and parameter examples in the original lesson. C1 comparison remains later learner work.

- Implemented truth fields: `scenario_id`, `sample_id`, `time_s`, `ego_front_x_m`, `lead_rear_x_m`, `ego_speed_mps`, `lead_speed_mps`, `gap_m`, `closing_speed_mps`. SI units and positive forward axis apply. Independent contact events come from clean continuous trajectories within the declared horizon.
- `observations.py`: `Observation` records scenario/sample IDs, measurement/arrival times, gap and closing speed. Dropout omits a reading and preserves source IDs/time; it never becomes zero gap. Fault configuration and stream seeds are stored separately.
- `replay.py`: consumes arrivals only when `arrival_time_s <= decision_time_s`, ordered by arrival and sample ID, and selects the newest measurement. `ReplayResult.decisions` retains selected timestamps, numeric values, age and unavailable/stale reasons.
- `warning_policy.py`: makes causal decisions using arrived observations/current time, holding raw values without extrapolation. Decisions include sample/measurement/arrival times, age, gap/closing speed, TTC, warning and reason.
- `evaluation.py`: scores independent contact/horizon references with exclusive useful/late/missed outcomes and false-warning negative episodes. Counts/rates preserve eligible denominators; full-horizon MAEs compare fresh held readings against truth at decision time. Thresholds/windows are experimental conventions.
- `experiments.py`/`reporting.py` retain M2; `release_config.py` enumerates M4, `release_runner.py` saves all statuses/traces and `release_report.py` verifies saved evidence and packages local HTML/plots. The CLI uses `--config` and a fresh `--output-dir`. Source filenames stay fixed; the README's PowerShell example generates only the output-folder name.
- C1 processes the same causal streams and uses the same warning/scoring policy. Choose one method from an observed failure; a Kalman filter is optional. Tuning and evaluation cases/seeds stay separate, and a comparison that loses is a valid result.

## How I use a block

Read the explanation and worked example, implement the guided changes, make the specified meaningful attempt, run the entire check block and inspect the saved output. Compare against the independently calculated expected answer and debug discrepancies. Send my code/output/questions when I want review; I do not need permission to proceed through the instructions.

All commands are run from `E:\DriveCheck` unless explicitly stated. Future expected output is labelled as expected. Actual test results are recorded only after a real run. My assistant maintains documentation from observed evidence and does not infer understanding from generated tests.

Git, publication and remote CI remain my responsibility. Local configuration or a lesson about CI does not establish a successful remote run. CARLA and interactive UI remain optional later work.

My explicit 1 November delegation covers the remaining M4 setup/reproduction/CI and its requested commit/push on the current branch. The run linked above supplies actual remote evidence for its checked revision; the learner workflow for C1/M5 is unchanged. The [one-command reproduction guide](reproduction.md) distinguishes observed local proof from new-checkout instructions.
