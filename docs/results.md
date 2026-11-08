# Results: correcting an old gap does not settle the warning trade-off

The comparison tests whether projecting an eligible old sensor reading to the current decision time addresses the baseline's delay failure. On the separate evaluation matrix, projection improves gap error in many pairs but leaves useful/late/missed positive counts unchanged and increases finite-horizon negative warning episodes. Raw remains the default and projection is an explicit comparison method.

These results describe the completed C1 experiment. They are synthetic validation evidence, with no claim of real-road safety or statistical significance. The [architecture](architecture.md) explains the causal/scoring contracts, [investigation](c1-investigation.md) traces the failure mechanism, and [reproduction](reproduction.md) gives the working commands.

## Experiment inventory

The frozen [C1 configuration](../configs/c1-comparison.json) uses the [M4 matrix](../configs/m4-release.json). Two families, lead braking and stop-and-go, each have an independently checked contact and non-contact configuration. A non-contact label means no contact inside that case's declared horizon.

| Split | Physical configurations and seed bases | Paired episodes | Method records | Positive / negative episodes |
| --- | --- | ---: | ---: | ---: |
| Development | Original four M4 configurations; bases 100, 200, 300 | 76 | 152 | 38 / 38 |
| Evaluation | Four distinct scaled configurations; bases 1000, 2000, 3000 | 76 | 152 | 38 / 38 |
| Development diagnostics | Five fixed delays on one constant-speed contact fixture; separate policy | 5 | 10 | 5 / 0 |
| Complete inventory | Raw and age projection retained for every pair | 157 | 314 | Kept separate by split |

Every pair and method completed in the accepted run: zero failed or partial pairs. The report includes misses and warning losses as valid outcomes rather than execution failures.

Each main split contains four clean episodes plus six stochastic conditions with three bases per configuration: `4 * (1 + 6*3) = 76`. Clean has a null case seed; its deterministic placeholder stream seeds are not extra repetitions. The four derived stream seeds are base+1 through base+4 for gap, closing speed, latency and dropout. Development/evaluation derived seed bundles are disjoint.

| Main condition | Settings | Positive / negative pairs per split |
| --- | --- | ---: |
| Clean | No fault | 2 / 2 |
| Low noise | Gaussian standard deviations: gap 0.2 m, closing speed 0.1 m/s | 6 / 6 |
| Strong noise | Gap 1 m, closing speed 0.5 m/s | 6 / 6 |
| Low latency | Delay `0.25 + 0.1*U` s, `U` uniform on `[0,1)` | 6 / 6 |
| Strong latency | Delay `0.5 + 1.5*U` s | 6 / 6 |
| Low dropout | Per-reading omission probability 0.1 | 6 / 6 |
| Strong dropout | Per-reading omission probability 0.4 | 6 / 6 |

The evaluation similarity transform is `x'=1.5x`, `t'=1.25t`; speeds scale by 1.2 and accelerations by 0.96. Contact times, final gaps and source sampling intervals have correspondingly transformed independent references. This changes physical parameters and seed bases, while retaining closely related synthetic families. It is a bounded holdout, with no claim about unfamiliar real traffic.

Both methods receive the same generated observations, omitted readings, arrival queue, decision clock, source-age gate, warning policy and scoring rule in each pair. Projection changes only `used_gap = measured_gap - measured_closing_speed * source_age`. The method/configuration were frozen before evaluation; later report fixes changed loss selection and endpoint visibility, without tuning the algorithm to the holdout.

The main policy uses a 3 s TTC threshold, inclusive 1.25 s maximum source age, 4 s pre-event window and 1 s minimum useful lead, on source sample times plus in-horizon arrivals. Diagnostics use a 2 s threshold, inclusive 3 s age limit, 3 s window and the same 1 s useful minimum, on a fixed 0.5 s clock. Their denominators remain separate.

## Main outcome counts

Positive outcomes are exclusive: useful, late or missed. The denominator for each is 38 positive episodes. False-warning rate uses 38 negative episodes. A warning on a negative episode is counted once at episode level, regardless of its number of warning decisions.

| Metric | Development raw | Development projection | Evaluation raw | Evaluation projection |
| --- | ---: | ---: | ---: | ---: |
| Useful positives | 33/38 | 33/38 | 31/38 | 31/38 |
| Late positives | 3/38 | 3/38 | 2/38 | 2/38 |
| Missed positives | 2/38 | 2/38 | 5/38 | 5/38 |
| Positives without a useful warning | 5/38 | 5/38 | 7/38 | 7/38 |
| False-warning negative episodes | 35/38 | 36/38 | 26/38 | 35/38 |
| Clear negative episodes | 3/38 | 2/38 | 12/38 | 3/38 |

The evaluation increase is nine false-warning episodes: `(9/38)*100 ≈ 23.6842` percentage points, or approximately 34.6154% relative to the raw count, calculated as `(9/26)*100`. Counts remain the clearest statement. This finite-horizon metric does not establish that a real driver should ignore any particular warning.

### Complete condition summaries

Useful/late/missed counts are identical between methods within every main condition. The tables retain each condition's own positive and negative denominators.

| Development condition | Useful / late / missed, both methods | Positive denominator | False warnings raw → projection | Negative denominator |
| --- | --- | ---: | ---: | ---: |
| Clean | 2 / 0 / 0 | 2 | 2 → 2 | 2 |
| Low noise | 6 / 0 / 0 | 6 | 6 → 6 | 6 |
| Strong noise | 6 / 0 / 0 | 6 | 6 → 6 | 6 |
| Low latency | 5 / 1 / 0 | 6 | 6 → 6 | 6 |
| Strong latency | 2 / 2 / 2 | 6 | 4 → 4 | 6 |
| Low dropout | 6 / 0 / 0 | 6 | 6 → 6 | 6 |
| Strong dropout | 6 / 0 / 0 | 6 | 5 → 6 | 6 |

| Evaluation condition | Useful / late / missed, both methods | Positive denominator | False warnings raw → projection | Negative denominator |
| --- | --- | ---: | ---: | ---: |
| Clean | 2 / 0 / 0 | 2 | 2 → 2 | 2 |
| Low noise | 6 / 0 / 0 | 6 | 6 → 6 | 6 |
| Strong noise | 6 / 0 / 0 | 6 | 6 → 6 | 6 |
| Low latency | 6 / 0 / 0 | 6 | 3 → 6 | 6 |
| Strong latency | 2 / 0 / 4 | 6 | 1 → 3 | 6 |
| Low dropout | 5 / 1 / 0 | 6 | 5 → 6 | 6 |
| Strong dropout | 4 / 1 / 1 | 6 | 3 → 6 | 6 |

### Evaluation seed variation

Each stochastic seed base covers 24 episodes: 12 positive and 12 negative, across six fault conditions and four configurations. Four clean pairs are separate: both methods give 2/2 useful positives and 2/2 false-warning negatives.

| Base | Useful / late / missed positives, both methods | Positive denominator | Raw false warnings | Projected false warnings |
| --- | --- | ---: | ---: | ---: |
| 1000 | 11 / 0 / 1 | 12 | 9/12 | 12/12 |
| 2000 | 10 / 0 / 2 | 12 | 8/12 | 11/12 |
| 3000 | 8 / 2 / 2 | 12 | 7/12 | 10/12 |

These are complete seed results from the configured experiment. Reused trajectories and standardized streams across conditions do not create independent real-road samples.

## Error and lead-time comparisons

Mean absolute error (MAE) compares the state actually used with truth at the decision time. Eligible rows have equal weight across the full horizon, including virtual post-contact paths. Stale/unavailable rows are counted separately. This differs from time-weighted error, measurement-time sensor error or pre-contact-only error.

The following counts classify projection against raw within each pair; they are not percentages of improvement or averages of different cases' MAEs.

| Paired metric | Development better / same / worse / unavailable | Evaluation better / same / worse / unavailable |
| --- | --- | --- |
| Gap MAE, m; lower is better | 39 / 37 / 0 / 0 | 37 / 38 / 0 / 1 |
| Closing-speed MAE, m/s; lower is better | 0 / 76 / 0 / 0 | 0 / 75 / 0 / 1 |
| Earliest matched useful lead, s; higher is better | 0 / 33 / 0 / 5 unpaired | 3 / 28 / 0 / 7 unpaired |
| False-warning negative outcome | 0 / 37 / 1 / 0, out of 38 negatives | 0 / 29 / 9 / 0, out of 38 negatives |

The lead comparison includes only positives where both methods gave a useful matched warning. The five development and seven evaluation unpaired positives remain visible as late/missed in the outcome table. Their lead is not inserted as zero.

`evaluation-013`, strong latency on the braking-contact case at base 3000, has no eligible estimate. Both MAEs are null, with unavailable/stale coverage retained in its method record. The absence of data is not a perfect estimate. Closing-speed error is unchanged wherever available because projection preserves closing speed.

No evaluation pair has a worse gap MAE on this matrix. A separate unit counterexample in [test_c1_estimators.py](../test_c1_estimators.py) covers changing speed: true gap 12.5 m, raw 15 m, projected 5 m; absolute errors are 2.5 m and 7.5 m. That test demonstrates an assumption failure, not an extra evaluation result.

## Three cases that explain the result

### `diagnostic-005`: the mechanism works under its assumption

The [original failure study](failure-study.md) uses constant closing speed 5 m/s, initial gap 30 m and independent contact at 6 s. With a fixed 2.5 s delay, at decision time 4 s the selected reading was measured at 1 s and arrived at 3.5 s. Its gap is 25 m and its age is 3 s, eligible under the diagnostic's inclusive age limit.

Raw TTC is `25/5 = 5 s`. Projection uses `25 - 5*3 = 10 m`, giving TTC 2 s and a warning at the diagnostic's inclusive 2 s threshold. Projection's first warning is at 4 s, useful with 2 s lead; raw misses the whole episode. Both retain three arrivals beyond the horizon and have the same eight eligible rows plus five unavailable rows. Gap MAE is 13.75 m raw and 0 m projected.

All fixed-delay diagnostic arms remain separate from the main matrix:

| Delay | Raw first warning / outcome | Projection first warning / outcome |
| --- | --- | --- |
| 0 s | 4 s / useful | 4 s / useful |
| 1 s | 5 s / useful | 4 s / useful |
| 1.5 s | 5.5 s / late | 4 s / useful |
| 2 s | 6 s / late | 4 s / useful |
| 2.5 s | None / missed | 4 s / useful |

Thus raw has 2 useful / 2 late / 1 missed out of five diagnostic positives; projection has 5 useful / 0 late / 0 missed. There are no diagnostic negatives, so no diagnostic false-warning rate is defined. The fixture deliberately matches constant closing speed.

### `evaluation-027`: a correct gap can still lose on the episode metric

At the 10 s horizon, the selected source was measured at 8.75 s and arrived at 9.047554402427377 s. Gap is 45 m, closing speed is 12 m/s, and age is 1.25 s. Raw TTC is 3.75 s, clear against the main 3 s threshold. Projection uses `45 - 12*1.25 = 30 m`, giving TTC 2.5 s and a warning.

The true gap at 10 s is 30 m. Episode gap MAE improves from 6.919372396522213 m to 0.9914500902539998 m, yet the outcome changes from `clear_negative` to `false_warning`. The declared 10 s horizon contains no contact; continuing the same prescribed motion would produce contact at 12.5 s. This is a scoring/horizon trade-off, with no inference that the more accurate current estimate is physically wrong.

All nine evaluation false-warning regressions are retained: `evaluation-027`, `028`, `029`, `030`, `035`, `036`, `037`, `038` and `069`. Eight concern the braking/non-contact family; `evaluation-069` concerns stop-and-go/non-contact.

### `evaluation-001`: no change is also evidence

Clean readings have zero age, so projection changes no used values. Both methods first warn at 2.5 s. Independently checked contact is 4.145780987944249 s, giving useful lead 1.645780987944249 s. Both gap and closing-speed MAEs are zero. The report retains this unchanged case alongside the diagnostic success and warning loss.

## Complete evidence and reproduction

A generated C1 run retains all 314 method rows in `cases.csv`, split/condition/family summaries in `summary.json`, and all planned pairs/statuses in `manifest.json` and `case-plan.json`. Each `cases/<case-id>/metrics.json` contains configuration, fault settings/seeds, references, policy, counts, per-method scores/errors and changes. Decision CSVs and source/estimate JSON traces preserve the arithmetic behind the summaries. The offline entry is `report/report.html`; its three selected figures are entry points into the complete table.

Use [the reproduction guide](reproduction.md) to generate those artifacts into a fresh folder. Generated `outputs/` evidence is ignored by Git; a reader should regenerate it rather than assume a local evidence folder is distributed with the repository.

Recorded acceptance includes:

- **Saved-evidence audit:** 157 pairs, 314 method records, 3,302 decision rows, 1,418 machine hashes, four report hashes and 1,102 contained local links.
- **Raw baseline preservation:** 243 saved raw decision/observation/truth files across 81 M4 cases match byte for byte.
- **Local reproduction:** at code revision `163aab5`, 55 copied inputs and 14 hash-locked wheel/package pins; 222 tests passed in 88.287 s in the copied-source/new environment. Both runs have 1,424 files, with zero differences. This proof is same-machine/new-environment on recorded Windows x64 / CPython 3.14.7.
- **Hosted verification:** accepted [main run 42012439506](https://github.com/Lifelessdice/DriveCheck/actions/runs/42012439506) at `60f26c30200a9b3465cee2ce9fcafb9d474f0f38` passed 222 tests in 33.929 s, dependency/Ruff checks and complete M4/C1 generation/audits. Hosted execution is separate from the local byte-identity proof; the test duration is an observed run time, not a performance benchmark.

The later [main run 42056296813](https://github.com/Lifelessdice/DriveCheck/actions/runs/42056296813) at `b2168f189377c9b7919f289f81f1b6e986b973ef` passed 227 tests in 33.920 s, the same complete M4/C1 audits and portfolio packaging. [Verification](verification.md) distinguishes these hosted checks from the local reproduction proof.

Three generated plots were visually reviewed. Browser-rendered HTML layout and cross-machine pixel identity remain unverified.

## Limits and decision

The families use prescribed one-dimensional motion, one reference event per episode, finite horizons, synthetic fault distributions and experimental thresholds. Noise and motion changes can break constant closing speed; projection multiplies closing-speed error by age. It cannot recover missing/unarrived information, override staleness or prevent a collision. Full-horizon row-weighted MAE and finite-horizon negative labels answer specific experimental questions, which must accompany the numbers.

The useful finding is bounded: age projection addresses the old-gap mechanism and improves current-gap estimates on many evaluated pairs, while the main positive warning outcomes remain unchanged and negative warning episodes increase. The complete losses and unchanged cases support retaining raw as the default.
