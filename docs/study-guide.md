# My DriveCheck study guide

The sections below are complete study-ready lessons that I follow at my own pace. My assistant prepares explanations, guided code, meaningful exercises, commands, expected checks and debugging guidance; I implement and run the project. I can work through a full block without replying between commands and ask for help whenever I need it.

The workspace includes AI-created M1 reference code, dependencies and plots. They are preserved reference material, separate from my own implementation and understanding. My reviewed learner work currently covers the original calculation/test, guided five-row table and first CSV save/read-back; the broader M1 learning work remains in progress.

Latest preference, 2026-10-27: I work in the original project files, without a required duplicate practice implementation. At my request, the assistant's completed M1 code/artifacts were archived privately and the original learner code restored. I resume at the partial sampler in `motion.py` and extend `test_motion.py`. The environment is retained; setup is not restarted. Historical reference runs do not establish that the restored code or my pending changes pass new tests.

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

## Shared proposed interfaces for the later lessons

These are curriculum conventions to keep the examples coherent, not a claim that the later modules exist. I can refine them with my coach when implementing a section, then update dependent lessons explicitly.

- Existing M1 reference truth fields: `scenario_id`, `sample_id`, `time_s`, `ego_front_x_m`, `lead_rear_x_m`, `ego_speed_mps`, `lead_speed_mps`, `gap_m`, `closing_speed_mps`. SI units and positive forward axis apply. Independent contact events come from clean continuous trajectories within the declared horizon.
- Proposed `observations.py`: an `Observation` record containing `scenario_id`, `sample_id`, `measurement_time_s`, `arrival_time_s`, `gap_m`, `closing_speed_mps`. Dropout omits a reading and preserves the time grid/source IDs; it never becomes a zero gap. Fault configuration/seed are recorded separately.
- Proposed `replay.py`: release readings only when `arrival_time_s <= decision_time_s`, ordered by arrival and sample ID. State clearly how out-of-order measurement times, stale values, duplicates and unavailable readings are handled.
- Proposed `warning_policy.py`: causal decisions using arrived observations/current decision time only. Suggested decision fields are `decision_time_s`, `measurement_time_s`, `observation_age_s`, `ttc_s`, `is_warning`, `reason`. Use this module name to avoid shadowing Python's standard-library `warnings` module.
- Proposed `evaluation.py`: score decisions against independent reference contact/horizon, with explicit useful/late/missed/false-warning episode rules. Keep per-case outcomes and denominators. Thresholds/windows are documented experimental choices, not driving advice or regulatory values.
- Proposed `experiments.py` and `reporting.py`: enumerate cases/seeds/fault settings, save every result including failed/partial cases, and produce an offline report. A suggested later entry point is `drivecheck.py`; CLI spellings in lessons remain proposed until implemented and checked.
- C1 processes the same causal streams and uses the same warning/scoring policy. Choose one method from an observed failure; a Kalman filter is optional. Tuning and evaluation cases/seeds stay separate, and a comparison that loses is a valid result.

## How I use a block

Read the explanation and worked example, implement the guided changes, make the specified meaningful attempt, run the entire check block and inspect the saved output. Compare against the independently calculated expected answer and debug discrepancies. Send my code/output/questions when I want review; I do not need permission to proceed through the instructions.

All commands are run from `E:\DriveCheck` unless explicitly stated. Future expected output is labelled as expected. Actual test results are recorded only after a real run. My assistant maintains documentation from observed evidence and does not infer understanding from generated tests.

Git, publication and remote CI remain my responsibility. Local configuration or a lesson about CI does not establish a successful remote run. CARLA and interactive UI remain optional later work.
