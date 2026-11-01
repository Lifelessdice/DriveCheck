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
