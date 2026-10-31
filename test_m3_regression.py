"""Preserve the independently predicted latency-induced warning failure."""

from dataclasses import asdict
import unittest

from m3_regression import run_latency_case
from replay import replay


DELAYS = (0.0, 1.0, 1.5, 2.0, 2.5)


class LatencyRegressionTests(unittest.TestCase):
    """Check the failure mechanism rather than changing expected outcomes."""

    def test_independent_outcomes_and_lead_times(self):
        expected = [
            (0.0, 4.0, 2.0, "useful"),
            (1.0, 5.0, 1.0, "useful"),
            (1.5, 5.5, 0.5, "late"),
            (2.0, 6.0, 0.0, "late"),
            (2.5, None, None, "missed"),
        ]

        for delay, first_warning, lead, outcome in expected:
            with self.subTest(delay_s=delay):
                case = run_latency_case(delay)
                score = case["score"]

                self.assertEqual(
                    score["first_warning_time_s"],
                    first_warning,
                )
                self.assertEqual(score["matched_lead_s"], lead)
                self.assertEqual(score["outcome"], outcome)
                self.assertEqual(
                    score["reference_contact_time_s"],
                    6.0,
                )

    def test_all_arms_preserve_truth_and_sensor_values(self):
        baseline = run_latency_case(0.0)
        expected_truth = [
            asdict(row) for row in baseline["truth"]
        ]

        for delay in DELAYS:
            with self.subTest(delay_s=delay):
                case = run_latency_case(delay)

                self.assertEqual(
                    [asdict(row) for row in case["truth"]],
                    expected_truth,
                )
                self.assertEqual(
                    asdict(case["scenario"]),
                    asdict(baseline["scenario"]),
                )
                self.assertEqual(case["policy"], baseline["policy"])
                self.assertEqual(
                    case["decision_times_s"],
                    baseline["decision_times_s"],
                )

                for observed, clean in zip(
                    case["observations"],
                    baseline["observations"],
                ):
                    self.assertEqual(
                        observed.sample_id,
                        clean.sample_id,
                    )
                    self.assertEqual(
                        observed.measurement_time_s,
                        clean.measurement_time_s,
                    )
                    self.assertEqual(observed.gap_m, clean.gap_m)
                    self.assertEqual(
                        observed.closing_speed_mps,
                        clean.closing_speed_mps,
                    )
                    self.assertEqual(
                        observed.arrival_time_s,
                        clean.measurement_time_s + delay,
                    )

    def test_every_decision_respects_causal_availability(self):
        for delay in DELAYS:
            with self.subTest(delay_s=delay):
                case = run_latency_case(delay)
                observations = case["observations"]

                for decision in case["replay"].decisions:
                    available = [
                        row
                        for row in observations
                        if row.arrival_time_s <= decision.decision_time_s
                    ]

                    if not available:
                        self.assertIsNone(decision.sample_id)
                        self.assertEqual(
                            decision.reason,
                            "unavailable",
                        )
                        continue

                    newest = max(
                        available,
                        key=lambda row: row.measurement_time_s,
                    )
                    self.assertEqual(
                        decision.sample_id,
                        newest.sample_id,
                    )
                    self.assertLessEqual(
                        decision.measurement_time_s,
                        decision.arrival_time_s,
                    )
                    self.assertLessEqual(
                        decision.arrival_time_s,
                        decision.decision_time_s,
                    )
                    self.assertEqual(
                        decision.observation_age_s,
                        decision.decision_time_s
                        - decision.measurement_time_s,
                    )

    def test_strongest_miss_is_pending_data_not_staleness(self):
        case = run_latency_case(2.5)
        final = case["replay"].decisions[-1]
        alarming = case["observations"][4]

        self.assertEqual(final.decision_time_s, 6.0)
        self.assertEqual(final.sample_id, 3)
        self.assertEqual(final.measurement_time_s, 3.0)
        self.assertEqual(final.arrival_time_s, 5.5)
        self.assertEqual(final.observation_age_s, 3.0)
        self.assertEqual(final.gap_m, 15.0)
        self.assertEqual(final.ttc_s, 3.0)
        self.assertEqual(final.reason, "ttc_clear")
        self.assertFalse(final.is_warning)

        self.assertEqual(alarming.measurement_time_s, 4.0)
        self.assertEqual(alarming.arrival_time_s, 6.5)
        self.assertEqual(alarming.gap_m, 10.0)
        self.assertEqual(
            case["replay"].beyond_horizon_arrival_count,
            3,
        )
        self.assertTrue(
            all(not row["dropped"] for row in case["audit"])
        )
        self.assertTrue(
            all(
                row.reason != "stale"
                for row in case["replay"].decisions
            )
        )
        self.assertIsNone(
            case["score"]["first_matched_warning_time_s"]
        )
        self.assertIsNone(case["score"]["matched_lead_s"])

    def test_boundary_latency_trace_rows(self):
        case = run_latency_case(2.0)
        rows = {
            row.decision_time_s: row
            for row in case["replay"].decisions
        }

        before_contact = rows[5.5]
        at_contact = rows[6.0]

        self.assertEqual(before_contact.sample_id, 3)
        self.assertEqual(before_contact.observation_age_s, 2.5)
        self.assertEqual(before_contact.ttc_s, 3.0)
        self.assertFalse(before_contact.is_warning)

        self.assertEqual(at_contact.sample_id, 4)
        self.assertEqual(at_contact.arrival_time_s, 6.0)
        self.assertEqual(at_contact.ttc_s, 2.0)
        self.assertTrue(at_contact.is_warning)
        self.assertEqual(case["score"]["outcome"], "late")
        self.assertEqual(case["score"]["matched_lead_s"], 0.0)

    def test_repeated_runs_are_identical(self):
        for delay in DELAYS:
            with self.subTest(delay_s=delay):
                self.assertEqual(
                    run_latency_case(delay),
                    run_latency_case(delay),
                )

    def test_half_second_delay_prediction(self):
        case = run_latency_case(0.5)

        self.assertEqual(
            case["score"]["first_warning_time_s"],
            4.5,
        )
        self.assertEqual(case["score"]["matched_lead_s"], 1.5)
        self.assertEqual(case["score"]["outcome"], "useful")

    def test_invalid_latency_is_rejected(self):
        for delay in (
            -1.0,
            True,
            False,
            None,
            "1",
            float("nan"),
            float("inf"),
        ):
            with self.subTest(delay=delay):
                with self.assertRaises(ValueError):
                    run_latency_case(delay)

    def test_larger_age_limit_does_not_deliver_future_data(self):
        case = run_latency_case(2.5)

        relaxed_age = replay(
            case["observations"],
            case["decision_times_s"],
            warning_threshold_s=2.0,
            max_age_s=100.0,
            scenario_id=case["scenario"].scenario_id,
            horizon_s=case["scenario"].horizon_s,
        )

        self.assertTrue(
            all(
                not row.is_warning
                for row in relaxed_age.decisions
            )
        )
        self.assertEqual(
            relaxed_age.decisions[-1].sample_id,
            3,
        )
        self.assertEqual(
            relaxed_age.beyond_horizon_arrival_count,
            3,
        )


if __name__ == "__main__":
    unittest.main()
