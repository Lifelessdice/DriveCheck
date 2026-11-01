# C1 Block 2 — Connect estimates to causal replay and the shared policy

Prepared 2 November 2026. This is supplied learner code, not assistant-implemented product work. Block 1 remains accepted at 15 focused/184 full tests. Local checkpoint `35a0447` and its configured tracking ref match on `feature/c1-fair-comparison`; tracked files were clean before this documentation update. No live remote/CI check, new product run or Git mutation was performed to deliver this block. C1 remains **1 of 5 blocks technically verified** until this block is saved, run and reviewed.

## Outcome and theory

Block 1 estimates a gap. This block makes a warning from that estimate, using the **same** policy gates and TTC branches as the baseline. Reuse the arrival queue; do not write a second queue or manufacture a new observation at the decision time.

The order is: release arrived readings → choose the newest measurement → enforce original source age → estimate state → apply shared TTC rule → evaluate offline. Projection changes the values used by the TTC calculation; it cannot change the source age, clock, latest-reading selection, warning threshold or independent reference event.

We will make two small baseline extensions: extract the existing eligibility/TTC logic into shared helpers in `warning_policy.py`, and add an optional decision callback to `replay.py`. Default replay still uses `decide`. Neither baseline module imports a C1 module, so the existing M4 source-copy workflow does not acquire an undeclared C1 dependency. The source hashes will change: compatibility means unchanged baseline behavior, not byte-identical source to the archived M4 revision. Do not overwrite archived evidence or label the new revision as the old one.

The new `c1_replay.py` records both the immutable source and the estimate. Its ordinary `Decision.gap_m` contains the value actually used by the policy, allowing the existing evaluator to score the correct estimate. The trace separately retains `source.gap_m` and source timestamps. A projected contact is a model output, never a ground-truth event label.

### Hand check grounded in the existing failure

Use the separate constant-speed diagnostic: contact6s, fixed0.5s decision grid, threshold2s, max-age3s, matching window3s and useful lead1s. At decision3.5, sourceID1 measured1/arrived3.5 has gap25/closing5/age2.5: projection12.5m/TTC2.5, still clear. At decision4, the same source has age3: projection10m/TTC2, warning. Its predicted earliest lead is2s, useful. Raw first warning under delay2.5 remains absent through H6. Both retain3 observations arriving beyond H. These are predictions for the supplied tests, not measured final-evaluation results.

The main M4 age limit stays1.25s. The diagnostic limit stays3s. An already-stale sample is rejected before projection, even if projection would produce an urgent estimate or overflow.

## 1. Extract shared policy helpers in `warning_policy.py`

Keep the existing imports, `Decision` record and `validate_warning_settings` function unchanged. Replace the existing `decide` function through the end of the file with these helpers and replacement `decide`:

```python
def prepare_decision(
    observation,
    now_s,
    warning_threshold_s=3.0,
    max_age_s=1.25,
):
    """Validate source availability and preserve its original age and values."""
    require_finite("now_s", now_s, minimum=0)
    validate_warning_settings(warning_threshold_s, max_age_s)
    if observation is None:
        return Decision(decision_time_s=now_s)
    if not isinstance(observation, Observation):
        raise ValueError("observation must be an Observation or None")
    if observation.arrival_time_s > now_s or observation.measurement_time_s > now_s:
        raise ValueError("the observation is not available at now_s")

    age_s = now_s - observation.measurement_time_s
    base = Decision(
        decision_time_s=now_s,
        sample_id=observation.sample_id,
        measurement_time_s=observation.measurement_time_s,
        arrival_time_s=observation.arrival_time_s,
        observation_age_s=age_s,
        gap_m=observation.gap_m,
        closing_speed_mps=observation.closing_speed_mps,
        reason="pending",
    )
    if age_s > max_age_s:
        return replace(base, reason="stale")
    return base


def ttc_from_state(gap_m, closing_speed_mps, warning_threshold_s=3.0):
    """Apply the unchanged TTC branches to finite signed state values."""
    require_finite("gap_m", gap_m)
    require_finite("closing_speed_mps", closing_speed_mps)
    require_finite("warning_threshold_s", warning_threshold_s, positive=True)
    if gap_m <= 0:
        return 0.0, True, "contact_or_overlap"
    if closing_speed_mps <= 0:
        return None, False, "not_closing"
    ttc_s = gap_m / closing_speed_mps
    require_finite("computed ttc_s", ttc_s, minimum=0)
    warning = ttc_s <= warning_threshold_s
    return ttc_s, warning, "ttc_warning" if warning else "ttc_clear"


def decide(observation, now_s, warning_threshold_s=3.0, max_age_s=1.25):
    """Apply the original policy to arrived, eligible held measurements."""
    base = prepare_decision(observation, now_s, warning_threshold_s, max_age_s)
    if base.reason != "pending":
        return base
    ttc_s, warning, reason = ttc_from_state(
        base.gap_m, base.closing_speed_mps, warning_threshold_s
    )
    return replace(base, ttc_s=ttc_s, is_warning=warning, reason=reason)
```

`pending` is an internal intermediate state, not a new completed decision category. Both paths must replace it before emitting an eligible decision. Preserve contact/overlap before not-closing: a nonpositive used gap gives TTC0 even with opening speed. Threshold and freshness comparisons remain inclusive at their existing boundaries.

## 2. Add an optional policy callback to `replay.py`

Keep all existing validation, sorting, queue selection, clocks and counters. Make only these three edits.

A callback is an ordinary function passed to another function. Here replay owns **when** a decision is made and **which reading** is available; the supplied function owns **how** that selected state becomes a decision. The default remains the existing `decide`. This keeps one causal timing implementation instead of copying a queue into the estimator module.

First, add a keyword-only parameter after `horizon_s` in the existing signature:

```python
    *,
    scenario_id,
    horizon_s,
    decision_function=None,
):
```

Second, immediately after its docstring, select the existing default and reject a bad callback:

```python
    decision_function = decide if decision_function is None else decision_function
    if not callable(decision_function):
        raise ValueError("decision_function must be callable or None")
```

Third, inside the existing decision-time loop, replace the `decisions.append(decide(...))` block with:

```python
        decision = decision_function(
            latest, now_s, warning_threshold_s, max_age_s
        )
        if not isinstance(decision, Decision) or decision.decision_time_s != now_s:
            raise ValueError("decision_function must return a Decision at now_s")
        decisions.append(decision)
```

The callback receives only the selected observation, current decision time and policy settings. It receives no truth, event label, future observation or scenario trajectory. Existing calls omit it and continue through `decide`.

## 3. Create `c1_replay.py`

```python
"""Causal estimator replay with original-source and used-state evidence."""

from dataclasses import dataclass, replace

from c1_estimators import METHODS, StateEstimate, estimate_state
from observations import Observation
from replay import ReplayResult, replay
from warning_policy import Decision, prepare_decision, ttc_from_state


@dataclass(frozen=True)
class DecisionRecord:
    """Retain the original input separately from estimated/used state."""
    source: Observation | None
    estimate: StateEstimate | None
    decision: Decision


@dataclass
class EstimatedReplayResult:
    replay: ReplayResult
    records: list[DecisionRecord]


def decide_with_estimator(
    observation, now_s, warning_threshold_s=3.0, max_age_s=1.25,
    *, method="raw",
):
    """Apply common source gates before estimating and applying common TTC."""
    if method not in METHODS:
        raise ValueError(f"unknown estimation method: {method!r}")
    base = prepare_decision(observation, now_s, warning_threshold_s, max_age_s)
    if base.reason != "pending":
        return DecisionRecord(observation, None, base)

    estimate = estimate_state(observation, now_s, method)
    ttc_s, warning, reason = ttc_from_state(
        estimate.gap_m, estimate.closing_speed_mps, warning_threshold_s
    )
    decision = replace(
        base,
        gap_m=estimate.gap_m,
        closing_speed_mps=estimate.closing_speed_mps,
        ttc_s=ttc_s,
        is_warning=warning,
        reason=reason,
    )
    return DecisionRecord(observation, estimate, decision)


def replay_with_estimator(
    observations, decision_times_s, warning_threshold_s=3.0, max_age_s=1.25,
    *, scenario_id, horizon_s, method="raw",
):
    """Reuse the validated arrival queue; collect one evidence record per tick."""
    if method not in METHODS:
        raise ValueError(f"unknown estimation method: {method!r}")
    records = []

    def decision_function(observation, now_s, threshold_s, age_limit_s):
        record = decide_with_estimator(
            observation, now_s, threshold_s, age_limit_s, method=method
        )
        records.append(record)
        return record.decision

    result = replay(
        observations, decision_times_s, warning_threshold_s, max_age_s,
        scenario_id=scenario_id,
        horizon_s=horizon_s,
        decision_function=decision_function,
    )
    return EstimatedReplayResult(result, records)
```

There is one replay queue, one source-gating helper and one TTC helper. The C1 layer selects the state estimator and records evidence. Because it does not first execute raw TTC before computing the alternative, a failure in raw arithmetic cannot silently prevent the alternative calculation. A failed case must still be accounted for by the later paired runner; this block propagates errors rather than inventing successful records.

For an eligible projected row at4s, `record.source.gap_m` remains25, while `record.estimate.gap_m` and `record.decision.gap_m` are10. All timestamps and source age remain unchanged. For stale rows, source information remains present but `estimate is None`; for unavailable rows both source and estimate are absent.

## 4. Create `test_c1_replay.py`

The tests reuse the actual diagnostic only as development/regression evidence. They do not call it held out. No persistent report, extra dependency or new fault mechanism is needed.

```python
"""Shared-policy compatibility, causal boundaries and projected-state checks."""

from dataclasses import replace
import unittest

from c1_replay import replay_with_estimator
from evaluation import aligned_errors, score_case
from m3_regression import run_latency_case
from observations import Observation
from replay import replay
from warning_policy import Decision, decide, prepare_decision, ttc_from_state


def play(readings, times, horizon, *, method="age_projection", max_age_s=3.0):
    return replay_with_estimator(
        readings, times, warning_threshold_s=2.0, max_age_s=max_age_s,
        scenario_id="fixture", horizon_s=horizon, method=method,
    )


def replay_data(data, method):
    return replay_with_estimator(
        data["observations"], data["decision_times_s"],
        warning_threshold_s=data["policy"]["warning_threshold_s"],
        max_age_s=data["policy"]["max_age_s"],
        scenario_id=data["scenario"].scenario_id,
        horizon_s=data["scenario"].horizon_s, method=method,
    )


class SharedPolicyTests(unittest.TestCase):
    def test_literal_ttc_branches(self):
        cases = [
            (10.0, 5.0, (2.0, True, "ttc_warning")),
            (10.5, 5.0, (2.1, False, "ttc_clear")),
            (0.0, -2.0, (0.0, True, "contact_or_overlap")),
            (-1.0, -2.0, (0.0, True, "contact_or_overlap")),
            (10.0, 0.0, (None, False, "not_closing")),
            (10.0, -2.0, (None, False, "not_closing")),
        ]
        for gap, closing, expected in cases:
            with self.subTest(gap=gap, closing=closing):
                self.assertEqual(ttc_from_state(gap, closing, 2.0), expected)

    def test_raw_literal_and_common_source_gates(self):
        source = Observation("fixture", 1, 1.0, 3.5, 25.0, 5.0)
        expected = Decision(
            decision_time_s=4.0, sample_id=1, measurement_time_s=1.0,
            arrival_time_s=3.5, observation_age_s=3.0, gap_m=25.0,
            closing_speed_mps=5.0, ttc_s=5.0, is_warning=False,
            reason="ttc_clear",
        )
        self.assertEqual(decide(source, 4.0, 2.0, 3.0), expected)
        self.assertEqual(prepare_decision(source, 4.0, 2.0, 3.0).reason, "pending")
        self.assertEqual(prepare_decision(source, 4.0001, 2.0, 3.0).reason, "stale")
        self.assertEqual(prepare_decision(None, 0.0).reason, "unavailable")
        with self.assertRaises(ValueError):
            prepare_decision(source, 3.4, 2.0, 3.0)

    def test_invalid_state_and_ttc_overflow(self):
        for values in (
            (float("nan"), 1.0, 2.0), (1.0, float("inf"), 2.0),
            (1.0, 1.0, 0.0), (1e308, 1e-308, 2.0),
        ):
            with self.subTest(values=values):
                with self.assertRaises(ValueError):
                    ttc_from_state(*values)


class CausalEstimateTests(unittest.TestCase):
    def test_raw_matches_all_existing_diagnostic_decisions(self):
        for delay, first in ((0, 4.0), (1, 5.0), (1.5, 5.5), (2, 6.0), (2.5, None)):
            with self.subTest(delay=delay):
                data = run_latency_case(delay)
                result = replay_data(data, "raw")
                self.assertEqual(result.replay, data["replay"])
                self.assertEqual(data["score"]["first_warning_time_s"], first)
                self.assertEqual(len(result.records), len(result.replay.decisions))
                for record, decision in zip(result.records, result.replay.decisions):
                    self.assertIs(record.decision, decision)

    def test_projected_diagnostic_preserves_sources_and_aligned_errors(self):
        data = run_latency_case(2.5)
        result = replay_data(data, "age_projection")
        score = score_case(
            result.replay.decisions, reference_contact_time_s=6.0,
            horizon_s=6.0, pre_event_window_s=3.0, minimum_useful_lead_s=1.0,
        )
        self.assertEqual(score["first_warning_time_s"], 4.0)
        self.assertEqual(score["matched_lead_s"], 2.0)
        self.assertEqual(score["outcome"], "useful")
        self.assertEqual(result.replay.beyond_horizon_arrival_count, 3)
        self.assertEqual(result.replay.ignored_older_arrival_count, 0)
        record = next(r for r in result.records if r.decision.decision_time_s == 4.0)
        self.assertEqual(record.source.gap_m, 25.0)
        self.assertEqual(record.source.measurement_time_s, 1.0)
        self.assertEqual(record.source.arrival_time_s, 3.5)
        self.assertEqual(record.decision.observation_age_s, 3.0)
        self.assertEqual(record.estimate.gap_m, 10.0)
        self.assertEqual(record.decision.gap_m, 10.0)
        raw_errors = aligned_errors(data["replay"].decisions, data["scenario"])
        errors = aligned_errors(result.replay.decisions, data["scenario"])
        self.assertEqual(raw_errors["gap_mae_m"], 13.75)
        self.assertEqual(errors["gap_mae_m"], 0.0)
        self.assertEqual(errors["closing_speed_mae_mps"], 0.0)
        self.assertEqual(errors["fresh_count"], 8)
        self.assertEqual(errors["unavailable_count"], 5)

    def test_age_boundary_and_stale_overflow_are_shared(self):
        source = Observation("fixture", 0, 0.0, 1.25, 10.0, 4.0)
        for method in ("raw", "age_projection"):
            result = play(
                [source], [0.0, 1.25, 1.2501], 1.2501,
                method=method, max_age_s=1.25,
            )
            self.assertIsNotNone(result.records[1].estimate)
            self.assertEqual(result.records[-1].decision.reason, "stale")
            self.assertIsNone(result.records[-1].estimate)
            self.assertFalse(result.records[-1].decision.is_warning)
            if method == "age_projection":
                self.assertEqual(result.records[1].estimate.gap_m, 5.0)
                self.assertEqual(result.records[1].decision.ttc_s, 1.25)
            huge = Observation("fixture", 0, 0.0, 2.0, 1e308, 1e308)
            stale = play([huge], [0.0, 2.0], 2.0, method=method, max_age_s=1.25)
            self.assertEqual(stale.records[-1].decision.reason, "stale")
            self.assertIsNone(stale.records[-1].estimate)

    def test_signed_estimates_use_the_same_policy_branches(self):
        cases = (
            (2.0, 5.0, -3.0, 0.0, True, "contact_or_overlap"),
            (-1.0, -2.0, 1.0, None, False, "not_closing"),
            (10.0, 0.0, 10.0, None, False, "not_closing"),
        )
        for gap, closing, used_gap, ttc, warning, reason in cases:
            with self.subTest(gap=gap, closing=closing):
                source = Observation("fixture", 0, 0.0, 1.0, gap, closing)
                decision = play([source], [0.0, 1.0], 1.0).replay.decisions[-1]
                self.assertEqual(decision.gap_m, used_gap)
                self.assertEqual(decision.ttc_s, ttc)
                self.assertEqual(decision.is_warning, warning)
                self.assertEqual(decision.reason, reason)
                if gap < 0:
                    self.assertTrue(decide(source, 1.0, 2.0, 3.0).is_warning)

    def test_arrival_boundary_is_not_brought_forward(self):
        source = Observation("fixture", 0, 0.0, 1.2, 10.0, 4.0)
        result = play([source], [0.0, 1.1, 1.2], 1.2)
        self.assertEqual([r.decision.reason for r in result.records[:2]],
                         ["unavailable", "unavailable"])
        self.assertIsNone(result.records[1].source)
        self.assertIs(result.records[-1].source, source)

    def test_old_and_simultaneous_arrival_selection_is_unchanged(self):
        older = Observation("fixture", 0, 1.0, 3.0, 15.0, 5.0)
        newer = Observation("fixture", 1, 2.0, 2.5, 10.0, 5.0)
        result = play([older, newer], [0.0, 2.5, 3.0], 3.0)
        self.assertEqual([d.sample_id for d in result.replay.decisions], [None, 1, 1])
        self.assertEqual(result.replay.ignored_older_arrival_count, 1)
        self.assertIs(result.records[-1].source, newer)
        same_time_old = Observation("fixture", 0, 0.0, 2.0, 50.0, 5.0)
        same_time_new = Observation("fixture", 1, 1.0, 2.0, 10.0, 5.0)
        simultaneous = play([same_time_new, same_time_old], [0.0, 2.0], 2.0)
        self.assertIs(simultaneous.records[-1].source, same_time_new)
        self.assertEqual(simultaneous.replay.decisions[-1].gap_m, 5.0)

    def test_future_values_do_not_change_the_decision_prefix(self):
        first = Observation("fixture", 0, 0.0, 0.0, 20.0, 5.0)
        future = Observation("fixture", 1, 1.0, 2.0, 10.0, 5.0)
        changed = replace(future, gap_m=-999.0)
        a = play([first, future], [0.0, 1.0, 2.0, 3.0], 3.0)
        b = play([first, changed], [0.0, 1.0, 2.0, 3.0], 3.0)
        self.assertEqual(a.replay.decisions[:2], b.replay.decisions[:2])
        self.assertNotEqual(a.replay.decisions[2], b.replay.decisions[2])

    def test_single_pass_iterables_preserve_the_original_source(self):
        source = Observation("fixture", 0, 0.0, 0.0, 20.0, 5.0)
        result = play((r for r in [source]), (t for t in [0.0, 1.0]), 1.0)
        self.assertIs(result.records[-1].source, source)
        self.assertEqual(source.gap_m, 20.0)
        self.assertEqual(result.records[-1].decision.gap_m, 15.0)

    def test_empty_stream_and_unknown_method(self):
        result = play([], [0.0], 0.0)
        self.assertEqual(result.replay.decisions[0].reason, "unavailable")
        self.assertIsNone(result.records[0].source)
        self.assertIsNone(result.records[0].estimate)
        with self.assertRaises(ValueError):
            play([], [0.0], 0.0, method="projectoin")

    def test_original_clock_and_duplicate_validation_still_applies(self):
        with self.assertRaises(ValueError):
            play([], [0.0, 0.0], 1.0)
        source = Observation("fixture", 0, 0.0, 0.0, 20.0, 5.0)
        with self.assertRaises(ValueError):
            play([source, source], [0.0, 1.0], 1.0)

    def test_invalid_callbacks_fail_explicitly(self):
        for callback in (7, lambda *args: None, lambda *args: Decision(1.0)):
            with self.subTest(callback=callback):
                with self.assertRaises(ValueError):
                    replay([], [0.0], scenario_id="fixture", horizon_s=0.0,
                           decision_function=callback)


if __name__ == "__main__":
    unittest.main()
```

### What these checks establish

The raw path must match every existing diagnostic decision and its legacy timing. In the strongest projection fixture, 8 fresh rows occur at2.5,3,3.5,4,4.5,5,5.5,6s;5 earlier rows are unavailable. Ages alternate2.5/3s, so raw gap errors alternate12.5/15m and average13.75m. Projection is exact under the fixture's constant closing speed, giving zero gap error on the same8 rows. This is development evidence with an intentionally matching motion model, not generalization or proof of a better warning system.

The signed-state test deliberately allows measured overlap with opening motion to project to positive gap: raw warns, projection clears. Do not hide this possible loss with a special raw-contact override. Whether the estimate is right is determined only by independent truth during offline evaluation. The causal-prefix test changes values before they have arrived and requires the earlier decision prefix to stay identical; it uses one unchanged valid horizon for both streams.

## 5. Run the whole block

Learner-run instructions, not observed executions:

```powershell
Set-Location 'E:\DriveCheck'
git branch --show-current
.\.venv\Scripts\python.exe -m unittest -v test_c1_estimators test_c1_replay
.\.venv\Scripts\python.exe -m unittest discover -v
```

Expected current branch: `feature/c1-fair-comparison`. The proposed new module has14 test methods. With unchanged accepted Block1/184 tests, expect29 combined C1 tests and198 total. Counts remain expectations until actual saving/runs/review. No new package is needed. Do not edit `evaluation.py`, M3 diagnostic settings, M4 configuration, CLI/report/export schemas or the reproduction inventory in this block.

If baseline decisions change, inspect helper extraction and default callback first. If stale projection raises overflow, the gate is in the wrong place. If errors stay at13.75m after projected decisions show10m at4s, check which decision list reached `aligned_errors`. If source age becomes zero, a timestamp was rewritten. If `pending` reaches evaluation, a prepared decision was emitted without applying TTC. Keep all old reason strings and use the same fixed diagnostic policy in its literal tests.

Meaningful attempt: explain the one decision at4s using the source, arrival, age, estimated gap, TTC and independent event. Explain why a reading arriving6.5s still cannot influence a6s decision even when projection is enabled. No extra quiz reply is required before working through the full block.

After saving/running, request review. Then save the reviewed selective checkpoint before the next substantial block. Expected implementation paths are `warning_policy.py`, `replay.py`, `c1_replay.py`, `test_c1_replay.py`; the exact reviewed documentation paths will be supplied at acceptance. No automatic commit/push/merge is authorized by this lesson. Block3 will freeze actual paired inputs and development/evaluation separation; do not tune from those future evaluation cases now.

**Checkpoint:** Block2 supplied, not implemented or verified by the assistant. C1 remains1/5 technically verified,184 previously passing tests. A fixed-delay regression improvement here, if observed, will be development evidence only. Full matrix wins/losses/unchanged results and independent learner explanation remain pending.
