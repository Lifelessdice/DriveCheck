# C1 — Investigate one failure through a fair comparison

Prepared 27 October 2026. **Lesson ready for study; learner implementation, experiments and understanding remain pending.** This document is teaching material. Its code, commands, filenames and expected fixtures are proposals for you to implement, unless explicitly described as inspected existing reference material. No C1 experiment or improvement is claimed.

Read this section after working through M1–M4. You may read ahead now, but do the implementation only once you can reproduce your CPU baseline and point to an observed M4 failure. Work from `E:\DriveCheck`. Keep the working baseline and its saved results. Git, publication and remote CI remain yours; no simulator is required.

The complete section is available below. Work through each block at your own pace; you do not need a reply or permission between tasks. A sensible stopping point is the end of a block, with its calculation, code and output saved. The roadmap's 8–12 focused hours is a provisional allowance, not measured work or a deadline.

## 1. The question you are answering

M4 asks whether the raw time-to-collision baseline fails when observations are imperfect. C1 asks a narrower follow-up: **does one small, explainable change address a diagnosed mechanism, and what does it cost on the other cases?**

For example, a delayed distance might still describe where the bumpers were a second ago. Projecting that distance forward could help under unchanged relative speed, but fail after the lead vehicle accelerates. Alternatively, one noisy closing-speed spike might cause an unwanted warning; smoothing could suppress the spike but respond too slowly to real braking. These are hypotheses and teaching examples, not observed DriveCheck results.

Your finished investigation should let another reader follow:

`saved failure → causal diagnosis → one proposed change → same-input comparison → complete results → supported conclusion`.

You do not need to beat the baseline. Finding that the baseline wins, or that a method trades fewer false warnings for later useful warnings, is a valid outcome. A smooth plot alone is insufficient evidence.

### What exists, and what this lesson proposes

At authoring, the preserved M1 reference exposes these truth fields in `motion.py`: `scenario_id`, `sample_id`, `time_s`, `ego_front_x_m`, `lead_rear_x_m`, `ego_speed_mps`, `lead_speed_mps`, `gap_m`, `closing_speed_mps`. `scenarios.py` loads independent fixture reference answers. The learner's completion of the full M1 section remains pending. Later modules below follow the [shared study guide](../study-guide.md) and must be checked against the modules you actually implement.

| File or interface | Responsibility in your later implementation |
| --- | --- |
| `motion.py`, `scenarios.py`, scenario configuration | Clean truth, declared horizon and independently checked contact event; unchanged for each paired run |
| `observations.py`: `Observation` | `scenario_id`, `sample_id`, `measurement_time_s`, `arrival_time_s`, `gap_m`, `closing_speed_mps`; no truth/reference-event fields |
| `replay.py` | Causal release, duplicate/out-of-order policy, common decision grid and accepted observation selection |
| `warning_policy.py` | The existing experimental TTC threshold, unavailable/stale policy and warning handling; both methods use the same logic |
| `evaluation.py` | Existing independent event scoring and aligned errors; it alone receives truth/reference events |
| **Proposed** `estimators.py` | Raw adapter plus exactly one selected alternative; no fault generation, reference-event access or policy tuning |
| **Proposed** `comparison.py` | Freeze/load paired inputs, reset state, run both methods, retain every result and provenance |
| **Proposed** `test_c1.py` | Independent numerical fixtures, baseline compatibility, causal/fairness and regression checks |
| **Proposed** `configs/c1-plan.json` | Failure question, chosen method/settings, split manifest and frozen policy/input identities |
| `reporting.py` from your completed M4, proposed `drivecheck.py compare` command | Comparison table, paired plots and offline artifacts, reusing M4 rather than building a second reporting system |
| **Proposed** `docs/c1-investigation.md` | Your actual question, design, results, losses and limitations, written after the runs |

Do not create `warnings.py`: that name shadows Python's standard-library `warnings` module. Do not copy a second evaluator into C1. Where names differ in your M4 implementation, make a small adapter and document the mapping.

**Checkpoint before continuing:** you can run the M4 command, identify its configuration/results/report files, explain one warning against its source reading, and locate the independent event used to score it. If the baseline itself is broken, repair and revalidate it first. C1 should not hide a timestamp bug inside an alleged algorithm improvement.

## 2. Freeze the failure and select one method

Start by reproducing a saved M4 failure. Copy the relevant trace and configuration into a new ignored C1 development output directory through your existing runner. Preserve the original M4 results. Record file hashes, source/configuration identity, runtime/dependency versions and the exact command. A hash identifies bytes; it does not prove those bytes are correct.

Write a short development note with actual values:

```text
Question:
Baseline case ID / scenario / fault / severity / seed:
Independent contact time or no-contact horizon:
Decision time, source measurement time and arrival time:
Observed raw gap, closing speed, TTC and warning:
How the warning was scored:
Evidence for the proposed mechanism:
One alternative and why its prerequisites are manageable:
One condition in which I expect it to lose:
```

Separate a symptom from a mechanism. “The warning was late” is a symptom. “At decision time 2 s, the available 25 m reading was measured at 1 s; at 5 m/s closing speed its unchanged-speed projection is 20 m” is a testable mechanism. Check the source reading and arrival trace before blaming noise or delay.

Choose **one** route below for this C1 investigation. The two routes are alternative study paths, not a requirement to implement two new algorithms or run an evaluation tournament.

| Your reproduced evidence | Bounded candidate | Prerequisites and reason to reject it |
| --- | --- | --- |
| An arrived, still-eligible reading is old; holding its gap overstates current separation | Route A: constant-closing-speed age projection of gap | Units, signs and actual elapsed time. Reject if M4 already projects age, or the failure is caused by no eligible readings rather than a stale held value. |
| A transient measured closing-speed spike changes warnings while truth stays smooth | Route B: causal exponential smoothing of closing speed only | Weighted averages, state and elapsed time. Reject if delayed/missing arrivals explain the symptom, or the important change is real rapid braking. |
| Neither mechanism fits | Revisit the diagnosis and write a different small candidate specification before coding | Do not force a method onto unrelated evidence. The rest of this lesson still supplies the comparison contract, split, tests and reporting workflow. |

A constant-velocity Kalman filter is a candidate for a different choice, not a requirement or an automatic upgrade. Before selecting it you would need a worked state-vector/matrix-shape example, covariance/uncertainty reasoning, motion/measurement models, initialization, predict/update and tuning checks, plus primary-source verification. Neither simple route below claims to implement a Kalman filter. Choose the smallest method that answers the actual question.

Write your hypothesis **before** looking at final evaluation outputs. Example: “Age projection may advance warnings under latency with nearly constant closing speed, but extrapolation after acceleration may add false warnings.” Identify the expected failure as well as the hoped-for benefit.

## 3. Keep the experimental contract fixed

For each case/seed, create the faulted observation stream once and save it, or retain an immutable tuple and a canonical serialized hash. Give both methods exactly those readings in the same release order at the same decision times. The same seed is insufficient if two code paths consume random numbers differently.

The sole changed component is the selected estimator. Keep these identical between raw and alternative:

- Underlying truth/configuration, independent reference event, horizon and fault severity.
- Observation values, omitted/dropout samples, source IDs, measurement times and arrival times.
- Decision grid, replay validation and duplicate/out-of-order handling.
- Source-age cutoff, unavailable behavior, TTC threshold, debounce/repetition handling and scoring window.
- Error alignment, summary denominators and treatment of failed/partial cases.

No reading is available until `arrival_time_s <= decision_time_s`. Arrival does not reset measurement age. Missing data is not a zero gap. Keep the M3 rule for a late-arriving older measurement; for example, if it is discarded from the latest-value state, neither method may secretly use it as a fresh update. Do not switch to sorting the entire log by measurement time: that can give an estimator data before it arrives.

The following-vehicle TTC calculation uses gap divided by positive closing speed under unchanged motion; [SUMO's official TTC documentation](https://sumo.dlr.de/docs/Simulation/Output/SSM_Device.html#ttc) supports that interpretation. It does not validate our threshold or scoring windows. Sources linked in this lesson were checked on 27 October 2026; the project-specific projection/smoothing design and numerical fixtures are teaching proposals, not findings from those sources.

### A small proposed estimator boundary

In `estimators.py`, use the existing `Observation` record from your implementation. The proposed estimate record below deliberately separates the time of a decision-state estimate from the time of its source reading:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class Estimate:
    decision_time_s: float
    source_sample_id: int
    source_measurement_time_s: float
    gap_m: float
    closing_speed_mps: float
```

This is a view for the policy, not a replacement observation. Preserve `arrival_time_s` on the observation and in the trace. For all methods, `observation_age_s = decision_time_s - source_measurement_time_s`. Do not replace the source time with the decision time to make a stale estimate appear fresh.

Adapt your M4 policy so it applies its existing eligibility checks once, obtains an estimate for an eligible reading, then uses the same numerical TTC/warning helper. The raw adapter simply carries the measured gap/speed forward unchanged as a zero-order-hold estimate. Preserve its old reasons, timestamps and warning decisions exactly. Add a compatibility test that replays the frozen M4 inputs through the original baseline path and the new raw adapter, then compares the complete decision records. A changed baseline means the refactor is unfinished.

**Learner task:** draw one row containing source time, arrival time, decision time, source age, estimated gap and TTC. Explain which fields a gap projection may change. Answer: estimated gap and resulting TTC/warning may change; it does not change source/arrival times, source age, truth or the scoring window.

Keep truth out of the estimator function signature. The runner may retain truth for later evaluation, but neither estimator nor warning policy receives a reference contact time, future row or clean current gap.

## 4A. Route A — use elapsed age to project the gap

Study and implement this block only if your saved failure supports Route A. Skip Route B's implementation.

Let `d_m` be measured gap in metres, `c_m` measured closing speed in m/s, and `a = t_decision - t_measurement` the age in seconds. If closing speed stayed unchanged over that age, the ego gained `c_m * a` metres, so:

`estimated_gap_now = d_m - c_m * a`.

The sign comes from relative motion: positive closing speed shrinks gap. Negative closing speed increases the projected gap. The method predicts state from information already received; it does not observe the present truth. Elapsed-time kinematics follows the displacement reasoning in [OpenStax University Physics §3.4](https://openstax.org/books/university-physics-volume-1/pages/3-4-motion-with-constant-acceleration); assuming constant relative speed during age is our model choice.

Use the same closing-speed value as the baseline. Do not quietly add an acceleration estimate, a new stale cutoff or a changed TTC threshold. Do not repeatedly subtract the entire age from a previously projected value: always start from the original measurement.

Guided core for `estimators.py`, called only after shared replay/eligibility validation:

```python
def raw_estimate(observation, decision_time_s):
    return Estimate(
        decision_time_s=decision_time_s,
        source_sample_id=observation.sample_id,
        source_measurement_time_s=observation.measurement_time_s,
        gap_m=observation.gap_m,
        closing_speed_mps=observation.closing_speed_mps,
    )


def age_projected_estimate(observation, decision_time_s):
    age_s = decision_time_s - observation.measurement_time_s
    # Learner: derive the sign and fill this line; do not call truth_at().
    projected_gap_m = ...
    return Estimate(
        decision_time_s=decision_time_s,
        source_sample_id=observation.sample_id,
        source_measurement_time_s=observation.measurement_time_s,
        gap_m=projected_gap_m,
        closing_speed_mps=observation.closing_speed_mps,
    )
```

Fill the expression from the displacement argument above. Keep negative projected gaps; pass them to the same contact/non-positive-gap rule used by your baseline. A negative estimate is not proof of a real contact and must never become a reference-event label. Invalid/future/unarrived or stale readings should be rejected/marked unavailable by the common M4 path before this helper is called. Test that path as well as the arithmetic helper. Check the output remains finite and surface overflow as a failed case.

### Independent fixture: useful projection without future truth

Take constant forward speeds: ego 20 m/s, lead 15 m/s, initial gap 30 m. At measurement time 1 s, individual distances are 20 m and 15 m, so the gap is `30 + 15 - 20 = 25 m`. Let it arrive at 2 s and make a decision then. The reading's age is 1 s. Projection gives `25 - 5*1 = 20 m`.

Check truth independently at decision time: the bumpers are at 40 m and `30 + 30 = 60 m`, again a 20 m gap. Raw TTC is `25/5 = 5 s`; projected TTC is `20/5 = 4 s`. With a **teaching fixture** threshold of 4 s inclusive and an age cutoff that admits 1 s, raw does not warn at 2 s while the alternative does. No present truth was required by the estimator.

For a 7 s horizon, independent contact is at 6 s because the ego gains 30 m at 5 m/s. With one-second samples and one-second delay, raw first warns at 3 s while projection first warns at 2 s. If the scoring window is `[2, 5]` s inclusive, both warnings are useful; their earliest leads are 3 s and 4 s respectively. Earlier warning here is a lead-time change, not a reduced missed-event count. These are hand-calculated fixtures, not measured portfolio results.

### Independent counterexample: a projection can lose

At measurement time zero, let gap be 30 m and closing speed 5 m/s. After that, let closing speed decrease as `c(t) = 5 - 5t` for `0 <= t <= 1`, then stay zero. The actual gap during that first second is `30 - 5t + 2.5t²`, so it reaches 27.5 m and remains there. No contact occurs within a 4 s horizon.

Suppose the time-zero reading arrives at 3 s. For this arithmetic fixture only, admit age 3 s and use the same 4 s TTC threshold for both methods. Raw TTC is `30/5 = 6 s`. Projection estimates `30 - 5*3 = 15 m` and TTC 3 s, causing a false-warning episode. Against true current gap 27.5 m, raw absolute error is 2.5 m and projected error is 12.5 m. The mechanism is extrapolation of closing speed after it stopped being valid. Keep the real M4 policy unchanged in experiments; these fixture settings do not authorize loosening its stale cutoff.

**Meaningful attempt:** a reading has gap 18 m, closing speed 4 m/s, measurement time 1.25 s and decision time 2 s. Predict projected gap and TTC before running. Then change closing speed to −2 m/s and explain the sign. Answers for checking afterward: age 0.75 s; projected gap 15 m and TTC 3.75 s in the first case; projected gap 19.5 m and no finite positive-closing-speed TTC in the second.

**Route A tests to add:** zero-age equality with raw; the 20 m example; the noninteger-age attempt; negative/zero closing speed; projected zero/negative gap; repeated calls at the same time; unavailable/stale/future rejection through the common policy; finite output. Repeat-call equality catches double projection. No parameter search is needed for this candidate: the rule has no tunable weight. Development still decides the method and reveals implementation mistakes; keep final evaluation separate.

## 4B. Route B — smooth a noisy closing-speed signal

Study and implement this block only if your saved failure supports Route B. Skip Route A's implementation. This route leaves measured gap unchanged and smooths **closing speed only**, keeping the changed mechanism narrow.

A weighted average gives part of the new estimate to a new reading and part to the previous estimate:

`smoothed_c = alpha * measured_c + (1 - alpha) * previous_c`.

With alpha 0.5, previous 2 m/s and new 10 m/s, the result is 6 m/s. With the next reading back at 2 m/s it becomes 4 m/s. A spike shrinks, but a real jump is also delayed. That is the trade-off you are testing. [NIST's EWMA explanation](https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc314.htm) provides the recursive weighted-average form and memory interpretation. We borrow that calculation, not its control-chart thresholds or its application assumptions.

Use elapsed measurement time, rather than applying the same weight once per decision tick. One simple project convention is a half-life `h` in seconds:

`alpha = 1 - 2 ** (-dt / h)` where `dt = new_measurement_time - previous_accepted_measurement_time`.

After one half-life the retained old weight is 0.5; after two it is 0.25. This time-dependent choice is a project adaptation, not a NIST recommendation for vehicle warnings. Initialize from the first accepted observation, so you do not invent an initial speed or tune an unseen starting value.

Guided stateful core for `estimators.py`:

```python
import math


class ClosingSpeedSmoother:
    def __init__(self, half_life_s):
        if (isinstance(half_life_s, bool)
                or not isinstance(half_life_s, (int, float))
                or not math.isfinite(half_life_s) or half_life_s <= 0):
            raise ValueError("half_life_s must be finite and positive")
        self.half_life_s = half_life_s
        self.previous_time_s = None
        self.source_sample_id = None
        self.closing_speed_mps = None

    def ingest(self, observation):
        # Called once for each new observation accepted by common replay.
        t = observation.measurement_time_s
        if self.previous_time_s is None:
            self.closing_speed_mps = observation.closing_speed_mps
        else:
            dt = t - self.previous_time_s
            if dt <= 0:
                raise ValueError("expected a newly accepted, newer observation")
            alpha = 1 - 2 ** (-dt / self.half_life_s)
            # Learner: write the weighted average; preserve signed speed.
            self.closing_speed_mps = ...
        self.previous_time_s = t
        self.source_sample_id = observation.sample_id

    def estimate(self, latest_observation, decision_time_s):
        if self.source_sample_id != latest_observation.sample_id:
            raise ValueError("filter state and selected observation disagree")
        return Estimate(
            decision_time_s=decision_time_s,
            source_sample_id=latest_observation.sample_id,
            source_measurement_time_s=latest_observation.measurement_time_s,
            gap_m=latest_observation.gap_m,
            closing_speed_mps=self.closing_speed_mps,
        )
```

Fill the average from the equation. Validate observations using the common M3/M4 contract, check finite filtered output, and create a **new instance per episode**. The example assumes measurement times in the accepted update sequence strictly increase. Use the exact common out-of-order rule to make that true; a discarded older arrival must not update the smoother. Multiple accepted arrivals in a decision tick must be ingested in the common accepted order before emitting that tick's estimate.

Do not call `ingest` every tick with the held reading. With no new accepted reading, hold the filter state; source age still grows, and the common stale cutoff still applies. Dropout supplies no update. Do not update on a fabricated zero or access future measurements. Record the accepted updates so you can test that each source ID is ingested once. Ingest the same common accepted update sequence, including updates that are too old to support a warning; eligibility at decision time still controls whether either method can emit a warning. Document this state-update convention and keep it fixed during development/evaluation.

### Independent spike and lag fixtures

Use half-life 1 s and observations at 0, 1 and 2 s. Measured closing speeds `[2, 10, 2]` produce `[2, 6, 4]` m/s. Check by substitution with alpha 0.5. If the middle gap is 25 m and the TTC threshold is 4 s inclusive, raw TTC is 2.5 s and smoothed TTC is `25/6 = 4.166666... s`. Raw warns; the smoothed estimate does not.

To make that a complete non-contact example, let actual closing speed be 2 m/s and initial gap 27 m, with horizon 2 s. The true gaps are `[27, 25, 23]` m and independent contact would be at 13.5 s, outside the horizon. The noisy measured spike can therefore cause a false-warning episode. Both methods still use the same gap readings and the same policy.

Now make the jump real: true closing speed is 2 m/s before time 1 s and 10 m/s afterward. Let the initial gap be 32 m. At 1 s the gap is 30 m; after that, contact is at `1 + 30/10 = 4 s`. Immediate observations give raw TTC `30/10 = 3 s` and smoothed TTC `30/6 = 5 s`. At 2 s the true gap is 20 m; the filtered speed becomes 8 m/s and TTC 2.5 s. With the same 4 s threshold, raw first warns at 1 s and the smoother at 2 s: earliest leads 3 s versus 2 s. Under a teaching scoring window `[1, 1.5]` s, raw is useful and the alternative is late. A prettier signal can therefore worsen the result that matters.

These complete synthetic examples use prescribed piecewise motion and independent event calculations. Adapt them to your scenario model or keep them as explicit evaluator/estimator unit fixtures; do not claim they were observed in M4.

**Meaningful attempt:** with half-life 1 s, first speed 2 at time 0 and next speed 10 at time 2, compute alpha and the new estimate. Then apply a speed of 2 at time 3. Answers: alpha 0.75, estimate 8 m/s; next alpha 0.5, estimate 5 m/s. A fixed 0.5 per arrival would incorrectly give 6 m/s at time 2. This is why actual intervals matter.

**Route B tests to add:** first-sample initialization; `[2, 6, 4]`; the irregular-interval `[2, 8, 5]`; no update between arrivals; dropout preserves state without resetting age; new episode resets state; rejected older arrivals/duplicates do not alter state; signed closing speeds; invalid half-life; finite output; spike suppression and the real-change lag counterexample. Pure estimator tests may reject duplicate ingestion; integration tests must show the common replay policy prevents or consistently handles it.

## 5. Separate development from evaluation before selecting settings

Your original M4 failure belongs to **development** because it motivated the method. Every case or seed you inspected while choosing the method, fixing an algorithmic choice or selecting a setting also belongs to development. Renaming it “test” later does not make it unseen.

Choose the split by whole scenario configuration and seed, not by shuffling rows from the same trajectory. Neighboring rows describe the same episode. Sharing a seed across different algorithms is good pairing; sharing tuning episodes with final evaluation is not an independent holdout. Official [scikit-learn evaluation guidance](https://scikit-learn.org/stable/modules/cross_validation.html#cross-validation-evaluating-estimator-performance) explains why repeatedly choosing settings from final test performance leaks information. This principle applies even though neither simple route requires fitting an ML model; no scikit-learn installation is needed.

A manageable **proposed** plan is:

| Split | Scenario configurations | Stochastic profile seeds | Use |
| --- | --- | --- | --- |
| Development | One contact and one challenging non-contact configuration from each of lead-braking and stop-and-go | 11, 29, 47, retaining the M4 teaching seed list | Diagnosis, debugging and Route B parameter selection; extra original-failure regressions listed separately |
| Evaluation | Four different, independently checked configurations covering the same family/contact combinations | 101, 102, 103, 104, 105, provided none was inspected earlier | Final paired comparison after method/settings are frozen |

These IDs are suggestions, not evidence of random independence. Confirm against your actual prior use; replace any previously inspected seed/configuration. Compare numerical scenario configurations with identity labels removed: renaming a scenario does not make it a new holdout configuration. Different seeds on the same deterministic truth do not demonstrate generalization to a new scenario family. Do not count every correlated time sample as an independent experiment.

For both methods and every split, retain M4's seven single-fault profiles: clean, low/strong noise, low/strong fixed latency, low/strong dropout, **if that is the matrix you implemented**. Preserve its actual magnitudes/distributions/patterns rather than inventing new severities to favor the alternative. If your M4 matrix differs, list its exact profiles and recalculate the expected count before running. No combined-fault scope is required.

Reuse M4's per-profile enumeration, not a Cartesian product of every profile with every seed. The three deterministic profiles (`clean`, `latency_low`, `latency_strong`) each retain **`seeds: [null]`** and run once per scenario. Only the four stochastic noise/dropout profiles receive the split's stochastic seed list:

| Profile group | Profiles | Development episodes per scenario | Evaluation episodes per scenario |
| --- | ---: | ---: | ---: |
| Clean and fixed latency, each with `[null]` | 3 | `3 × 1 = 3` | `3 × 1 = 3` |
| Low/strong noise and dropout | 4 | `4 × 3 = 12` | `4 × 5 = 20` |
| Total per scenario | 7 | 15 | 23 |

With four scenario configurations per split, development has **`4 × (3 + 4 × 3) = 60` paired episodes / `120` method records**. Evaluation has **`4 × (3 + 4 × 5) = 92` paired episodes / `184` method records**. With two contact and two non-contact configurations, evaluation has 46 positive and 46 negative paired episodes; development has 30 of each. These are planned counts, not observed outcomes. Each pair uses the same stream for raw and alternative, so 184 method records are not 184 independent episodes. Do not manufacture deterministic replicas under extra seed labels. Add original M4 regression cases outside these counts, label them development/regression, and list their own expected counts and any overlap with the main development keys.

Preserve M4's `enumerate_cases` and `fault_config_for_case` boundary adapters. Load each frozen profile with its unchanged parameters; replace its seed list only when its kind is stochastic. Keep deterministic profile seeds `[null]` in both splits. The nullable case seed maps through `four-streams-v1` to distinct `gap_seed`, `closing_seed`, `latency_seed`, `dropout_seed`: base `4 * seed` for an integer seed, base 0 for null, then offsets 0–3. For example seed 11 resolves to `[44, 45, 46, 47]`; evaluation seed 101 to `[404, 405, 406, 407]`; null uses unused deterministic placeholders `[0, 1, 2, 3]`. Retain M4/M3's field mapping, draw order, saved resolved `FaultConfig`, `seed_role` and derivation version. Do not replace it with a single shared RNG seed or pass presentation field names directly to the M3 constructor. Generate each resolved stream once and pair that exact stream across methods.

### A concrete plan structure you fill from actual M4 artifacts

Create `configs/c1-plan.json` yourself after naming real input cases. This is a proposed schema; placeholder text must fail validation rather than silently run:

```json
{
  "schema_version": "drivecheck.comparison.v1",
  "question": "REPLACE with an observed failure mechanism",
  "alternative": "age_projection_OR_closing_speed_ewma",
  "settings": {},
  "baseline_manifest": "REPLACE with a preserved M4 manifest path",
  "policy_config": "REPLACE with preserved M4 resolved config.json path",
  "development": {
    "case_ids": ["REPLACE with four real development configuration IDs"],
    "stochastic_seeds": [11, 29, 47]
  },
  "evaluation": {
    "case_ids": ["REPLACE with four distinct evaluation configuration IDs"],
    "stochastic_seeds": [101, 102, 103, 104, 105]
  },
  "fault_conditions": ["REPLACE with exact existing M4 condition IDs"]
}
```

Here `policy_config` refers to the full preserved M4 resolved configuration; load and freeze both its `warning_policy` and `evaluation_policy`, as well as its referenced profile parameters. `case_ids` means scenario-configuration identities in this proposed plan, not already-expanded case/seed IDs. Resolve them through the M4 catalog adapter, then reuse its per-profile enumerator. The `stochastic_seeds` name is deliberate: it must never expand the deterministic profiles. Save the resulting complete case plan and expected split counts before executing either method.

For Route A set `alternative` to `age_projection` and leave settings empty. For Route B set it to `closing_speed_ewma`; on development only, compare a small declared set of half-lives, such as `[0.25, 0.5, 1.0]` seconds. These are experimental candidates, not driving guidance. Record all development attempts, including unsuccessful choices.

Choose your selection rule before the search. One transparent example ranks by fewer missed-or-no-useful-warning positive episodes, then fewer false-warning negative episodes, then fewer late-only positives, then larger median earliest useful lead among paired successes; resolve a remaining tie by a declared parameter order. The first term treats late-only as lacking a useful warning; the later term distinguishes which failures are late. Record this overlap explicitly. Other priorities are defensible, but changing the rule after seeing outcomes is another tuning step that belongs in development. Keep all individual metrics visible instead of hiding the trade-off behind one score.

Freeze the chosen method, its parameters, the input split, source/configuration hashes and the warning/scoring policies in a selection artifact. Run final evaluation once afterward. If evaluation reveals a software bug, preserve and label that run invalid, fix it and explain the rerun. If evaluation inspires a new algorithmic setting, the viewed set is now development; obtain fresh holdout cases/seeds for a new final comparison or label the result exploratory.

## 6. Build the paired runner without rebuilding the CPU core

In proposed `comparison.py`, add orchestration around your working M4 functions. The following is an algorithm sketch, **not executable code** and not a claim about existing function names:

```text
validate plan, split disjointness, paths and expected episode count
load preserved M4 policy and scoring configuration
resolve profiles with [null] for deterministic kinds and split seeds for stochastic kinds
reuse M4 enumeration and four-stream fault adapter; save expanded case plan
create new output directory; write status = running and full plan identity
for each planned episode key in a stable order:
    load the scenario and independent reference separately
    create/load its faulted observations ONCE
    serialize/hash immutable observations and decision grid
    for method in [raw, selected_alternative]:
        construct fresh per-episode estimator state
        replay the SAME observations with the SAME policy/grid
        record every decision plus source IDs/ages and estimate values
        score decisions against independent reference, offline
        save result, including status and all metric denominators
        if a method fails: save its exception/status; do not omit its key
    verify common stream, truth, policy, grid and reference identities
verify all planned episode keys and both method records are present
write complete or failed/partial manifest; render report with all cases
```

Make the shared replay return both newly accepted updates and the latest selected observation, or expose an equivalent callback. Route A needs the eligible latest observation and decision time. Route B ingests each new accepted update once, then emits its estimate from the latest source. Both use the same selection and freshness path.

The scorer receives the independent contact event and declared horizon only after the decisions have been produced. The estimator does not receive the enclosing case dictionary if it contains truth or contact labels. Add a causal-prefix test: append/alter observations whose arrival is later than a chosen decision time and confirm that decisions up to that time remain unchanged.

Keep the baseline callable and its original M4 command working. Write C1 output under a separate directory, such as `outputs/c1-dev-01` or `outputs/c1-eval-01`, with distinct run IDs. Do not overwrite a previous successful run with an experiment. Validate all input/output paths and destination collisions before writes, reusing M4's protections. A failed or partial run stays labelled; its missing pair is not an unchanged result.

**Learner task:** implement plan validation that rejects overlapping scenario configurations or non-null stochastic split seeds, unknown alternatives, unfilled placeholders, a missing baseline/policy file, nonfinite settings and an undeclared policy change. Null in a deterministic profile is valid in both splits; it is not a stochastic seed overlap. Reject a deterministic profile carrying several seed labels. Assert the illustrated development/evaluation counts of 60/92 pairs and 120/184 method records before extra regressions. Then deliberately pass one invalid plan and check the helpful error and failed/nonstarted status. Do this without deleting the successful baseline output.

## 7. Tests with known answers and checks that can catch unfairness

Use your existing standard-library `unittest` runner unless M4 has deliberately selected another runner. Add C1 tests without removing earlier fixtures. Focus on a few independent answers and integration invariants.

For Route A, the following is a proposed numerical test you can place in `test_c1.py` after implementing the proposed functions. `Observation` uses the shared curriculum fields; adapt its constructor if your validated record has additional required fields:

```python
import unittest

from observations import Observation
from estimators import raw_estimate, age_projected_estimate


class TestAgeProjection(unittest.TestCase):
    def test_arrived_one_second_old_gap(self):
        observation = Observation(
            scenario_id="projection_fixture", sample_id=1,
            measurement_time_s=1.0, arrival_time_s=2.0,
            gap_m=25.0, closing_speed_mps=5.0,
        )
        raw = raw_estimate(observation, 2.0)
        alternative = age_projected_estimate(observation, 2.0)
        # Literals from independently checking both bumper positions.
        self.assertEqual(raw.gap_m, 25.0)
        self.assertEqual(alternative.gap_m, 20.0)
        self.assertEqual(alternative.source_measurement_time_s, 1.0)
        self.assertEqual(alternative.closing_speed_mps, 5.0)
```

For Route B, replace this class and its estimator import with `ClosingSpeedSmoother` tests that construct three observations at 0, 1 and 2 s, call `ingest` once per observation, and assert filtered speeds `[2.0, 6.0, 4.0]`. In a separate test use measurement times 0, 2 and 3 s and assert `[2.0, 8.0, 5.0]`. Use `assertAlmostEqual` for nonexact calculations. Do not import an unimplemented Route A helper when following Route B. Do not write expected values by calling the implementation's own formula inside the test.

The common integration tests matter as much as estimator arithmetic:

| Test | Independent expectation / failure it catches |
| --- | --- |
| Baseline compatibility | Raw adapter reproduces every saved original-baseline decision and score; catches an accidental policy rewrite |
| No arrival before availability | A sample arriving at 1.2 s cannot influence a decision at 1.1 s; at 1.2 s it may, under the common boundary rule |
| Source age is preserved | A time-zero sample arriving at 1.2 s has age 1.2 s at that decision, not zero |
| Stale/unavailable is shared | At times when the common policy rejects the source, neither method emits an eligible warning; no fake zero-gap measurement |
| Accepted sequence is common | Same source IDs/order for both methods; older-arriving discarded samples never update only the alternative |
| Causal prefix | Alter later-arriving readings; earlier decisions do not change |
| State reset and repeat behavior | Run a case alone and after another case; same result. Route B does not ingest a held reading repeatedly. Route A does not project an already projected gap. |
| Pair and matrix integrity | Expected key count, exactly two method records per key, same truth/stream/policy/grid/reference hashes; deliberately remove one record and detect it |
| Per-profile seed enumeration | Four scenarios give 60 development pairs and 92 evaluation pairs under the illustrated split; clean/fixed-latency use one null case seed, stochastic profiles use their declared lists; check M4's exact resolved stream bundles |
| Aligned error compatibility | Raw `gap_rmse_m` / `closing_rmse_mps`, masks and coverage match M4 before/after the adapter; changing or excluding post-contact rows must not silently change the metric definition |
| Scoring known answers | The fabricated scoring exercise below matches literal counts and denominators; no successful-warning-only average conceals misses |
| Regression | Reproduce the original observed M4 failure with raw and retain the alternative outcome even if it loses |

### A hand-calculated scoring exercise

This is **fabricated teaching data**, unrelated to measured DriveCheck performance. Use it to check reporting. Assume three positive episodes P1–P3 and two negative episodes N1–N2. Reuse M4's exact mutually exclusive episode categories; for this exercise define useful as a warning in the declared useful window, late-only as a pre-contact warning after that window with no useful warning, and missed as neither. Early-unmatched or post-contact warnings do not become useful. A late-only episode still lacks a useful warning, so report that combined count separately.

| Episode | Raw | Alternative |
| --- | --- | --- |
| P1 | useful, earliest matched lead 3 s | useful, earliest matched lead 2.5 s |
| P2 | missed | late-only |
| P3 | useful, earliest matched lead 2 s | useful, earliest matched lead 2 s |
| N1 | false-warning episode | no warning |
| N2 | no warning | false-warning episode |

Correct summaries: positives 3, negatives 2; useful 2/3 for each; missed 1/3 raw versus 0/3 alternative; late-only 0/3 versus 1/3; lacking useful warning `(missed + late-only)` is 1/3 for each. False-warning episodes are 1/2 for each. Mean lead among useful successes is 2.5 s raw and 2.25 s alternative, with denominator 2 visibly stated for each. On paired useful successes, alternative minus raw lead changes are −0.5 s and 0 s. The mean alone does not reveal that P2 remains without a useful warning or that N1 and N2 exchanged which episode warned falsely.

If your M4 definition calls every no-useful-warning episode a “miss,” preserve that definition: missed/no-useful is 1/3 for both and late-only is a subset 0/3 versus 1/3. Explain the category mapping. Never change metric definitions during C1 to make a result look better.

Avoid a single overall win/loss label unless you predeclare its priority rule. Report directions per metric: P1 loses lead time; P2 trades a missed category for late-only without useful-warning success; P3 is unchanged; N1 improves false-warning status; N2 worsens it. This table demonstrates why every case must remain visible.

## 8. Commands you run and artifacts you inspect

All commands below are **learner-run instructions**, not observed executions. Start in the project and reuse the existing environment. No new dependency is needed for either estimator. Retain M4's exact working baseline/test/report commands in your notes.

```powershell
Set-Location 'E:\DriveCheck'
.\.venv\Scripts\python.exe -m unittest discover -v
```

Expected after your implementation: old tests and your selected C1 tests pass. No exact test count is promised. A failure is evidence to inspect, not a reason to delete a difficult test.

Expose the following **proposed CLI** by adding a `compare` command to your M4 `drivecheck.py`. It delegates to `comparison.py`, validates the split and saves a complete offline report. Preserve the existing M4 root command `drivecheck.py --config ... --output ...` and its `--output-dir` alias. The new command `drivecheck.py compare --plan ... --output-dir ...` must not require root `--config` or root output arguments as well. These commands do not imply the new path exists now.

A small proposed parser adapter makes that separation explicit. In `drivecheck.py`, route on the leading command word **before parsing** the root parser's required flags. This keeps the old M4 surface working and avoids an `argparse` parent parser rejecting a valid comparison command:

```python
import argparse
from pathlib import Path
import sys


def parse_cli(argv=None):
    words = list(sys.argv[1:] if argv is None else argv)
    if words and words[0] == "compare":
        parser = argparse.ArgumentParser(
            prog="drivecheck.py compare", allow_abbrev=False,
            description="Run the frozen paired comparison plan.",
        )
        parser.add_argument("--plan", type=Path, required=True)
        parser.add_argument("--split", choices=("development", "evaluation"),
                            required=True)
        parser.add_argument("--output-dir", type=Path, required=True)
        parser.add_argument("--debug", action="store_true")
        parser.set_defaults(command="compare")
        return parser, parser.parse_args(words[1:])

    parser = argparse.ArgumentParser(
        prog="drivecheck.py", allow_abbrev=False,
        description="Run the M4 CPU release; use compare --help for C1.",
    )
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", "--output-dir", dest="output_dir",
                        type=Path, required=True)
    parser.add_argument("--debug", action="store_true")
    parser.set_defaults(command="release")
    return parser, parser.parse_args(words)
```

Adapt your existing `main(argv=None)` to receive `(parser, args)`. For `args.command == "release"`, keep the M4 execution path using `args.config` and `args.output_dir`. For `compare`, load `args.plan`, select `args.split` and dispatch to the comparison runner using `args.output_dir`; do not access nonexistent `args.config` there. Each branch validates its complete configuration/paths before writes and uses its selected `parser.error` for input errors. Preserve M4's exit 0/1/2 conventions and helpful diagnostics. The adapter does not replace either runner.

**Parser checks you implement:** root `--help` and `compare --help` succeed; root `--config <file> --output <folder>` and its `--output-dir` alias select release; `compare --plan <file> --split evaluation --output-dir <folder>` selects comparison without root-required flags; missing compare plan/output/split fails with exit 2 and compare-specific usage. These can be argument-only tests; do not run a matrix merely to test parser behavior. Angle-bracket fields in this paragraph are symbolic test values, not literal shell commands.

The old baseline and the new comparison therefore have distinct documented invocations:

```powershell
# Preserved M4 command, run only when you need a new baseline reproduction.
.\.venv\Scripts\python.exe .\drivecheck.py --config .\configs\m4-release.json --output .\outputs\m4-baseline-check-01
# Help paths should not require flags for an unrelated command.
.\.venv\Scripts\python.exe .\drivecheck.py --help
.\.venv\Scripts\python.exe .\drivecheck.py compare --help
```

Then use the proposed C1 path:

```powershell
# Development only: inspect failures and select the method/settings here.
.\.venv\Scripts\python.exe .\drivecheck.py compare --plan .\configs\c1-plan.json --split development --output-dir .\outputs\c1-dev-01
```

Inspect the saved development results before choosing Route B's half-life. For Route A inspect causal correctness and its counterexample; do not invent a tunable multiplier after seeing final evaluation. Save the selection artifact and freeze the evaluation plan/settings.

```powershell
# Final evaluation after the selection artifact has been saved.
.\.venv\Scripts\python.exe .\drivecheck.py compare --plan .\configs\c1-plan.json --split evaluation --output-dir .\outputs\c1-eval-01
Get-Content -LiteralPath .\outputs\c1-eval-01\manifest.json
Get-Content -LiteralPath .\outputs\c1-eval-01\summary.json
Import-Csv -LiteralPath .\outputs\c1-eval-01\cases.csv | Select-Object -First 8
Invoke-Item -LiteralPath .\outputs\c1-eval-01\report.html
```

The manifest should distinguish `running`, `complete`, `failed` and/or `partial` according to the M4 convention; include planned and actual key counts and both methods' statuses. `summary.json` and `cases.csv` must retain failures and denominators. A successful shell exit alone does not prove the correct matrix ran. Compare counts, inspect a contact and non-contact case from each family, inspect the investigated failure, and inspect every case with a changed outcome.

For a repeatability check, run the same frozen evaluation plan into **another** new directory, such as `outputs/c1-eval-02`. Compare structured per-case decisions and numerical metrics under declared tolerances, along with input hashes. Creation timestamps and some artifact metadata may differ; do not require byte identity of entire HTML/PNG files unless you deliberately made them deterministic. Repetition verifies reproducibility on these inputs; it does not create new holdout evidence.

### What the report must show

The case table needs scenario/configuration ID, family, contact status/event/horizon, fault/severity/case seed and resolved stream seeds, method/settings, status, useful/missed/late categories, false-warning episode flag and earliest matched lead. Retain M4's exact current-state error columns **`gap_rmse_m`**, **`closing_rmse_mps`**, **`eligible_error_steps`**, **`total_error_steps`**, **`error_coverage`**, **`missing_steps`** and **`stale_steps`**. Include input/policy/source identities and the development/evaluation label. Do not replace those RMSE fields with differently named MAE values.

At each common decision time, compare each available estimate to truth **at that decision time**. The raw path is a held current-state estimate with an old source; do not score it at its source time while scoring projection at the present time. Preserve source age so the reader can understand its error. Reuse M4's aligned-RMSE mask exactly: decision instants from zero through `min(reference_contact_time_s, horizon_s)` inclusive for a positive episode, or through the horizon inclusive for a negative; include only readings eligible under the same unavailable/stale rule. Count excluded missing/stale steps. Virtual post-contact overlap is outside this RMSE interval; a negative/no-contact episode remains in the metric through its declared horizon.

For eligible set `I` with `n` decision instants, define `gap_error_i = estimated_gap_i - truth_gap_at_decision_time_i` and `closing_error_i = estimated_closing_i - truth_closing_at_decision_time_i`. The unchanged baseline metrics are:

`gap_rmse_m = sqrt(sum(gap_error_i ** 2 for i in I) / n)`

`closing_rmse_mps = sqrt(sum(closing_error_i ** 2 for i in I) / n)`.

For `n = 0`, each RMSE is null, eligible count is zero and coverage is zero if there are decision steps in the interval. A nonempty set of exact zero errors produces numeric 0.0. Preserve M4's handling of a zero total-step denominator rather than inventing a rate. If estimator availability differs, show coverage for each and separately labelled RMSE on their common-time subset too. Do not call a failed execution an unavailable estimate with zero error.

As an independent fixture, reuse M4's constant-speed gaps `[30, 25, 20]` m at times `[0, 1, 2]` s with one-second latency and a teaching freshness limit admitting age 1 s. At times 1 and 2, raw held gaps are 30 and 25 m against current truth 25 and 20 m: errors `[5, 5]` m, so `gap_rmse_m = sqrt((25 + 25)/2) = 5 m`, `closing_rmse_mps = 0 m/s`, and coverage is `2/3`. Under Route A, age projection gives gaps 25 and 20 m: both errors are zero and gap RMSE is 0 m on the same `2/3` coverage. Under M4's worked release age cutoff 0.5 s, both methods have no eligible delayed readings: RMSE is null and coverage `0/3`, not a measured improvement. Keep fixture settings and release settings distinct.

M2/M4's existing MAE columns, **`gap_mae_m`** and **`closing_mae_mps`**, may remain as separately named additional diagnostics on their original documented interval and decision-row weighting. The MAE formula is `sum(abs(error_i)) / n` on that diagnostic's own explicitly named eligible set, with null for no included values. Do not silently narrow its old interval to the RMSE pre-contact mask or compare an MAE aggregate with an RMSE aggregate as if they were the same quantity. If you also calculate pre-contact MAE, give it separate names/mask metadata. For errors `[3, 4]` m on one shared two-row mask, MAE is 3.5 m while RMSE is `sqrt(12.5) ≈ 3.535533906 m`; this known-answer check catches a mislabeled formula.

For lead time report how many positives had useful matches, all misses/late-only episodes, and paired lead differences only where both have the relevant match. State that subset explicitly.

Summarize each family, contact class and fault profile/severity, then overall with visible denominators. Deterministic profiles occur once per scenario with null case seed; stochastic profiles show their actual seed count and variation, for example individual seed values plus median/range. With five stochastic seeds you should not claim statistical significance or broad generalization. Do not fabricate deterministic replicas to balance subgroup sizes or inflate sample size.

Use paired plots for the investigated failure, one loss and one unchanged case. If a category does not occur, report its count as zero and choose another informative case. A useful figure has decision time on x, truth/estimates with units, TTC with the fixed threshold, source-age/arrival markers, the independent contact event and useful-warning window. Mark missing estimates as gaps. Label any post-contact path as virtual kinematics rather than physical impact motion. Share axes across methods where needed so scales do not manufacture a visual improvement.

## 9. Debugging by the symptom you see

| Symptom | Check in this order |
| --- | --- |
| Baseline changes after adding the estimator interface | Compare policy/config hashes, raw values, age handling, inclusive threshold boundaries and warning debounce; finish compatibility before comparing algorithms |
| Both methods improve before a delayed reading arrives | Look for truth in an estimator argument, measurement-time sorting, precomputed future features or replaying all observations at time zero |
| Projection grows gap when closing speed is positive | Re-derive the sign using individual bumper travel; check seconds versus milliseconds and m/s versus km/h |
| Projection changes again at the same decision time | You projected a previous estimate or mutated an observation; recompute from immutable source data |
| Smoothing depends on the decision tick rate | A held reading is ingested repeatedly; update only on newly accepted readings and use measurement elapsed intervals |
| Smoothing behaves differently when cases are reordered | State/RNG is shared between episodes; construct new estimator state and isolate each stream |
| A very smooth curve misses real changes | Inspect filter half-life and the lag fixture; that may be the expected trade-off, not a code defect |
| Error falls while event scores worsen | Check alignment/coverage, then distinguish estimation quality from the nonlinear threshold and useful-warning window |
| Final counts are too small | Reconcile every planned case/seed/method key, exceptions and failed/partial outputs; never silently drop cases |
| Evaluation improves after repeated setting changes | The evaluation set has become development; preserve the history and stop describing it as an untouched test |
| All reported results are “wins” | Recheck definition, seed pairing and omitted losses; show metric-specific changes and unchanged cases explicitly |

If a check exposes a bug in the CPU core, preserve the evidence, fix and reverify the baseline, then produce a clearly identified new baseline snapshot. Compare against that same corrected snapshot. A changed evaluator and changed estimator in one unlabeled comparison cannot isolate the estimator's effect.

## 10. Write the investigation and hand off to M5

Write `docs/c1-investigation.md` after you have actual outputs. Use first person for decisions you made, name AI help honestly, and distinguish supplied scaffolds from your own implementation. A readable report can use these paragraphs:

1. **Question and evidence:** name the observed M4 failure, its exact input identity and how the trace supports the diagnosis.
2. **Method and assumption:** explain the one changed component with a numerical example; state when its assumption can fail.
3. **Experiment design:** give development/evaluation separation, all settings, fixed policy/scoring, cases/seeds, pairing and available-estimate handling.
4. **Results:** include the complete case table and summary denominators; explain wins, losses and unchanged cases rather than selecting only a favorable plot.
5. **Diagnosis:** trace a changed warning from source reading through estimate/TTC to independent scoring. Preserve a regression test and a counterexample.
6. **Conclusion and limits:** state what the finite synthetic comparison supports, what it does not establish, and whether you would retain the raw baseline as default.
7. **Reproduction:** include commands that you actually ran, versions/configuration/source identities, output locations, failed/rerun history and assistance attribution.

A claim such as “this method improves safety” is unsupported. A defensible form, filled with actual evidence, is: “On this declared evaluation matrix, the alternative changed X useful-warning outcomes and Y false-warning episodes; it lost Z cases under the fixed policy. The mechanism was ___. The model assumes ___.” Do not fill X/Y/Z from the teaching fixtures.

### Completion criteria

- [ ] I preserved and reproduced a usable raw CPU baseline, with its original command and complete results.
- [ ] I selected one method from an actual saved failure and can explain its mechanism, prerequisite and failing assumption.
- [ ] My estimator cannot access truth/future observations; both methods share causal streams, source eligibility, decision grid, policy, scenarios/faults and independent scoring.
- [ ] I kept development/tuning cases and seeds separate from final evaluation, froze settings and recorded prior inspection/reruns honestly.
- [ ] Known-answer, causal, compatibility, state/interval and matrix-integrity checks pass in my actual run; I saved the commands/output.
- [ ] Every planned key has two status-labelled method records; failed/partial cases and misses remain visible.
- [ ] My report shows complete metric-specific wins, losses and unchanged cases, counts/denominators, aligned errors/coverage and stated variation/limitations.
- [ ] I can reproduce the comparison and explain one changed outcome plus one loss or counterexample without merely reading the generated prose.
- [ ] I wrote a concise technical handoff for M5 and kept remote CI/publication status separate from local results.

Your handoff to M5 is the preserved baseline identity, frozen C1 plan/selection, actual verification commands/results, complete comparison report, failure/regression evidence, one supported conclusion, limitations and the short explanation you can give. Learner understanding is demonstrated through your attempt and explanation; passing supplied tests or reading this lesson does not establish it.

**Current checkpoint:** the C1 lesson is prepared. Selection of an actual failure/method, learner code, product commands, measured results, report and teach-back are pending. No C1 implementation, benchmark improvement, remote CI success or publication is claimed by this document.
