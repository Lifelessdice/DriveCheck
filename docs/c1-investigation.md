# C1: better gap estimates can still produce more warning episodes

Investigated 4 November 2026. The assistant implemented and checked the remaining C1 work after my explicit delegation. I had saved the first estimate module and tests from the supplied teaching block. This report describes technical evidence; my independent explanation and transfer exercise remain separate.

## Question and baseline failure

The M4 [failure study](failure-study.md) showed an exact sensor whose old values delayed a warning. In its strongest fixed-delay diagnostic, the last decision at 6 s selected a 3 s measurement: gap 15 m, closing speed 5 m/s, age 3 s. It was eligible under that diagnostic's inclusive age limit, but held-value TTC was 3 s, above the fixed 2 s threshold. The more alarming 4 s reading arrived at 6.5 s, after the 6 s horizon.

I investigated one question: does projecting an eligible old gap to the current decision time address this mechanism, and what changes on the other cases? The alternative is:

`estimated_gap_now = measured_gap - measured_closing_speed * measurement_age`.

Closing speed and source timestamps are unchanged. This is constant-closing-speed extrapolation, not a Kalman filter, noise smoother or learned model. It has no tunable parameters. The displacement reasoning follows [OpenStax](https://openstax.org/books/university-physics-volume-1/pages/3-4-motion-with-constant-acceleration); the following-vehicle TTC ratio is documented by [SUMO](https://sumo.dlr.de/docs/Simulation/Output/SSM_Device.html#ttc). Those references do not validate this project's thresholds or safety.

For example, at decision time 4 s in that diagnostic, source ID 1 was measured at 1 s, arrived at 3.5 s, and said 25 m / 5 m/s. Its age is 3 s. Raw TTC is 5 s; projection uses `25 - 5*3 = 10 m`, giving TTC 2 s. Independent contact is at 6 s. The observed projected warning is useful with 2 s lead, without using a reading before its arrival or passing truth into the warning policy.

## Frozen design and fair inputs

The method and evaluation design were selected before inspecting final evaluation outcomes. The configuration is [configs/c1-comparison.json](../configs/c1-comparison.json); its canonical SHA-256 is `8bf3c4aaaa9395ee66c2a75a4e52a554c94d47fe111f404af5a9dcddd12bef27`. Each run writes the selection, complete case plan, configuration and source hashes before executing either method.

| Split | Physical cases and seed bases | Paired episodes |
| --- | --- | ---: |
| Development | Original four M4 configurations; bases 100/200/300 already inspected in M4 | 76 |
| Evaluation | Four distinct scaled configurations; bases 1000/2000/3000 | 76 |
| Development diagnostics | Original five fixed-delay arms with their own fixed policy | 5 |
| Total | Both raw and projection retained for every pair | 157 pairs / 314 method records |

The seven main conditions are clean, low/strong noise, low/strong jittered latency and low/strong dropout. Clean runs once per scenario with a null case seed; the six stochastic conditions each use three bases. Thus each main split has `4 * (1 + 6*3) = 76` episodes, comprising 38 positive and 38 negative references. Stream seeds retain M4's base+1..4 mapping. Validation rejects overlapping derived stream bundles between development and evaluation.

The evaluation cases use the analytic similarity transform `x'=1.5x`, `t'=1.25t`: speeds scale by 1.2 and accelerations by 0.96. Contact times scale by 1.25, final gaps by 1.5, and source sampling intervals/horizons by 1.25. These expected answers follow the original independent derivations; the continuous solvers check them before warnings run. This changes physical parameters rather than only renaming scenario IDs. The holdout is still a closely related synthetic construction, not evidence about unseen real traffic families.

Within each pair, the same truth, fault configuration, exact immutable observations, omitted samples, decision clock and independent reference are used. Observations are generated once; input identities are checked around each method. Both reuse the same arrival queue, newest-measurement rule, source-age gate and numerical TTC branches. The default raw API remains usable and is compared with the raw adapter. Failed methods remain in the inventory with explicit status rather than becoming zero-error successes or disappearing.

The main policy remains TTC threshold 3 s, maximum source age 1.25 s, event window 4 s and useful lead 1 s, using source sample times plus in-horizon arrival times. The diagnostics retain threshold 2 s, age 3 s, window 3 s and useful lead 1 s on a fixed 0.5 s clock. Their results are never pooled into the main evaluation denominator.

## Complete evaluation results

All 76 evaluation pairs completed; there were no failed/partial method records.

| Metric | Raw | Projection |
| --- | ---: | ---: |
| Useful positive episodes | 31/38 | 31/38 |
| Late positive episodes | 2/38 | 2/38 |
| Missed positive episodes | 5/38 | 5/38 |
| Positives without a useful warning | 7/38 | 7/38 |
| False-warning negative episodes | 26/38 | 35/38 |

Positive outcome categories were unchanged in all 38 paired positives. Among pairs where both methods gave useful warnings, earliest matched lead improved in 3 and was unchanged in 28. Seven positive pairs lacked a paired useful match and are excluded from this lead comparison, but remain visible as late/missed outcomes above.

Gap MAE improved in 37 evaluation pairs, was unchanged in 38 and had no available estimate in one pair. No pair had worse gap MAE on this particular matrix. Closing-speed MAE was unchanged in 75 pairs and unavailable in the same remaining pair, consistent with the method leaving closing speed unchanged. The unavailable pair was `evaluation-013`, strong latency on the contact braking case at base 3000; absence of eligible inputs is not zero error.

For negative warning outcomes, projection lost 9 pairs, won none and left 29 unchanged. The complete machine table and HTML retain every case, full seed/settings, errors and source coverage. There is no single aggregate claim that the alternative won.

### Seed-level variation

The four clean pairs are deterministic: both methods give 2/2 useful positives and 2/2 false-warning negatives. The remaining stochastic results are:

| Evaluation base | Useful / late / missed positives, both methods | Raw false warnings | Projected false warnings |
| --- | ---: | ---: | ---: |
| 1000 | 11 / 0 / 1, out of 12 | 9/12 | 12/12 |
| 2000 | 10 / 0 / 2, out of 12 | 8/12 | 11/12 |
| 3000 | 8 / 2 / 2, out of 12 | 7/12 | 10/12 |

These are complete controlled seed results, not independent real-road samples or a statistical significance claim. Families, source trajectories and standardized random streams are deliberately reused across conditions.

## Trace one actual warning loss

`evaluation-027` is a scaled braking/non-contact case with low jittered latency and base 1000. Its horizon is 10 s. At that last decision:

| Evidence | Value |
| --- | ---: |
| Source ID / measurement time | 7 / 8.75 s |
| Arrival time | 9.047554402427377 s |
| Source age | 1.25 s, eligible |
| Measured gap / closing speed | 45 m / 12 m/s |
| Raw TTC | 3.75 s, clear |
| Projected gap / TTC | 30 m / 2.5 s, warning |

The current true gap is 30 m, so the projection is correct at that instant. Across the episode, its gap MAE is about 0.99145 m versus raw 6.91937 m. Nevertheless, the extra warning changes the finite-horizon negative classification from clear to false-warning episode.

This exposes a property of the scoring convention: no contact occurs within the declared 10 s horizon, so any warning in that negative episode counts as false. Continuing the prescribed motion would give contact at 12.5 s. The classification does not prove that a real driver should ignore that warning or that projection physically overestimated the risk. Horizon and warning-policy semantics must accompany the numbers.

The other warning losses are `evaluation-028`, `evaluation-029`, `evaluation-030`, `evaluation-035`, `evaluation-036`, `evaluation-037` and `evaluation-038` on the same negative braking family, and `evaluation-069` on stop-and-go/non-contact. Every one remains in the report. A separate unit counterexample also preserves a changing-speed situation where projection increases gap error: true gap 12.5 m, raw 15 m and projected 5 m, giving errors 2.5 m versus 7.5 m.

## Development and regression results

The 76 development pairs have the same positive outcome counts under both methods: 33 useful, 3 late and 2 missed out of 38. False-warning episodes rise from 35/38 to 36/38. These cases informed the question and remain development evidence.

| Fixed diagnostic delay | Raw first warning / outcome | Projection first warning / outcome |
| --- | --- | --- |
| 0 s | 4 s / useful | 4 s / useful |
| 1 s | 5 s / useful | 4 s / useful |
| 1.5 s | 5.5 s / late | 4 s / useful |
| 2 s | 6 s / late | 4 s / useful |
| 2.5 s | None / missed | 4 s / useful |

In the strongest diagnostic both methods retain three pending arrivals beyond the horizon. On the same eight eligible decision rows, raw gap MAE is 13.75 m and projected MAE is 0 m; five earlier decisions remain unavailable. This intentionally constant-speed fixture matches the model's assumption. It explains the mechanism but cannot establish generalization.

## What was checked and how to reproduce it

The initial original-environment suite passed 221 tests in 256.031 s. A reporting-only repair then added one test: if no gap-MAE loss exists, the plot selection includes the first false-warning regression instead of omitting a loss figure. A visual-QA repair made warning ticks and final values visible at the exact horizon, and labelled truth lines as joined samples. All nine focused report tests pass after the final repair. These changes affected presentation only; the estimator, frozen settings and machine outcomes were not tuned after evaluation.

The independent verifier checks the frozen inventory, source/configuration identities, split separation, modeled truth/references, fault/audit arithmetic, causal source selection, used estimates/TTC, recomputed scoring and aligned errors. Its seven audit tests include valid evidence acceptance and negative controls for rehashed CSV tampering, omitted pairs, unlisted artifacts, incomplete status and report changes. Each final default run was independently checked: 157 pairs, 314 method records, 3,302 decision rows, 1,418 machine hashes, four report hashes and 1,102 contained local links.

Final reproduction at code revision `163aab5` is complete in `outputs/c1-reproduction-6c4f270cbbe5428b94d559633e551ed6/reproduction.json`: 55 explicit source inputs match their copied hashes; 14 cached wheel artifacts were hash-installed into a newly created environment with 14 installed packages; pip consistency and Ruff pass. The copied environment passed **222 tests in 88.287 s**. Original and copied runs each contain **1,424 files**, all byte-identical, including the three visually inspected PNGs. There are no source changes during reproduction or differing generated files. This is same-machine/new-environment evidence on the recorded Windows x64 / CPython 3.14.7 target. Browser-rendered HTML layout and a new remote C1 CI run are not claimed.

A separate comparison against the saved M4 machine evidence checked every development/diagnostic raw decision CSV, observation CSV and truth CSV: **243 files across 81 cases match byte for byte**. This protects the usable baseline against more than just summary-count agreement. The check is saved locally as `outputs/c1-baseline-compatibility-20261104.json`.

Run the report into a new directory:

```powershell
Set-Location 'E:\DriveCheck'
.\.venv\Scripts\python.exe c1_compare.py --config configs/c1-comparison.json --output-dir outputs/c1-example
.\.venv\Scripts\python.exe -m tools.verify_c1 outputs/c1-example
```

The offline entry is `outputs/c1-example/report/report.html`. The runner refuses an existing destination. Machine evidence, frozen selection, complete CSV/JSON results and raw/source/used traces remain alongside it. The report has a separate hash-bound package manifest; rendering cannot silently revise machine evidence.

For a new source copy and fresh hash-locked environment, use:

```powershell
.\.venv\Scripts\python.exe -m tools.reproduce_c1
```

An optional `--wheelhouse` pointing to a project-local reviewed wheel cache avoids redownloading packages. This preserves the original environment, copies an explicit source allowlist, checks lint/full tests, regenerates and independently audits both reports, and compares their file inventories. The recorded target remains CPython 3.14.7 / Windows x64. The C1 CI step is configured; no new remote run is claimed from local commands or commits.

## Decision and limits

Keep raw as the default baseline and projection as an explicit comparison method. This experiment supports a narrow conclusion: age projection corrects the mechanism of treating an old reading as current and improves current-gap error on many evaluated cases, but it does not improve positive outcome counts on the separate evaluation matrix and increases finite-horizon negative warning episodes.

Constant closing speed can fail during braking, acceleration or noisy speed; projecting multiplies speed error by age. It cannot recover an unarrived observation, relax a stale cutoff or change the physical trajectory. The two synthetic families and scaled relatives do not represent road traffic, multi-object perception or vehicle dynamics. Warning thresholds/windows are experimental conventions, not driving guidance or safety certification.

M5 can build a short demonstration around three traces: `diagnostic-005` for the mechanism, `evaluation-027` for the metric/scoring trade-off, and `evaluation-001` for unchanged behavior. Learner completion still requires explaining that trade-off and independently reproducing or changing a bounded case. Assistant-written implementation and passing tests do not supply that evidence.

## Follow the implementation

`c1_compare.py` validates CLI arguments and calls `c1_comparison.run`, then packages saved evidence with `c1_report.render`. The runner validates the original/scaled fixture references and writes the frozen selection and plan first. Each case creates truth, observations, fault audit and clock once; both methods reuse those inputs. Inputs are hashed before and after method execution to detect unintended mutation.

`c1_estimators.StateEstimate` retains its original immutable `Observation`. `c1_replay.replay_with_estimator` supplies a decision callback to the existing arrival queue. The shared `prepare_decision` checks availability and original source age; only an eligible source reaches the estimator. The common `ttc_from_state` applies the same warning branches to the used state. The decision retains original IDs/timestamps while its numeric gap records the estimate used. Each accompanying record preserves measured and estimated values separately.

Only offline `evaluation.score_case` and `aligned_errors` receive independent events or truth callbacks. Outcomes retain exclusive useful/late/missed categories. Errors retain the existing equally weighted eligible-decision, full-horizon convention, including virtual post-contact paths. A missing estimate is counted and yields null error when no eligible row exists; it is never inserted as zero error.

`tools.verify_c1` separately reconstructs causal source selection and arithmetic from saved evidence, checks physical/reference/fault policies and recomputes metrics. Rehashing a wrong decision CSV does not make it pass those semantic checks. `tools.reproduce_c1` copies an explicit source allowlist into a new workspace, creates a new environment, hash-installs dependencies, runs all tests and independently audits both regenerated reports. This protects correctness, completeness and reproduction with different kinds of evidence rather than relying on one successful shell exit.
