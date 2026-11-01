# A useful warning becomes late, then disappears when its reading arrives after the horizon

Observed 1 November 2026 in the saved M4 machine results. This note was drafted with AI assistance from the actual code, independent fixture and reviewed traces. It describes a controlled synthetic diagnostic, not real-vehicle warning validation or an evaluated improvement.

## Question and fixed setup

Can observation delivery delay alone turn a useful warning into a late or missed warning while the clean trajectory, warning threshold and evaluation rule stay fixed?

The ego travels at 10 m/s, the lead at 5 m/s and the initial bumper gap is 30 m. Independent relative motion gives `gap(t) = 30 - 5t` metres, so first contact is exactly 6 s. The declared horizon is `[0, 6]` s. Source readings are measured each second; decisions occur every 0.5 s. Warnings are passive and do not change this trajectory.

The diagnostic policy uses TTC threshold 2 s, maximum observation age 3 s inclusive, matching window 3 s and minimum useful lead 1 s. These differ from the main 76-case matrix. The five fixed-delay arms are therefore summarized separately. Delay changes only arrival time; the sensor values are exact at their measurement time.

## Independent prediction and observed result

At source time 4 s, gap is 10 m and closing speed is 5 m/s. Its held-value TTC is 2 s, exactly the inclusive warning threshold. With no delay, the first warning is therefore at 4 s, giving 2 s of lead before contact. Delaying that reading delays its availability; a reading cannot cause a warning before arrival.

| Fixed delay | Observed first warning | Matched lead | Observed outcome |
| --- | ---: | ---: | --- |
| 0 s | 4 s | 2 s | useful |
| 1 s | 5 s | 1 s | useful |
| 1.5 s | 5.5 s | 0.5 s | late |
| 2 s | 6 s | 0 s | late |
| 2.5 s | None | None | missed |

These are saved results from `outputs/m4-machine/run-a/` and `run-b/`, rows `regression-001` through `regression-005`. Each condition has one positive episode and no negative episodes. They are deterministic arms of one synthetic scenario, not five independent worlds or a statistically representative sample.

## What actually caused the strongest miss

The last decision in `cases/regression-005/decisions.csv` is:

| Field | Saved value |
| --- | ---: |
| Decision time | 6 s |
| Selected source ID | 3 |
| Measurement time | 3 s |
| Arrival time | 5.5 s |
| Measurement age | 3 s |
| Held gap | 15 m |
| Held closing speed | 5 m/s |
| TTC | 3 s |
| Warning / reason | false / `ttc_clear` |

The selected reading is accepted at the inclusive 3 s age boundary. This is **not a stale-reading rejection**. Its TTC is above the 2 s warning threshold.

Source ID 4, saved in `observations.csv`, describes the 4 s measurement: gap 10 m and closing speed 5 m/s. It would satisfy the TTC threshold, but arrives at **6.5 s**, after the 6 s horizon. IDs 5 and 6 arrive at 7.5 and 8.5 s. All three remain retained-but-pending observations; none is a dropout. Replay must not flush them early or extend the episode horizon to rescue the score.

The held gap at decision time 6 s is also 15 m away from current clean truth, which is zero at contact. Measurement-time error remains zero for this exact sensor; treating the old measurement as current state creates the discrepancy. Offline error evaluation can inspect that truth, while the warning policy cannot.

## Evidence and regression protection

The saved machine runs each contain 76 main cases plus five separate diagnostic cases, 343 verified artifact hashes and 344 files. All 344 files match byte-for-byte between the two runs. Source/configuration hashes, all per-case records, causal selection/age, independent scoring and fresh-row MAEs were reviewed. Existing M3 regression checks and M4 runner tests preserve the five timing outcomes, pending-arrival count, failure accounting and reproducible exports. The actual full suite passed 153 tests during this review.

The readable M4 report/plots are the next learner block; no new rendered M4 figure is claimed by this machine-results review. Inspect the future report against these saved rows rather than changing expected values to match an attractive picture.

## Limits and next question

This experiment uses constant-speed one-dimensional prescribed motion, exact measurements, fixed delays, one contact event and a finite horizon. It has no driver response, braking controller, impact dynamics or safety certification. A warning exactly at contact is late under this convention. A case can complete correctly while the algorithm misses a warning.

The main matrix's strong jittered latency also shows a trade-off: only 2 of 6 positive episodes have useful warnings, 2 are late and 2 missed, while 4 of 6 negatives warn. The lower negative-warning count relative to clean is not established improvement, especially when timely positive warnings are lost. Keep seed/family results and denominators visible.

C1 can later test one bounded latency-aware alternative with the same causal streams and warning/scoring policy, using separate development and evaluation cases/seeds. No alternative or improvement has been implemented or measured here.
