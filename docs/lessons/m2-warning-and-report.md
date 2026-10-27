# M2 — causal readings, a first warning, and a complete small report

Prepared 27 October 2026. **This is a study-ready lesson for me to implement and run.** Its code snippets, proposed modules, commands and expected results are teaching material. Writing this lesson does not complete the M2 implementation, demonstrate my understanding, or establish a successful experiment run. No product commands were run while preparing it.

I can work through the whole section without sending a reply between steps. Each block gives a reason, a worked example, a concrete implementation task and a check. If I get stuck, I can send the smallest relevant code, command and error. I do not have to finish a block in one sitting.

## Starting point and destination

M1 asks where the bumpers are and when contact occurs. M2 asks a different question: **what warning can a program produce from readings that have actually arrived, and how should I score that warning against an independently established event?**

The learner prerequisite is M1's truth contract, saved configurations, independently checked contact/non-contact fixtures and a labelled plot. Some M1 reference code was already created with AI assistance and is preserved. Its presence is not evidence that I implemented or understand M1. I first work through the M1 lesson and check its results. I do not recreate the existing environment or overwrite the original `outputs/constant_speed.csv`.

The source snapshot inspected for this lesson contains these M1 interfaces:

| Existing reference interface | What M2 needs from it |
| --- | --- |
| `motion.Scenario` | Configuration and `horizon_s` |
| `motion.TruthSample` | `scenario_id`, `sample_id`, `time_s`, bumper positions, both speeds, `gap_m`, `closing_speed_mps` |
| `motion.sample_truth(scenario)` | Ordered clean samples, including time zero and the horizon |
| `motion.truth_at(scenario, elapsed_s, sample_id=0)` | Truth at a specified time, for offline checks/plots only |
| `scenarios.load_fixtures(path)` | Fixtures exposing `scenario`, `reference_contact_time_s`, `reference_final_gap_m`, `reference_basis` |
| `configs/m1-fixtures.json` | Three independently specified fixtures under `drivecheck.truth.v1` |

If my completed M1 uses different names, I map them once at the experiment boundary. I preserve the units and semantics; I do not silently change an event to make this lesson's expected table pass. New M2 interfaces below are **proposed**, aligned with [the study guide](../study-guide.md), rather than claims of existing modules.

At the end I aim to have six evaluated cases: all three M1 fixtures, each clean and with a fixed one-second arrival delay. One local command will save observations, decisions, all case results, configuration, a small offline HTML report and plots. Noise, dropout, stop-and-go, the complete fault matrix and the release/CI work belong to later lessons.

## Block 1 — give a reading two timestamps

Truth describes the synthetic world. An observation describes what a sensor says about that world. Even when its numbers are exact, an observation may arrive too late to describe the present well.

For a reading measured at 2.0 s and delivered at 3.0 s:

- `measurement_time_s = 2.0`: when the physical quantity was sampled.
- `arrival_time_s = 3.0`: the earliest time the warning program may use it.
- At decision time 3.0 s, `observation_age_s = 3.0 - 2.0 = 1.0`.

Arrival age is not zero merely because the reading has just arrived. The one-second journey still happened. All these times use the same scenario-relative simulation clock in seconds, rather than wall-clock time or a call to `sleep`.

Create the proposed `observations.py`. Begin with a small immutable record:

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Observation:
    scenario_id: str
    sample_id: int
    measurement_time_s: float
    arrival_time_s: float
    gap_m: float
    closing_speed_mps: float
```

The sensor adapter may read truth to manufacture synthetic measurements. The warning policy will receive only an `Observation` and the current decision time. It will not receive a `Scenario`, future samples, an event time or a truth callback. Positions are unnecessary for this first policy and stay out of its observation record.

Implement `make_observations(truth_samples, latency_s) -> list[Observation]`. For each sample, copy its gap and closing speed, use `sample.time_s` as measurement time, and use `sample.time_s + latency_s` as arrival time. A clean condition has zero latency. This function must return new records and leave the truth list and its records unchanged. Fixed latency has no random draw: record `seed: null` and `randomness: "none; fixed latency"`.

Implement `validate_observations(observations, scenario_id, horizon_s) -> None` before replay. Use these explicit policies:

| Input issue | M2 policy |
| --- | --- |
| Non-finite or non-numeric time/gap/closing speed, including booleans | Raise `ValueError` with the field and sample ID |
| Negative measurement/arrival time; arrival before measurement | Reject |
| Measurement time beyond the declared horizon | Reject |
| Arrival beyond the horizon | Keep in saved observations; count as not delivered within the horizon |
| Negative gap or closing speed | Allow: overlap and opening motion have defined meanings |
| Wrong scenario ID; missing required field | Reject |
| Duplicate sample ID or duplicate measurement time in one stream | Reject; one sensor reading per measurement time in this contract |
| Noninteger/negative/boolean sample ID | Reject |
| Input list stored in arbitrary order | Allow after validation; replay sorts a copy by arrival |

Also validate latency as finite and nonnegative, and validate the resulting arrival time against overflow. `math.isfinite` is useful, but a boolean passes many numeric checks unless I reject it explicitly. Missing readings later will be omitted records, never `gap_m = 0`.

**My task:** write the generator and validator, then add tests for the 2 s → 3 s example, zero latency, a negative gap that is accepted, an impossible arrival-before-measurement record that is rejected, and a duplicated sample that is rejected. Compare the original truth records before/after generation. Equality with the original immutable records is enough for the small fixture; no file mutation should occur.

**Self-check:** latency changes arrival time only. Measurement time, numeric readings, source IDs, truth configuration and independent reference event stay the same. I should be able to explain why a reading can have zero measurement error and still be poor information for the present.

## Block 2 — replay arrivals without borrowing future knowledge

Replay is a simulated clock plus an arrival queue. It is not a loop that reads `observations[i]` next to `truth[i]` and treats them as simultaneous. That shortcut would erase delay.

Use a declared decision clock consisting of the sorted union of the M1 sampling times and observation arrival times within `[0, horizon_s]`. Include 0 and the horizon. The base sampling times come from the configured measurement schedule; no physical gap/speed values are needed to build them. Including arrivals avoids silently rounding 2.25 s delivery to a 3 s decision. **Never add the true contact time to the decision clock.** Contact is offline evaluation knowledge.

Create proposed `replay.py` and implement:

```python
def make_decision_times(base_times_s, observations, horizon_s):
    """Return finite, unique, increasing times, including 0 and horizon."""
    # Validate the horizon and every base time before building this set.
    # Keep only arrivals <= horizon; validate observations separately.
    raise NotImplementedError("Build the declared clock")

def replay(observations, decision_times_s, warning_threshold_s, max_age_s,
           *, horizon_s):
    """Return one Decision per time; no truth or event argument."""
    raise NotImplementedError("Consume the arrival queue")
```

Implement the clock helper by taking a set of valid times, then sorting it. Reject base times outside the horizon rather than silently discarding them. Validate an externally supplied decision-time list as finite, nonnegative, unique and strictly increasing. In this experiment it must begin at 0 and end at the declared horizon. `horizon_s` gives replay an experiment cutoff for this validation, not a physical event label; do not pass it to `decide`. Do not round times to display precision before comparing them.

The stateful replay algorithm is short enough to trace on paper:

```text
queue = a sorted COPY of observations by (arrival_time_s, sample_id)
next_index = 0
latest = no reading
for now in increasing decision times:
    while queue has a next reading with arrival_time_s <= now:
        consume that reading
        if its measurement_time_s is newer than latest's:
            latest = that reading
        otherwise record that an older measurement arrived and was ignored
    append decide(latest, now, warning_threshold_s, max_age_s)
```

Process **all** arrivals at a time before producing that time's decision. A reading arriving exactly at `now` is available. Sort equal arrivals by sample ID for deterministic processing. The selected reading is the one with the newest measurement time, not the last item received if that item is older. This matters when future variable delays cause overtaking. A late old reading must not move the selected measurement clock backwards.

For example, A measured at 1 s arrives at 3 s; B measured at 2 s arrives at 2.5 s. At 2.5 s B becomes latest. At 3 s A is consumed and logged, but B stays selected. File order does not change this outcome. Duplicate measurement times were rejected in Block 1, so there is no ambiguous tie to resolve here.

Unavailable and stale are different states. Before the first arrival there is no reading. Later there may be a stored reading whose age exceeds the maximum. Keep the stale record's timestamps and values in the trace for diagnosis, but do not use it to make a numeric TTC decision.

**Worked boundary trace:** one reading has measurement time 0, arrival time 1 and gap/closing speed 10 m / 5 m/s. Use decision times `[0, 0.999, 1, 1.25, 1.2501]`, max age 1.25 s and threshold 3 s. Expected states are unavailable, unavailable, fresh/warning, fresh/warning, stale/no warning. At 1 s its age is 1 s and TTC is 2 s. Exactly 1.25 s is accepted; just beyond it is stale.

**My task:** implement the loop with an index into the sorted queue. Add tests for the boundary trace, simultaneous arrivals, the overtaking example, an empty stream and nonuniform decision times. Add a causal regression check: change the values of an observation whose arrival is after time 2; all decisions strictly before its arrival must remain identical. This checks the information boundary instead of merely reusing the TTC formula.

No asynchronous framework or priority queue library is required for this small sorted stream. Keep an ignored-old-arrival count and a beyond-horizon-arrival count in the per-case diagnostics.

## Block 3 — define TTC and every unavailable branch

Time to collision (TTC) is a constant-velocity prediction. With positive gap `d` metres and positive closing speed `c` metres/second, the predicted time is `d/c` seconds **if those current speeds remain unchanged**. SUMO's official following-vehicle definition uses this gap/speed-difference relationship. It does not select a universal safe warning threshold for DriveCheck. [SUMO TTC documentation](https://sumo.dlr.de/docs/Simulation/Output/SSM_Device.html#ttc)

If the gap is 10 m and closing speed 5 m/s, TTC is 2 s. If the lead continues braking, actual contact can occur sooner than that prediction. Sensor error and delay add other discrepancies. In this lesson I deliberately use a transparent baseline: **hold the last arrived values without extrapolating them to now**. Subtracting observation age from TTC or predicting a new gap would introduce another method. I can investigate an alternative later using the same causal inputs and evaluator.

Create proposed `warning_policy.py`, avoiding the name `warnings.py`, which would shadow Python's standard-library `warnings` module. Give each decision a diagnostic reason:

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Decision:
    decision_time_s: float
    sample_id: int | None
    measurement_time_s: float | None
    arrival_time_s: float | None
    observation_age_s: float | None
    gap_m: float | None
    closing_speed_mps: float | None
    ttc_s: float | None
    is_warning: bool
    reason: str
```

`None` means unavailable/not applicable, not zero and not infinity. Save it as JSON null or an empty CSV cell, with `reason` to distinguish branches. Preserve gap/speed and age on stale rows for audit; TTC remains null. Implement `decide(observation, now_s, warning_threshold_s, max_age_s) -> Decision` using this ordered policy:

| Condition, in this order | TTC | Warning | Reason |
| --- | --- | --- | --- |
| No arrived observation | null | False | `unavailable` |
| Observation arrives after now or measurement is in the future | Error | No result | Reject caller/stream bug |
| Age `> max_age_s` | null | False | `stale` |
| Fresh `gap_m <= 0` | 0 | True | `contact_or_overlap` |
| Fresh positive gap, `closing_speed_mps <= 0` | null | False | `not_closing` |
| Fresh positive gap/closing speed and TTC `<= threshold` | finite TTC | True | `ttc_warning` |
| Fresh positive gap/closing speed and TTC `> threshold` | finite TTC | False | `ttc_clear` |

Validate `now_s`, max age and threshold as finite numbers; `now_s` and max age are nonnegative, threshold is positive. Reject non-finite computed TTC rather than silently serializing overflow as infinity. A no-warning stale/unavailable row means the baseline lacks a valid numeric decision; it does **not** certify safety. The report must show these states.

For the first experiment choose threshold **3.0 s**, maximum age **1.25 s**, pre-event window **4.0 s**, and minimum useful lead **1.0 s**. These are declared experiment conventions chosen for an inspectable teaching example. They are not regulatory values, human response-time claims or driving advice. Record them before looking at report output. An age limit above the one-second delay lets the delay experiment expose old-but-accepted readings instead of suppressing every delayed reading.

**My task:** implement one branch at a time and write table-driven tests with `unittest.subTest`. Use these fixed expected answers:

| Fresh inputs | Expected |
| --- | --- |
| Gap 10, closing 5, threshold 3 | TTC 2; warning |
| Gap 15, closing 5 | TTC 3; warning at the inclusive threshold |
| Gap 15.5, closing 5 | TTC 3.1; clear |
| Gap 10, closing 0 or −2 | null TTC; not closing |
| Gap 0 or −1, closing −2 | TTC 0; contact/overlap branch takes precedence |
| Gap 0, age 1.2501 with max age 1.25 | null TTC; stale takes precedence |

I can first implement this small control-flow spine, filling the record constructor and validated values myself:

```python
if observation is None:
    ...  # unavailable Decision
age_s = now_s - observation.measurement_time_s
if age_s > max_age_s:
    ...  # stale Decision
elif observation.gap_m <= 0:
    ...
elif observation.closing_speed_mps <= 0:
    ...
else:
    ttc_s = observation.gap_m / observation.closing_speed_mps
    ...
```

The omitted validation belongs before the physical branches. Ellipses are exercise markers, not a complete program. The expected-answer tables let me finish and check the branches without waiting for another chat reply.

For a first concrete test in `test_m2.py`, use the proposed imports and API above:

```python
import unittest
from observations import Observation
from warning_policy import decide

class TestReadingAge(unittest.TestCase):
    def test_arrival_does_not_reset_measurement_age(self):
        reading = Observation("fixture", 0, 0.0, 1.0, 10.0, 5.0)
        decision = decide(reading, 1.0, 3.0, 1.25)
        self.assertEqual(decision.observation_age_s, 1.0)
        self.assertEqual(decision.ttc_s, 2.0)
        self.assertTrue(decision.is_warning)
        stale = decide(reading, 1.2501, 3.0, 1.25)
        self.assertEqual(stale.reason, "stale")
        self.assertIsNone(stale.ttc_s)
        self.assertFalse(stale.is_warning)
```

This test stores an independently specified age and TTC; it does not call another copy of the production formula to get its expected answer. Add the remaining table rows rather than stopping after this example.

## Block 4 — score against an independent event

A warning is a policy output; contact is a model event. If I label a case positive whenever TTC is below my threshold and then use that same threshold to score the warning, the evaluation rewards its own definition. Instead M1 supplies an independent continuous-trajectory contact time and derivation. The evaluator may read future truth; the warning policy may not.

For M1's braking-contact fixture, the lead rear position during braking is `30 + 15t - 2.5(t-1)^2`; the ego front is `20t`. Equating positions gives `t² = 11`, so contact is `sqrt(11) ≈ 3.3166247903554 s`, within its 5 s horizon. This answer is independent of the TTC threshold, replay clock and first nonpositive sampled row. M1's 4 s sample is already past contact and is not the exact event time.

Fix this scoring policy in proposed `evaluation.py` before producing the experiment report:

1. An episode is the declared scenario on `[0, H]`. A positive episode has one independent reference contact `e` in that interval. A negative episode has no contact within it. Initial contact at zero is positive; contact exactly at H is positive. Do not use an event beyond H as a positive label.
2. For a positive episode, consider true warning **decision timestamps** within `[max(0, e-W), e]`, where W is the pre-event window. Use the earliest timestamp `w` in that window. This is a discrete-decision convention; do not infer unsampled warning times.
3. If no such timestamp exists, outcome is `missed`, with null matched lead. A warning after contact does not rescue a miss. Retain early-outside-window and post-contact warning counts as diagnostics.
4. Otherwise lead is `e-w`. If lead is at least the minimum useful lead U, outcome is `useful`; if lead is smaller, outcome is `late`. A warning exactly at contact is late. A late episode is not also counted as missed under this definition.
5. Multiple true decisions do not create multiple matched contacts. Count warning activations separately as False→True transitions, starting from False. An unavailable/stale/no-warning decision ends the activation. For matching, an already-active warning can qualify through a true decision inside the window; its original onset alone is not the only candidate.
6. A negative episode with any true warning decision in `[0,H]` is a `false_warning` episode; otherwise it is `clear_negative`. Its false-warning-episode contribution is 1 or 0 even if it contains many warning activations. Report the activation count as a separate diagnostic if useful.

Validate finite event/horizon/policy times, `0 <= e <= H` when e exists, `W > 0`, and `0 < U <= W`. Requiring a positive useful-lead minimum keeps a warning at contact classified as late. Validate increasing finite decision times within `[0,H]`. Use exact inclusive comparisons on stored times; do not introduce a broad tolerance that turns an after-event warning into a before-event one. In assertions on calculated lead, use a small explicit tolerance such as `1e-9 s`. Preserve full precision in saved results and round only for display.

Implement these proposed functions:

```python
def score_case(decisions, reference_contact_time_s, horizon_s,
               pre_event_window_s, minimum_useful_lead_s):
    """Return outcome, earliest matched warning, lead, and diagnostics."""
    raise NotImplementedError("Implement the six scoring rules")

def summarize(case_results):
    """Report counts/rates by condition, including invalid/failed cases."""
    raise NotImplementedError("Keep denominators explicit")
```

**Independent metric fixtures:** use literal warning times rather than calling the TTC policy to manufacture expectations. Here `e=5`, `H=8`, `W=4`, `U=1`; thus the matching window is `[1,5]`.

| True warning decision times | Expected outcome | Earliest matched lead |
| --- | --- | --- |
| None | missed | null |
| 0.5 only | missed; one early warning | null |
| 1, 4.5 | useful, one matched event | 4 s |
| 4 exactly | useful | 1 s |
| 4.25 | late | 0.75 s |
| 5 exactly | late | 0 s |
| 5.01 only | missed; one post-contact warning | null |
| 0.5, 2, 3 | useful through the 2 s decision | 3 s |

Add a separate zero-event fixture: `e=0`, a warning at 0 is late with zero lead; no warning at 0 is missed. For `reference_contact_time_s=None`, repeated true rows in a negative episode still contribute only one false-warning episode. Supply false rows between activations to test that activation counting differs from counting true rows.

Also test a contact exactly at the horizon (`e=H=8`): it is positive, and a warning at 8 is late with zero lead. With `e=5`, compare a lone warning at 0.999999 against one at 1 exactly: missed versus useful under the inclusive four-second window. A stored reference event at 8.001 with H=8 is inconsistent input and must be rejected, not rounded inside the horizon.

For summary testing, construct five **literal scored outcomes**: one useful positive, one late positive, one missed positive, one negative with warning and one clear negative. Expected: 3 positives, 2 negatives, miss rate `1/3`, late count 1, false-warning-episode rate `1/2`. Also show `(late + missed)/positive = 2/3` as the fraction without a useful warning, so a reader cannot mistake the low miss count for timely performance. With no positives/negatives, the corresponding rate is null, not zero. Partition useful+late+missed must equal the number of successfully scored positives.

Make the return contract explicit while implementing: `score_case` returns keys `outcome`, `first_matched_warning_time_s`, `matched_lead_s`, `first_warning_time_s`, `warning_activation_count`, `early_warning_decision_count`, and `post_contact_warning_decision_count`. It also records `reference_contact_time_s` and `horizon_s`. All matched fields are null for a miss or a negative. `first_warning_time_s` can still exist for an unmatched early/post-contact warning, which is why it differs from the first matched time. A simple safe rate helper is `numerator / denominator if denominator else None`; store numerator and denominator as well as the rate.

**My task:** implement scoring and its tests before wiring it into the real trajectory experiment. Do not adjust W, U or the warning threshold to turn a disappointing outcome into a success. Later changes require a new saved configuration and an explanation.

## Block 5 — predict the clean-versus-delay experiment by hand

Use all three M1 fixtures unchanged. They provide one positive and two negative episodes **per condition**. One negative is a short constant-speed horizon; the other is lead braking without contact within its horizon. They are a tiny demonstration, not a representative benchmark.

For the contact fixture, compute distances rather than asking the production policy for the answer:

| Measurement time | Ego front | Lead rear | Gap | Closing speed | Constant-speed TTC |
| --- | --- | --- | --- | --- | --- |
| 0 s | 0 m | 30 m | 30 m | 5 m/s | 6 s |
| 1 s | 20 m | 45 m | 25 m | 5 m/s | 5 s |
| 2 s | 40 m | 57.5 m | 17.5 m | 10 m/s | 1.75 s |
| 3 s | 60 m | 65 m | 5 m | 15 m/s | 1/3 s |

At 2 s, braking has lasted one second: the lead travels `15 + (15*1 - 0.5*5*1²) = 27.5 m` from its initial rear position 30 m. Ego travels 40 m. The gap is 17.5 m and lead speed is 10 m/s. The 1.75 s TTC prediction differs from the actual remaining `sqrt(11)-2 ≈ 1.316625 s` because braking continues.

For clean observations, the 2 s reading arrives at 2 s and immediately warns. With one-second delay, it arrives at 3 s, has age 1 s, and is still allowed by the 1.25 s age rule. At decision time 2 s, the delayed baseline only has the 1 s reading: TTC 5 s, so it stays clear. The resulting predicted comparison is:

| Scenario / declared horizon | Independent contact | Clean first warning / outcome | 1 s latency first warning / outcome |
| --- | --- | --- | --- |
| `constant_speed_original`, 4 s | None within H | 3 s / false-warning episode | 4 s / false-warning episode |
| `lead_braking_contact`, 5 s | `sqrt(11)` s | 2 s / useful; lead ≈1.316625 s | 3 s / late; lead ≈0.316625 s |
| `lead_braking_noncontact`, 8 s | None within H | 7 s / false-warning episode | 8 s / false-warning episode |

The constant-speed row has gap 15 m at time 3, closing speed 5 m/s, hence TTC 3 s. Contact would occur at 6 s, outside its declared 4 s horizon. The non-contact braking row has lead rear x=100 m after it stops at 5 s. At 7 s ego front x=70 m, so gap 30 m / closing 10 m/s gives TTC 3 s. Contact would occur at 10 s, outside its 8 s horizon. Calling these false-warning episodes is a consequence of the declared finite-horizon convention; it does not show that the rule is physically irrational. The report needs that limitation beside the result.

Expected per-condition totals, **predictions rather than observed runs**:

| Condition | Positives / negatives | Useful / late / missed | False-warning negative episodes |
| --- | --- | --- | --- |
| clean | 1 / 2 | 1 / 0 / 0 | 2 / 2 |
| fixed latency 1 s | 1 / 2 | 0 / 1 / 0 | 2 / 2 |

A zero miss rate here conceals the late warning in the delay condition unless I also show late/useful counts. Do not pool the two conditions as independent replications of different worlds. Each condition uses the same three underlying scenarios. There is one deterministic run per condition, no random seeds or confidence interval to estimate.

**My task:** before running the integrated experiment, trace the delayed contact case at decision times 0, 1, 2, 3 and 4. Write selected sample ID, both reading timestamps, age, TTC, warning and reason. At 0 there is no arrived reading; at 3 the selected measurement time must be 2. If I see time 3's gap at decision time 3 under one-second delay, I have leaked future availability.

## Block 6 — wire the section into one inspectable command

Use the following proposed responsibilities. Small modules keep a physics error separate from a queue or scoring error.

| Proposed file I create | Responsibility |
| --- | --- |
| `observations.py` | Observation record, validation, clean/fixed-latency adapter |
| `warning_policy.py` | Decision record and causal TTC branches |
| `replay.py` | Decision clock, arrival release, newest-measurement selection |
| `evaluation.py` | Independent event scoring, aligned errors and summaries |
| `experiments.py` | Configuration, case enumeration, execution and status records |
| `reporting.py` | CSV/JSON, local HTML and plots; no decision-making |
| `drivecheck.py` | Small `argparse` entry point calling the experiment runner |
| `test_m2.py` | Policy/arrival/metric fixtures and one integration check |
| `configs/m2-experiment.json` | The declared six-case teaching experiment |

Create this proposed configuration when implementing the lesson:

```json
{
  "schema_version": "drivecheck.m2.v1",
  "fixtures_path": "configs/m1-fixtures.json",
  "scenario_ids": [
    "constant_speed_original",
    "lead_braking_contact",
    "lead_braking_noncontact"
  ],
  "conditions": [
    {"condition_id": "clean", "latency_s": 0.0, "seed": null},
    {"condition_id": "latency_1s", "latency_s": 1.0, "seed": null}
  ],
  "warning": {"threshold_s": 3.0, "max_age_s": 1.25},
  "scoring": {"pre_event_window_s": 4.0, "minimum_useful_lead_s": 1.0},
  "decision_clock": "sample_times_union_arrivals_within_horizon"
}
```

Reject unknown schema version, unknown/duplicate scenario and condition IDs, duplicate JSON keys, missing/unknown settings, invalid numeric values and an empty experiment. For now seed must be null because this adapter has no randomness. A new noise model later will introduce a distribution, units and seed explicitly. An invalid top-level configuration fails before writing a run.

Implement `experiments.run(config_path, output_dir) -> dict`. This is the orchestration recipe, not a finished implementation:

```text
load and validate configuration; select every requested M1 fixture
build every (scenario, condition) case and unique case ID
validate all input/output paths; require a fresh output folder
write manifest with status running and every case marked pending
for every case:
    generate the scenario truth (same values for both conditions)
    generate/validate observations with the configured delay
    form decision clock; replay with warning policy
    score against fixture.reference_contact_time_s offline
    compute offline aligned error diagnostics
    save observations, decisions, result and plot
    set case status complete
    on case error: record failed + error and continue the remaining cases
aggregate completed cases; include expected/completed/failed counts
write report and set overall status complete, partial or failed
if reporting itself fails: retain machine-readable status/error
return manifest; CLI exits nonzero for any failure or partial run
```

For failed cases, keep the known scenario/reference label and the error. Show planned positive/negative counts, successfully scored positive/negative counts, and unscored counts separately. Compute metric rates over successfully scored cases and label that denominator explicitly; never treat an execution failure as a clear negative or silently present a partial subset as the full experiment. If scoring succeeded but plotting failed, retain its diagnostic data, label the case incomplete/failed, and show that status. A full accepted six-case run has no unscored cases.

Do not call `first_contact_time` to create M2 labels afresh or derive labels from warnings. The M1 computed contact can be checked against its stored independent reference; the stored reference/derivation supplies this fixture's evaluation target. Do not pass that target into replay. Run a whole case through its horizon, including virtual post-contact truth; only offline scoring excludes post-contact warnings from matching.

Resolve fixture/config/output paths under the project root (`Path(__file__).resolve().parent` in a root module). Reject any path escaping it. Use a new ignored directory such as `outputs/m2-first`; refuse an existing destination rather than overwrite previous evidence. Validate before `mkdir`. Restrict IDs to safe filename characters and reject Windows reserved names, or use deterministic numeric case folders plus an ID manifest. Preserve all source/config/M1 artifacts.

Save this output contract per case:

| Artifact | Required contents |
| --- | --- |
| `observations.csv` | Every generated record, including arrivals after H |
| `decisions.csv` | Every decision with timestamps, age, selected ID, gap, closing speed, TTC, warning and reason |
| `result.json` | Case ID/status, full scenario/condition, H, independent event/basis, outcome/lead, warning/availability counts, aligned errors |
| `timeline.png` | Truth, readings actually selected at decision times, warning/TTC, arrival/age evidence and event/horizon markers |

At run level save `manifest.json`, `results.json`, `cases.csv`, the exact effective configuration, and `report.html`. Record runtime/dependency versions and SHA-256 hashes of fixture/configuration/source files used. A hash identifies bytes; it does not prove correct physics. Generated runs stay under ignored `outputs/`. Failed cases still get a row/status/error and cannot disappear from the HTML or denominator explanation.

**Error alignment:** compute gap and closing-speed mean absolute error only offline, comparing a fresh selected observation at decision time `t` with `truth_at(scenario, t)`. This measures error in treating held readings as present values. Save separate counts for included, unavailable and stale decision rows, and the decision-row weighting convention. Do not silently compare a delayed measurement with truth at its measurement time and call that current-state accuracy. For the clean exact stream current-time errors should be zero at the declared decision times. For the delayed contact case at t=3, selected gap is 17.5 m but current truth gap is 5 m: absolute gap error **12.5 m**. Selected closing speed is 10 m/s versus current 15 m/s: error **5 m/s**. These truth comparisons must never affect policy decisions.

Measurement-time error may also be reported with that explicit label: a pure-delay exact sensor has zero error against truth at measurement time. The two alignments answer different questions. Unavailable/stale rows have no included numeric estimate, so do not fill their errors with zero. If there are no included rows, MAE is null with count zero. Repeated decision rows give a decision-weighted mean, not a time-weighted integral; changing the decision schedule can change that aggregate.

### A small offline report I can actually read

The HTML report should open directly from disk with a local `timeline.png` for each case. Use `html.escape` for dynamic text, relative local image links and an ordinary HTML table. No CDN, hosted service or JavaScript framework is necessary. A compact template is enough:

```python
from html import escape

case_section = (
    f"<h2>{escape(case_id)}</h2>"
    f"<p>Status: {escape(status)}; outcome: {escape(outcome)}</p>"
    f'<img src="{escape(relative_plot_path, quote=True)}" '
    'alt="Gap, TTC and reading age on the decision timeline">'
)
```

First display run status, expected/completed/failed counts, the full per-condition table, then every per-case row. Show numerator/denominator next to rates. Include no-positive/no-negative groups as not applicable, not 0%. Put the experimental thresholds, horizons, null/stale rules and finite-horizon false-warning limitation next to the results. Show null lead as “no matched warning,” not 0 s. A miss should remain visible beside the successful lead times.

Use the plotting tool already selected in M1 if it works in my environment; do not introduce a new plotting stack here. For Matplotlib, follow M1's noninteractive `Agg` approach. The plot is an offline evaluator artifact and may show truth/contact. A useful three-panel design is:

1. Signed true gap with units and zero line, plus held selected readings at **decision time**. Label that the reading was measured earlier; do not shift its original measurement timestamp in the CSV.
2. Finite TTC in seconds, threshold line, true warning decision markers and shaded unavailable/stale regions or distinct markers. Null TTC is a gap in the plot.
3. Observation age in seconds and the 1.25 s limit; measurement-to-arrival arrows for a few readings if that clarifies the delay.

Add H and the independent contact marker to every shared time axis where appropriate. Use a dense offline truth curve from `truth_at` for a braking plot, rather than suggesting that straight lines between sparse samples are the exact path. Annotate negative gap after contact as virtual overlap without impact dynamics. Close figures after saving. Visually check all six plots: axis labels/units, threshold, exact event between samples, clean/delayed timing, readable legends, no joined line across unavailable data and no scale that hides the delay.

**My task:** implement the runner in the order in the recipe. First inspect one JSON/decision table before spending time on HTML styling. Then include every case. Make the report explain what happened, even when all negative episodes warn.

## Block 7 — commands, independent checks and debugging

The following are **commands for me to run after I implement the proposed files**. They were not executed to author this lesson. Keep using the existing project interpreter; M1's tested dependency instructions apply if plotting support is missing. Do not create a second environment automatically.

```powershell
Set-Location 'E:\DriveCheck'
.\.venv\Scripts\python.exe -m unittest -v test_motion test_m1 test_m2
.\.venv\Scripts\python.exe .\drivecheck.py --config .\configs\m2-experiment.json --output-dir .\outputs\m2-first
Get-Content -LiteralPath .\outputs\m2-first\cases.csv
Get-Content -LiteralPath .\outputs\m2-first\manifest.json
```

`test_m1` is the existing AI reference test module at the inspected snapshot. If my completed M1 organizes its tests differently, use its documented command plus `test_m2`; do not delete the original `test_motion` fixture. `drivecheck.py` should parse `--config` and `--output-dir`, call `experiments.run`, print status/case totals/output path, and return a nonzero exit code for partial/failed runs. Keep execution under `if __name__ == "__main__":` so importing the entry point does not generate a report.

Open `E:\DriveCheck\outputs\m2-first\report.html` in a browser locally after generation. Expected checks are the six-case prediction table in Block 5, not a prescribed exact test count or runtime. Inspect the delayed contact case's `decisions.csv` and locate the time-3 row: measurement time 2, arrival 3, age 1, gap 17.5, closing speed 10, TTC 1.75, warning true. The result must use `sqrt(11)-3`, not `4-3`, as matched lead.

For reproducibility, run the same command again with a **new** output folder:

```powershell
.\.venv\Scripts\python.exe .\drivecheck.py --config .\configs\m2-experiment.json --output-dir .\outputs\m2-repeat
Get-FileHash -LiteralPath .\outputs\m2-first\cases.csv -Algorithm SHA256
Get-FileHash -LiteralPath .\outputs\m2-repeat\cases.csv -Algorithm SHA256
```

Canonical case/observation/decision data should match for this deterministic configuration. Keep volatile execution timestamp/output path metadata separate from canonical metrics so they do not create false differences. Matching data hashes in this environment do not establish cross-platform plot identity or clean-environment reproduction; those release checks come later.

Add one integration test using `tempfile.TemporaryDirectory(dir=ROOT / "outputs")` after creating the ignored output parent if necessary. Pass a nonexistent child folder to the runner so it satisfies the fresh-directory rule. Assert six result rows, the exact predicted first-warning times/outcomes, all case statuses complete, readable artifact paths and unchanged original truth. Read JSON/CSV back and verify fields, not only file existence. If an integration test must simulate a case failure, use `unittest.mock` to raise for one selected case; assert the failed row/error, remaining case rows and overall partial status survive. A zero exit code alone is not enough.

Python's standard-library test runner supports running named modules with `-m unittest -v`; `assertAlmostEqual`/explicit tolerances and `assertRaises` help express numeric and rejection fixtures. [Python 3.14 unittest](https://docs.python.org/3.14/library/unittest.html)

Save JSON with UTF-8 and `json.dumps(data, indent=2, allow_nan=False)`, and write one complete object per JSON file. Convert no-finite-TTC to null before serialization rather than allowing nonstandard Infinity/NaN values. [Python 3.14 JSON documentation](https://docs.python.org/3.14/library/json.html)

| Symptom | First place to inspect |
| --- | --- |
| Delay produces the same time-2 contact warning as clean | Replay availability check; did time-2 values arrive at time 3? |
| Newly delivered reading always has age zero | Age calculation; it is now minus measurement time, not arrival time |
| Delayed condition has no warnings at all | max-age value/units and ordering of stale branch; 1 s is accepted under 1.25 s |
| Old arriving packet replaces a newer measurement | Selection uses arrival rather than measurement time |
| Contact time changes when warning threshold changes | Circular label generation or truth/config mutation |
| Report says contact is at 4 s | First sampled overlap substituted for independent continuous event |
| Multiple true rows inflate event count | Counting warning rows rather than one matched reference event |
| Negative false-warning rate uses six as denominator | Conditions pooled or all cases used instead of per-condition negative episodes |
| Clean and delay have zero current-time errors everywhere | Evaluation aligned to measurement time only, or future truth leaked into policy |
| NaN/Infinity breaks JSON or HTML | Null/reason handling and finite validation |
| Second run mixes old and new case files | Require a fresh destination; do not reuse an old run directory |
| Missing image offline | Relative path from report location and saved file existence |

Do not fix a failure by changing a known answer to whatever the program prints. Return to the first layer where the trace diverges: truth, observation timestamps, selection, TTC, score, summary, serialization. Record the input and a regression assertion after finding the cause.

## Block 8 — my meaningful change, completion evidence and M3 handoff

After the default experiment matches the independent checks, make one bounded change in a **copied** M2 configuration: set `max_age_s` to 0.75 while keeping delay at 1 s. Predict first. Every selected delayed reading is at least 1 s old at arrival, so it is stale at every decision where it exists. Expected delayed outcomes: the contact episode is missed, both negative episodes have no warning, and TTC remains null on stale rows. That lower false-warning rate comes with unavailable numeric decisions and a missed contact; it is not an established improvement. Clean results should be unchanged. Preserve the default configuration and both reports.

Alternatively, change latency to 0.5 s with the original 1.25 s age limit. The 2 s reading arrives at 2.5 s, so its first contact warning should occur at 2.5 s; lead is `sqrt(11)-2.5 ≈ 0.816625 s`, still late under the 1 s useful-lead rule. The union-arrival clock is necessary to see 2.5 s. This is a good check that the implementation is not hard-coded to integer steps.

I can mark the **technical M2 work** complete only after I have observed these items, and record the exact run evidence separately from my explanation:

- Separate truth/observation records, explicit units and validated timestamps; truth unchanged by the fault.
- Causal sequential replay with boundary/overtaking/nonuniform-time fixtures, newest-measurement selection and visible unavailable/stale states.
- TTC branches and inclusive threshold/age/contact policies checked against fixed answers.
- Independent event/window/useful/late/missed/negative-episode scoring checked with literal metric fixtures.
- One command producing all six case rows, settings, local plots, machine-readable results and an offline report, with any failure honestly labelled.
- Default first-warning/outcome values checked against Block 5; a repeated canonical-data run checked; original M1 artifacts preserved.
- One changed-age or fractional-delay prediction/run explained, including its trade-off and a known limitation.

My understanding is evidenced when I can trace one arrived reading through age → TTC → warning → event matching, explain why TTC and exact contact differ, and explain why a finite-horizon negative can still warn. Running a generated test suite alone does not establish this. No remote CI, user commit or publication follows automatically from this lesson.

For a concise review/handoff I can supply: my changed files, exact test command and observed summary, the report path, the time-3 delayed decision row, the default comparison table, my changed-setting prediction/result and one issue I still cannot explain. My coach can update the shared checkpoint/README from that evidence. I do not need to paste private chat transcripts.

M3 starts with these explicit contracts: `Observation` measurement/arrival fields, ordered arrival replay, latest-measurement policy, age limit, causal `Decision` fields, independent event scoring and complete per-case results. It expands single-fault noise/latency/dropout and adds stop-and-go, while preserving the M2 regression cases. It does not silently combine faults, retune the default to manufacture a gain or pass future truth into the algorithm. Full release reproduction, the complete matrix and actual remote CI evidence remain M4 work.

**Lesson status:** ready for self-paced implementation and review. **Project/learning status:** M2 implementation, observed checks and learner explanation remain pending until I perform and inspect them.
