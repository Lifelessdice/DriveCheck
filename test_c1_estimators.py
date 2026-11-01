"""Independent arithmetic, source provenance and availability checks."""

import unittest

from c1_estimators import estimate_state
from observations import Observation


def reading(gap=25.0, closing=5.0, measured=1.0, arrived=2.0):
    return Observation("c1_fixture", 1, measured, arrived, gap, closing)


class TestStateEstimates(unittest.TestCase):
    def test_raw_holds_original_values_and_source(self):
        source = reading()
        result = estimate_state(source, 3.0)

        self.assertIs(result.source, source)
        self.assertEqual(result.gap_m, 25.0)
        self.assertEqual(result.closing_speed_mps, 5.0)
        self.assertEqual(result.observation_age_s, 2.0)

    def test_existing_diagnostic_hand_prediction(self):
        source = reading(arrived=3.5)
        result = estimate_state(source, 4.0, "age_projection")

        self.assertEqual(result.gap_m, 10.0)
        self.assertEqual(result.observation_age_s, 3.0)
        self.assertEqual(result.source.measurement_time_s, 1.0)
        self.assertEqual(result.source.arrival_time_s, 3.5)
        self.assertEqual(source.gap_m, 25.0)

    def test_fractional_age(self):
        source = reading(gap=18.0, closing=4.0, measured=1.25)
        result = estimate_state(source, 2.0, "age_projection")

        self.assertEqual(result.observation_age_s, 0.75)
        self.assertEqual(result.gap_m, 15.0)

    def test_zero_age_matches_raw(self):
        source = reading(measured=2.0)

        self.assertEqual(
            estimate_state(source, 2.0, "raw"),
            estimate_state(source, 2.0, "age_projection"),
        )

    def test_opening_motion_increases_projected_gap(self):
        source = reading(gap=18.0, closing=-2.0, measured=1.25)

        self.assertEqual(
            estimate_state(source, 2.0, "age_projection").gap_m,
            19.5,
        )

    def test_zero_closing_speed_keeps_gap(self):
        source = reading(gap=18.0, closing=0.0)

        self.assertEqual(
            estimate_state(source, 3.0, "age_projection").gap_m,
            18.0,
        )

    def test_projected_overlap_remains_signed(self):
        source = reading(gap=10.0, measured=0.0, arrived=3.0)

        self.assertEqual(
            estimate_state(source, 3.0, "age_projection").gap_m,
            -5.0,
        )

    def test_repeated_calls_do_not_project_previous_estimate(self):
        source = reading(gap=18.0, closing=4.0, measured=1.25)

        first = estimate_state(source, 2.0, "age_projection")
        second = estimate_state(source, 2.0, "age_projection")

        self.assertEqual(first, second)
        self.assertEqual(second.gap_m, 15.0)
        self.assertEqual(source.gap_m, 18.0)

    def test_no_reading_produces_no_estimate(self):
        for method in ("raw", "age_projection"):
            with self.subTest(method=method):
                self.assertIsNone(estimate_state(None, 0.0, method))

    def test_future_arrival_is_unavailable(self):
        for method in ("raw", "age_projection"):
            with self.subTest(method=method):
                with self.assertRaises(ValueError):
                    estimate_state(reading(), 1.5, method)

    def test_invalid_decision_time_is_rejected(self):
        for now_s in (-1.0, float("nan"), float("inf"), True):
            with self.subTest(now_s=now_s):
                with self.assertRaises(ValueError):
                    estimate_state(None, now_s)

    def test_unknown_method_is_rejected_even_without_data(self):
        with self.assertRaises(ValueError):
            estimate_state(None, 0.0, "projectoin")

    def test_wrong_source_type_is_rejected(self):
        with self.assertRaises(ValueError):
            estimate_state({"gap_m": 25.0}, 2.0)

    def test_projection_overflow_is_rejected(self):
        source = reading(
            gap=1e308,
            closing=1e308,
            measured=0.0,
        )

        with self.assertRaises(ValueError):
            estimate_state(source, 2.0, "age_projection")

    def test_changing_speed_can_make_projection_worse(self):
        source = reading(gap=15.0, measured=0.0)

        raw = estimate_state(source, 2.0, "raw")
        alternative = estimate_state(source, 2.0, "age_projection")

        # Closing speed falls 5 -> 0 over 1 s: only 2.5 m is gained.
        independently_checked_current_gap_m = 12.5

        self.assertEqual(raw.gap_m, 15.0)
        self.assertEqual(alternative.gap_m, 5.0)

        self.assertEqual(
            abs(raw.gap_m - independently_checked_current_gap_m),
            2.5,
        )
        self.assertEqual(
            abs(alternative.gap_m - independently_checked_current_gap_m),
            7.5,
        )


if __name__ == "__main__":
    unittest.main()