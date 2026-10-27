import unittest

from motion import gap_after_seconds, sample_constant_speed


class TestGapAfterSeconds(unittest.TestCase):
    def test_gap_after_seconds(self):
        expected_gap_m = 20

        actual_gap_m = gap_after_seconds(30.0, 20.0, 15.0, 2.0)
        self.assertEqual(expected_gap_m, actual_gap_m)


class SamplingTests(unittest.TestCase):
    def test_original_five_rows(self):
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
