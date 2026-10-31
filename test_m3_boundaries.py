"""Precise causal, scoring and offline error-alignment fixtures."""

from dataclasses import replace
import math
import unittest

from evaluation import aligned_errors, score_case, summarize
from faults import FaultConfig, apply_draws, inject_faults
from motion import Scenario, sample_truth, truth_at
from observations import Observation
from replay import replay
from stop_and_go import StopGoScenario, stop_go_truth_at
from warning_policy import Decision, decide


def warning_rows(times):
    """Construct independent scoring inputs without invoking TTC."""
    return [
        Decision(
            decision_time_s=time_s,
            is_warning=True,
            reason="scoring_fixture",
        )
        for time_s in times
    ]


def scored_case(case_id, reference, warning_times):
    """Package a complete literal metric fixture for summary checks."""
    return {
        "case_id": case_id,
        "condition_id": "metric_fixture",
        "status": "complete",
        "reference_contact_time_s": reference,
        "horizon_s": 12.0,
        "score": score_case(
            warning_rows(warning_times),
            reference,
            12.0,
            pre_event_window_s=4.0,
            minimum_useful_lead_s=1.0,
        ),
    }


class BoundaryTests(unittest.TestCase):
    """Check information boundaries separately from warning performance."""

    def run_stream(self, readings, times, *, max_age_s=3.0):
        return replay(
            readings,
            times,
            max_age_s=max_age_s,
            scenario_id=readings[0].scenario_id,
            horizon_s=times[-1],
        )

    def test_adjacent_arrival_boundary(self):
        reading = Observation("edge", 7, 0.0, 1.0, 10.0, 5.0)
        before = math.nextafter(1.0, -math.inf)
        after = math.nextafter(1.0, math.inf)

        result = self.run_stream(
            [reading],
            [0.0, before, 1.0, after, 2.0],
        )

        self.assertEqual(result.decisions[1].reason, "unavailable")
        self.assertEqual(result.decisions[2].sample_id, 7)
        self.assertEqual(result.decisions[3].sample_id, 7)
        self.assertEqual(result.decisions[2].arrival_time_s, 1.0)

    def test_age_boundary_precedes_contact_branch(self):
        reading = Observation("edge", 0, 0.0, 0.0, 0.0, 0.0)
        after_limit = math.nextafter(0.5, math.inf)

        result = self.run_stream(
            [reading],
            [0.0, 0.5, after_limit, 1.0],
            max_age_s=0.5,
        )

        at_limit = result.decisions[1]
        too_old = result.decisions[2]

        self.assertTrue(at_limit.is_warning)
        self.assertEqual(at_limit.ttc_s, 0.0)

        self.assertEqual(too_old.reason, "stale")
        self.assertFalse(too_old.is_warning)
        self.assertIsNone(too_old.ttc_s)
        self.assertEqual(too_old.gap_m, 0.0)

    def test_old_alarming_arrival_does_not_replace_newer_reading(self):
        older = Observation("edge", 0, 0.0, 1.5, 0.0, 5.0)
        newer = Observation("edge", 1, 1.0, 1.0, 50.0, 5.0)

        result = self.run_stream(
            [newer, older],
            [0.0, 1.0, 1.5, 2.0],
        )

        self.assertEqual(
            [row.sample_id for row in result.decisions],
            [None, 1, 1, 1],
        )
        self.assertEqual(result.ignored_older_arrival_count, 1)
        self.assertTrue(all(not row.is_warning for row in result.decisions))

    def test_age_uses_actual_nonuniform_times(self):
        readings = [
            Observation("edge", 10, 0.0, 0.25, 30.0, 5.0),
            Observation("edge", 20, 0.5, 0.75, 27.5, 5.0),
            Observation("edge", 30, 1.4, 1.75, 23.0, 5.0),
        ]

        result = self.run_stream(
            readings,
            [0.0, 0.25, 0.75, 1.2, 1.75, 2.0],
        )

        self.assertEqual(result.decisions[3].sample_id, 20)
        self.assertAlmostEqual(
            result.decisions[3].observation_age_s,
            0.7,
            delta=1e-12,
        )
        self.assertEqual(result.decisions[-1].sample_id, 30)
        self.assertAlmostEqual(
            result.decisions[-1].observation_age_s,
            0.6,
            delta=1e-12,
        )

    def test_future_values_cannot_change_past_decisions(self):
        scenario = Scenario("future_values", 30.0, 10.0, 5.0, 1.0, 4)
        observations, _ = inject_faults(
            sample_truth(scenario),
            FaultConfig(mode="latency", latency_s=1.0),
        )

        changed = [
            replace(row, gap_m=0.0) if row.sample_id == 2 else row
            for row in observations
        ]
        times = [0.0, 1.0, 2.0, 3.0]

        original = self.run_stream(observations, times)
        modified = self.run_stream(changed, times)

        # ID 2 arrives at 3 s, so all earlier decisions must agree.
        self.assertEqual(
            original.decisions[:-1],
            modified.decisions[:-1],
        )
        self.assertFalse(original.decisions[-1].is_warning)
        self.assertTrue(modified.decisions[-1].is_warning)

    def test_adjacent_metric_window_boundaries(self):
        examples = [
            (math.nextafter(6.0, -math.inf), "missed"),
            (6.0, "useful"),
            (9.0, "useful"),
            (math.nextafter(9.0, math.inf), "late"),
            (10.0, "late"),
            (math.nextafter(10.0, math.inf), "missed"),
        ]

        for time_s, expected in examples:
            with self.subTest(time_s=time_s):
                score = score_case(
                    warning_rows([time_s]),
                    10.0,
                    12.0,
                    pre_event_window_s=4.0,
                    minimum_useful_lead_s=1.0,
                )
                self.assertEqual(score["outcome"], expected)

                if expected == "missed":
                    self.assertIsNone(score["matched_lead_s"])
                else:
                    self.assertEqual(
                        score["first_matched_warning_time_s"],
                        time_s,
                    )

                if time_s == 6.0:
                    self.assertEqual(score["matched_lead_s"], 4.0)
                elif time_s == 9.0:
                    self.assertEqual(score["matched_lead_s"], 1.0)
                elif time_s == 10.0:
                    self.assertEqual(score["matched_lead_s"], 0.0)

    def test_five_episode_denominators(self):
        cases = [
            scored_case("episode_a", 10.0, [5.0, 6.0, 8.0]),
            scored_case("episode_b", 10.0, [9.5]),
            scored_case("episode_c", 10.0, []),
            scored_case("episode_d", None, [2.0, 2.5, 4.0]),
            scored_case("episode_e", None, []),
        ]

        group = summarize(cases)[0]

        self.assertEqual(
            group["scored"],
            {"positive": 3, "negative": 2},
        )
        self.assertEqual(
            group["outcomes"],
            {
                "useful": 1,
                "late": 1,
                "missed": 1,
                "false_warning": 1,
                "clear_negative": 1,
            },
        )
        self.assertEqual(
            group["rates"]["missed"],
            {"numerator": 1, "denominator": 3, "value": 1 / 3},
        )
        self.assertEqual(
            group["rates"]["without_useful_warning"],
            {"numerator": 2, "denominator": 3, "value": 2 / 3},
        )
        self.assertEqual(
            group["rates"]["false_warning_episode"],
            {"numerator": 1, "denominator": 2, "value": 1 / 2},
        )

    def test_absent_subsets_have_null_rates(self):
        positive_only = summarize(
            [
                scored_case("positive_only", 10.0, []),
            ]
        )[0]
        negative_only = summarize(
            [
                scored_case("negative_only", None, []),
            ]
        )[0]

        self.assertIsNone(positive_only["rates"]["false_warning_episode"]["value"])
        self.assertEqual(
            positive_only["rates"]["false_warning_episode"]["denominator"],
            0,
        )
        self.assertIsNone(negative_only["rates"]["missed"]["value"])
        self.assertIsNone(negative_only["rates"]["without_useful_warning"]["value"])

    def test_noise_can_cross_closing_and_contact_boundaries(self):
        source = sample_truth(Scenario("noise_edge", 10.0, 5.0, 4.0, 1.0, 1))[0]
        config = FaultConfig(
            mode="noise",
            gap_sigma_m=1.0,
            closing_sigma_mps=1.0,
        )

        examples = [
            (0.0, -1.0, "not_closing", None, False),
            (0.0, -2.0, "not_closing", None, False),
            (-10.0, -1.0, "contact_or_overlap", 0.0, True),
        ]

        for z_gap, z_closing, reason, ttc, warning in examples:
            with self.subTest(z_gap=z_gap, z_closing=z_closing):
                reading, _ = apply_draws(
                    source,
                    config,
                    z_gap=z_gap,
                    z_closing=z_closing,
                    u_latency=0.5,
                    u_dropout=0.5,
                )
                decision = decide(reading, 0.0)

                self.assertEqual(decision.reason, reason)
                self.assertEqual(decision.ttc_s, ttc)
                self.assertEqual(decision.is_warning, warning)

    def test_measurement_error_differs_from_current_time_error(self):
        scenario = Scenario("alignment", 30.0, 10.0, 5.0, 1.0, 7)
        observations, _ = inject_faults(
            sample_truth(scenario),
            FaultConfig(mode="latency", latency_s=2.0),
        )
        reading = observations[2]

        decision = decide(
            reading,
            4.0,
            warning_threshold_s=2.0,
            max_age_s=3.0,
        )
        errors = aligned_errors([decision], scenario)

        self.assertEqual(reading.measurement_time_s, 2.0)
        self.assertEqual(reading.gap_m, 20.0)
        self.assertEqual(
            reading.gap_m - truth_at(scenario, 2.0).gap_m,
            0.0,
        )
        self.assertEqual(errors["gap_mae_m"], 10.0)
        self.assertEqual(errors["closing_speed_mae_mps"], 0.0)
        self.assertEqual(errors["fresh_count"], 1)

    def test_stop_go_callback_errors_and_missing_coverage(self):
        scenario = StopGoScenario("error_alignment", 18.0)
        rows = [
            Decision(
                0.0,
                gap_m=16.0,
                closing_speed_mps=0.0,
                reason="not_closing",
            ),
            Decision(1.0),
            Decision(
                2.0,
                gap_m=14.0,
                closing_speed_mps=4.0,
                reason="ttc_clear",
            ),
            Decision(
                3.0,
                gap_m=999.0,
                closing_speed_mps=999.0,
                reason="stale",
            ),
            Decision(
                4.0,
                gap_m=8.0,
                closing_speed_mps=4.0,
                is_warning=True,
                ttc_s=2.0,
                reason="ttc_warning",
            ),
        ]

        # True gaps at 0/2/4 are 18/14/6 m.
        # Signed residuals -2/0/+2 give absolute errors 2/0/2.
        errors = aligned_errors(
            rows,
            scenario,
            truth_at_time=lambda time_s: stop_go_truth_at(scenario, time_s),
        )

        self.assertAlmostEqual(
            errors["gap_mae_m"],
            4 / 3,
            delta=1e-12,
        )
        self.assertEqual(errors["closing_speed_mae_mps"], 0.0)
        self.assertEqual(errors["fresh_count"], 3)
        self.assertEqual(errors["unavailable_count"], 1)
        self.assertEqual(errors["stale_count"], 1)

        def forbidden_callback(time_s):
            raise AssertionError("excluded rows must not evaluate truth")

        missing = aligned_errors(
            [Decision(0.0), Decision(1.0, reason="stale")],
            scenario,
            truth_at_time=forbidden_callback,
        )
        self.assertEqual(missing["fresh_count"], 0)
        self.assertIsNone(missing["gap_mae_m"])
        self.assertIsNone(missing["closing_speed_mae_mps"])

        with self.assertRaises(ValueError):
            aligned_errors([], scenario, truth_at_time=42)


if __name__ == "__main__":
    unittest.main()
