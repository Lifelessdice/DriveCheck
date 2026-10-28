# Fixed expected values keep assertions independent of the model calculation.
import unittest

from motion import (
    Scenario,
    contact_delay,
    first_contact_time,
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


class ContactTests(unittest.TestCase):
    def test_braking_contact_between_samples(self):
        # Independent bumper-position equations give contact at sqrt(11) seconds.
        scenario = Scenario("contact", 30, 20, 15, 1, 6, 1, 5)

        self.assertAlmostEqual(
            first_contact_time(scenario),
            3.3166247903554,
            places=10,
        )
        self.assertGreater(truth_at(scenario, 3).gap_m, 0)
        self.assertLess(truth_at(scenario, 4).gap_m, 0)

    def test_event_does_not_depend_on_sample_grid(self):
        # All grids represent the same trajectory over a 5 s horizon.
        for step, count in [(1, 6), (0.5, 11), (2.5, 3)]:
            with self.subTest(step=step):
                scenario = Scenario("grid", 30, 20, 15, step, count, 1, 5)
                self.assertAlmostEqual(
                    first_contact_time(scenario),
                    3.3166247903554,
                    places=10,
                )

    def test_contact_in_each_motion_phase(self):
        # Cover contact before, at the start/end of, and after braking.
        cases = [
            ("before", 10, 20, 15, 3, 5, 2.0),
            ("brake_start", 15, 20, 15, 3, 5, 3.0),
            ("stop", 10, 10, 10, 1, 5, 3.0),
            ("after_stop", 20, 10, 10, 1, 5, 4.0),
        ]

        for name, gap, ego, lead, start, decel, expected in cases:
            with self.subTest(case=name):
                scenario = Scenario(name, gap, ego, lead, 1, 6, start, decel)

                self.assertAlmostEqual(
                    first_contact_time(scenario), expected, places=10
                )

    def test_inclusive_horizon(self):
        # A 30 m gap closing at 5 m/s reaches zero at the inclusive 6 s endpoint.
        short = Scenario("short", 30, 20, 15, 1, 6)
        endpoint = Scenario("endpoint", 30, 20, 15, 1, 7)
        longer = Scenario("longer", 30, 20, 15, 1, 8)

        self.assertIsNone(first_contact_time(short))
        self.assertEqual(first_contact_time(endpoint), 6.0)
        self.assertEqual(first_contact_time(longer), 6.0)

    def test_noncontact_depends_on_horizon(self):
        # The lead stops at x=100 m; ego reaches x=80 m at 8 s and x=100 m at 10 s.
        short = Scenario("noncontact", 40, 10, 20, 1, 9, 1, 5)
        extended = Scenario("extended", 40, 10, 20, 1, 11, 1, 5)

        self.assertIsNone(first_contact_time(short))
        self.assertEqual(truth_at(short, 8).gap_m, 20.0)
        self.assertEqual(first_contact_time(extended), 10.0)

    def test_initial_contact_and_zero_horizon(self):
        # Initial contact counts even when no simulation interval has elapsed.
        for gap in [0, -1]:
            with self.subTest(gap=gap):
                scenario = Scenario("initial_contact", gap, 0, 15, 1, 1, 1, 5)
                self.assertEqual(first_contact_time(scenario), 0.0)

        separated = Scenario("separated", 30, 20, 15, 1, 1)
        self.assertIsNone(first_contact_time(separated))

    def test_small_times_use_their_own_scale(self):
        # Tiny horizons must not inherit a tolerance based on one whole second.
        tiny_horizon = Scenario("tiny_horizon", 1e-15, 1, 0, 1e-18, 2)
        tiny_gap = Scenario("tiny_gap", 1e-12, 1, 0, 1, 2)

        self.assertIsNone(first_contact_time(tiny_horizon))
        self.assertEqual(first_contact_time(tiny_gap), 1e-12)

    def test_helper_branches_and_numeric_stability(self):
        # The large closing speed stresses arithmetic, not a driving scenario.
        self.assertIsNone(contact_delay(10, 0, 0))
        self.assertIsNone(contact_delay(10, -1, 0))

        self.assertAlmostEqual(
            contact_delay(1, 100000000, 1),
            1e-8,
            delta=1e-20,
        )
        self.assertAlmostEqual(
            contact_delay(1, -1, 1),
            2.7320508075688772,
            places=12,
        )

        with self.assertRaises(ValueError):
            contact_delay(1, 1e308, 1)
