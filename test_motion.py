# Fixed expected values keep assertions independent of the model calculation.
import unittest

from motion import (
    Scenario,
    gap_after_seconds,
    sample_constant_speed,
    sample_truth,
    truth_at,
)


class TestGapAfterSeconds(unittest.TestCase):
    def test_gap_after_seconds(self):
        # At 2 s: 30 m initial gap + 30 m lead travel - 40 m ego travel = 20 m.
        expected_gap_m = 20

        actual_gap_m = gap_after_seconds(30.0, 20.0, 15.0, 2.0)
        self.assertEqual(expected_gap_m, actual_gap_m)


class SamplingTests(unittest.TestCase):
    def test_original_five_rows(self):
        # Check sample identity, time spacing and gap values separately.
        rows = sample_constant_speed(30, 20, 15, 1, 5)

        self.assertEqual(
            [row["sample_id"] for row in rows],
            [0, 1, 2, 3, 4],
        )

        self.assertEqual(
            [row["time_s"] for row in rows],
            [0, 1, 2, 3, 4],
        )

        self.assertEqual(
            [row["gap_m"] for row in rows],
            [30, 25, 20, 15, 10],
        )

    def test_half_second_steps(self):
        # Five rows contain four half-second intervals: a 2 s horizon.
        rows = sample_constant_speed(30, 20, 15, 0.5, 5)

        self.assertEqual(
            [row["time_s"] for row in rows],
            [0, 0.5, 1, 1.5, 2],
        )

        self.assertEqual(
            [row["gap_m"] for row in rows],
            [30, 27.5, 25, 22.5, 20.0],
        )

    def test_one_sample_reconrds_initial_state(self):
        # A single sample represents t=0 with no elapsed time interval.
        rows = sample_constant_speed(30, 20, 15, 1, 1)

        self.assertEqual(
            rows,
            [{"sample_id": 0, "time_s": 0, "gap_m": 30}],
        )

    def test_invalid_sampling_settings(self):
        invalid_settings = [
            (0, 5),
            (-1, 5),
            (float("nan"), 5),
            (1, 0),
            (1, 2.5),
            (1, True),
        ]

        for step, count in invalid_settings:
            with self.subTest(step=step, count=count):
                with self.assertRaises(ValueError):
                    sample_constant_speed(30, 20, 15, step, count)

    def test_half_second_steps_preserve_four_second_horizon(self):
        # Nine rows contain eight half-second intervals: a 4 s horizon.
        rows = sample_constant_speed(
            initial_gap_m=30,
            ego_speed_mps=20,
            lead_speed_mps=15,
            timestep_s=0.5,
            sample_count=9,
        )

        self.assertEqual(len(rows), 9)
        self.assertEqual(rows[-1]["time_s"], 4.0)
        self.assertEqual(rows[-1]["gap_m"], 10.0)


class ScenarioTests(unittest.TestCase):
    def test_half_second_horizon(self):
        # The horizon is derived from configuration without generating a trajectory.
        scenario = Scenario(
            scenario_id="original",
            initial_gap_m=30,
            ego_speed_mps=20,
            lead_speed_mps=15,
            timestep_s=0.5,
            sample_count=9,
        )

        self.assertEqual(scenario.horizon_s, 4.0)
        self.assertIsNone(scenario.stop_time_s)

    def test_stop_time(self):
        # Braking lasts 15 / 5 = 3 s; the 1 s start delay gives a 4 s stop time.
        scenario = Scenario(
            scenario_id="braking",
            initial_gap_m=30,
            ego_speed_mps=20,
            lead_speed_mps=15,
            timestep_s=1,
            sample_count=6,
            brake_start_s=1,
            lead_deceleration_mps2=5,
        )

        self.assertEqual(scenario.horizon_s, 5.0)
        self.assertEqual(scenario.stop_time_s, 4.0)

    def test_boolean_sample_count_rejected(self):
        with self.assertRaises(ValueError):
            Scenario(
                scenario_id="invalid",
                initial_gap_m=30,
                ego_speed_mps=20,
                lead_speed_mps=15,
                timestep_s=1,
                sample_count=True,
            )


class BrakingTests(unittest.TestCase):
    def test_known_braking_values(self):
        scenario = Scenario("braking", 30, 20, 15, 1, 6, 1, 5)

        rows = sample_truth(scenario)

        self.assertEqual(
            [row.gap_m for row in rows],
            [30, 25, 17.5, 5, -12.5, -32.5],
        )

        self.assertEqual(
            [row.lead_speed_mps for row in rows],
            [15, 15, 10, 5, 0, 0],
        )

    def test_lead_stays_stopped(self):
        scenario = Scenario("braking", 30, 20, 15, 1, 6, 1, 5)

        for elapsed_s in [4, 5, 20]:
            with self.subTest(elapsed_s=elapsed_s):
                row = truth_at(scenario, elapsed_s)

                self.assertEqual(row.lead_rear_x_m, 67.5)
                self.assertEqual(row.lead_speed_mps, 0.0)

    def test_without_braking_matches_original_example(self):
        scenario = Scenario("constant", 30, 20, 15, 1, 5)

        rows = sample_truth(scenario)

        self.assertEqual(
            [row.gap_m for row in rows],
            [30, 25, 20, 15, 10],
        )

        self.assertEqual(rows[2].ego_front_x_m, 40.0)
        self.assertEqual(rows[2].lead_rear_x_m, 60.0)
        self.assertEqual(rows[2].closing_speed_mps, 5.0)

    def test_half_second_braking_sample(self):
        scenario = Scenario("braking", 30, 20, 15, 0.5, 11, 1, 5)

        rows = sample_truth(scenario)
        row = rows[5]

        self.assertEqual(row.time_s, 2.5)
        self.assertEqual(row.lead_rear_x_m, 61.875)
        self.assertEqual(row.gap_m, 11.875)
        self.assertEqual(row.lead_speed_mps, 7.5)
