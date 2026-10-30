"""Independent observation fixtures and invalid-input contract checks."""

import unittest
from dataclasses import replace

from motion import sample_truth
from observations import (
    Observation,
    make_observations,
    validate_observations,
)
from scenarios import m1_fixtures


class ObservationTests(unittest.TestCase):
    """Check clean values, delivery delays and separation from source truth."""

    def setUp(self):
        """Use the existing braking fixture with a five-second horizon."""
        fixture = next(
            fixture
            for fixture in m1_fixtures()
            if fixture.scenario.scenario_id == "lead_braking_contact"
        )

        self.scenario = fixture.scenario
        self.truth = sample_truth(self.scenario)

    def test_clean_observations_match_known_truth_values(self):
        """Zero delay retains independently calculated M1 times and values."""
        readings = make_observations(self.truth)

        # At 2 s: lead rear 57.5 m minus ego front 40 m gives 17.5 m.
        # Later negative gaps are virtual overlap, not simulated impact motion.
        expected_times = [0, 1, 2, 3, 4, 5]
        expected_gaps = [30, 25, 17.5, 5, -12.5, -32.5]
        expected_closing_speeds = [5, 5, 10, 15, 20, 20]

        self.assertEqual(
            [reading.sample_id for reading in readings],
            [0, 1, 2, 3, 4, 5],
        )
        self.assertEqual(
            [reading.measurement_time_s for reading in readings],
            expected_times,
        )
        self.assertEqual(
            [reading.arrival_time_s for reading in readings],
            expected_times,
        )
        self.assertEqual(
            [reading.gap_m for reading in readings],
            expected_gaps,
        )
        self.assertEqual(
            [reading.closing_speed_mps for reading in readings],
            expected_closing_speeds,
        )

    def test_latency_changes_delivery_without_changing_truth(self):
        """The 2 s measurement arrives at 3/2.5 s with unchanged values."""
        before = list(self.truth)

        for delay_s, expected_arrival_s in ((1.0, 3.0), (0.5, 2.5)):
            with self.subTest(delay_s=delay_s):
                readings = make_observations(self.truth, delay_s)
                reading = readings[2]

                self.assertEqual(reading.measurement_time_s, 2.0)
                self.assertEqual(reading.arrival_time_s, expected_arrival_s)
                self.assertEqual(reading.gap_m, 17.5)
                self.assertEqual(reading.closing_speed_mps, 10.0)

                self.assertIsNot(readings, self.truth)
                self.assertIsNot(reading, self.truth[2])
                self.assertEqual(self.truth, before)

    def test_empty_stream_is_allowed(self):
        """No readings is a valid stream, distinct from a zero-gap reading."""
        self.assertEqual(make_observations([], 1.0), [])

        validate_observations(
            [],
            scenario_id=self.scenario.scenario_id,
            horizon_s=self.scenario.horizon_s,
        )

    def test_signed_gap_and_closing_speed_are_allowed(self):
        """Overlap and vehicles moving apart remain valid signed inputs."""
        reading = Observation(
            scenario_id="fixture",
            sample_id=0,
            measurement_time_s=0,
            arrival_time_s=0,
            gap_m=-1,
            closing_speed_mps=-2,
        )

        self.assertEqual(reading.gap_m, -1)
        self.assertEqual(reading.closing_speed_mps, -2)

    def test_unordered_storage_and_missing_ids_are_allowed(self):
        """Stream validation neither renumbers missing samples nor sorts them."""
        readings = make_observations(self.truth, 1.0)
        subset = [readings[3], readings[0]]

        validate_observations(
            subset,
            self.scenario.scenario_id,
            self.scenario.horizon_s,
        )

        # Validation preserves storage order and source IDs.
        self.assertEqual(
            [reading.sample_id for reading in subset],
            [3, 0],
        )

    def test_invalid_latency_is_rejected_even_for_empty_input(self):
        """Empty input must not bypass the delay's type/range checks."""
        for invalid in (-1, True, "1", float("nan"), float("inf")):
            with self.subTest(latency_s=invalid):
                with self.assertRaises(ValueError):
                    make_observations([], invalid)

    def test_invalid_observation_fields_are_rejected(self):
        """Record reconstruction reruns validation of changed fields."""
        valid = Observation("fixture", 0, 1.0, 1.0, 10.0, 5.0)

        invalid_changes = [
            {"scenario_id": ""},
            {"scenario_id": 7},
            {"sample_id": -1},
            {"sample_id": True},
            {"sample_id": 0.0},
            {"measurement_time_s": -1},
            {"measurement_time_s": float("nan")},
            {"arrival_time_s": float("inf")},
            {"arrival_time_s": 0.5},
            {"gap_m": "10"},
            {"closing_speed_mps": True},
        ]

        # replace creates a new frozen record and invokes __post_init__ again.
        for changes in invalid_changes:
            with self.subTest(changes=changes):
                with self.assertRaises(ValueError):
                    replace(valid, **changes)

    def test_duplicate_ids_or_measurement_times_are_rejected(self):
        """ID uniqueness and measurement-time uniqueness are separate rules."""
        first = Observation("fixture", 0, 0.0, 0.0, 30.0, 5.0)

        same_id = replace(
            first,
            measurement_time_s=1.0,
            arrival_time_s=1.0,
        )
        same_time = replace(first, sample_id=1)

        for duplicate in (same_id, same_time):
            with self.subTest(duplicate=duplicate):
                with self.assertRaises(ValueError):
                    validate_observations(
                        [first, duplicate],
                        "fixture",
                        2.0,
                    )

    def test_stream_context_and_horizon_boundaries(self):
        """The measurement horizon is inclusive and differs from delivery."""
        reading = Observation("fixture", 0, 4.0, 5.0, 10.0, 5.0)

        # Measurement at H is valid even when delivery occurs after H.
        validate_observations([reading], "fixture", 4.0)

        with self.assertRaises(ValueError):
            validate_observations([reading], "other_scenario", 4.0)

        with self.assertRaises(ValueError):
            validate_observations(
                [replace(reading, measurement_time_s=4.1)],
                "fixture",
                4.0,
            )

        for invalid_horizon in (-1, True, float("nan")):
            with self.subTest(horizon_s=invalid_horizon):
                with self.assertRaises(ValueError):
                    validate_observations([], "fixture", invalid_horizon)

        with self.assertRaises(ValueError):
            validate_observations([], "", 4.0)

        with self.assertRaises(ValueError):
            validate_observations([{}], "fixture", 4.0)

    def test_generator_rejects_invalid_or_mixed_source_samples(self):
        """Generated streams must have valid source types and unique metadata."""
        invalid_streams = [
            [42],
            [self.truth[0], self.truth[0]],
            [
                self.truth[0],
                replace(self.truth[1], scenario_id="other_scenario"),
            ],
            [
                self.truth[0],
                replace(self.truth[1], time_s=0.0),
            ],
        ]

        for samples in invalid_streams:
            with self.subTest(samples=samples):
                with self.assertRaises(ValueError):
                    make_observations(samples)


if __name__ == "__main__":
    unittest.main()
