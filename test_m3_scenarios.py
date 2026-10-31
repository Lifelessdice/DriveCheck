"""Independent stop-and-go motion and contact fixtures."""

from dataclasses import asdict, replace
import math
import unittest

from evaluation import score_case
from faults import FaultConfig, inject_faults
from replay import make_decision_times, replay
from stop_and_go import (
    StopGoScenario,
    first_stop_go_contact_time,
    sample_stop_go_truth,
    stop_go_fixtures,
    stop_go_truth_at,
)


class StopGoTests(unittest.TestCase):
    """Check continuous motion independently of warnings and sample spacing."""

    def setUp(self):
        self.case = StopGoScenario(
            scenario_id="stop_go_test",
            initial_gap_m=15.0,
        )

    def test_derived_phase_values(self):
        self.assertEqual(self.case.family, "stop_and_go")
        self.assertEqual(self.case.stop_time_s, 2.0)
        self.assertEqual(self.case.restart_time_s, 4.0)
        self.assertEqual(self.case.cruise_time_s, 7.0)
        self.assertEqual(self.case.stop_distance_m, 4.0)
        self.assertEqual(self.case.cruise_distance_m, 13.0)
        self.assertEqual(self.case.horizon_s, 8.0)

    def test_independent_truth_table(self):
        # t, ego x, lead x, gap, lead speed, closing speed.
        expected = [
            (0, 0, 15, 15, 4, 0),
            (1, 4, 18, 14, 2, 2),
            (2, 8, 19, 11, 0, 4),
            (3, 12, 19, 7, 0, 4),
            (4, 16, 19, 3, 0, 4),
            (5, 20, 20, 0, 2, 2),
            (6, 24, 23, -1, 4, 0),
            (7, 28, 28, 0, 6, -2),
            (8, 32, 34, 2, 6, -2),
        ]
        samples = sample_stop_go_truth(self.case)

        self.assertEqual(len(samples), 9)

        for index, values in enumerate(expected):
            with self.subTest(time_s=values[0]):
                row = samples[index]
                self.assertEqual(row.sample_id, index)
                self.assertEqual(
                    (
                        row.time_s,
                        row.ego_front_x_m,
                        row.lead_rear_x_m,
                        row.gap_m,
                        row.lead_speed_mps,
                        row.closing_speed_mps,
                    ),
                    values,
                )
                self.assertEqual(row.ego_speed_mps, 4.0)

    def test_literal_fixture_references(self):
        fixtures = stop_go_fixtures()
        self.assertEqual(len(fixtures), 2)

        for fixture, event, final_gap in zip(
            fixtures,
            (5.0, None),
            (2.0, 5.0),
        ):
            with self.subTest(id=fixture.scenario.scenario_id):
                self.assertEqual(
                    fixture.reference_contact_time_s,
                    event,
                )
                self.assertEqual(
                    fixture.reference_final_gap_m,
                    final_gap,
                )
                self.assertTrue(fixture.reference_basis)

                actual = first_stop_go_contact_time(fixture.scenario)

                if event is None:
                    self.assertIsNone(actual)
                else:
                    self.assertAlmostEqual(
                        actual,
                        event,
                        delta=1e-9,
                    )

                final = stop_go_truth_at(
                    fixture.scenario,
                    fixture.scenario.horizon_s,
                )
                self.assertAlmostEqual(
                    final.gap_m,
                    final_gap,
                    delta=1e-9,
                )

    def test_noncontact_minimum(self):
        for initial_gap, minimum, final_gap in (
            (18.0, 2.0, 5.0),
            (17.0, 1.0, 4.0),
        ):
            with self.subTest(initial_gap=initial_gap):
                case = replace(
                    self.case,
                    initial_gap_m=initial_gap,
                )

                self.assertIsNone(first_stop_go_contact_time(case))
                self.assertEqual(
                    stop_go_truth_at(case, 6.0).gap_m,
                    minimum,
                )
                self.assertEqual(
                    stop_go_truth_at(case, 8.0).gap_m,
                    final_gap,
                )

    def test_tangent_contact(self):
        case = replace(self.case, initial_gap_m=16.0)

        self.assertEqual(stop_go_truth_at(case, 5.0).gap_m, 1.0)
        self.assertEqual(stop_go_truth_at(case, 6.0).gap_m, 0.0)
        self.assertEqual(stop_go_truth_at(case, 7.0).gap_m, 1.0)
        self.assertAlmostEqual(
            first_stop_go_contact_time(case),
            6.0,
            delta=1e-9,
        )

    def test_contact_does_not_depend_on_sampling_grid(self):
        for timestep, count in ((1.0, 9), (0.25, 33), (4.0, 3)):
            with self.subTest(timestep=timestep):
                case = replace(
                    self.case,
                    timestep_s=timestep,
                    sample_count=count,
                )
                self.assertEqual(case.horizon_s, 8.0)
                self.assertAlmostEqual(
                    first_stop_go_contact_time(case),
                    5.0,
                    delta=1e-9,
                )

                if timestep == 4.0:
                    samples = sample_stop_go_truth(case)
                    self.assertEqual(
                        [row.gap_m for row in samples],
                        [15.0, 3.0, 2.0],
                    )

    def test_phase_boundary_continuity(self):
        fields = (
            "ego_front_x_m",
            "lead_rear_x_m",
            "ego_speed_mps",
            "lead_speed_mps",
            "gap_m",
            "closing_speed_mps",
        )

        for boundary in (2.0, 4.0, 7.0):
            centre = stop_go_truth_at(self.case, boundary)
            neighbours = (
                math.nextafter(boundary, -math.inf),
                math.nextafter(boundary, math.inf),
            )

            for time_s in neighbours:
                row = stop_go_truth_at(self.case, time_s)

                for field in fields:
                    with self.subTest(
                        boundary=boundary,
                        field=field,
                        time_s=time_s,
                    ):
                        self.assertAlmostEqual(
                            getattr(row, field),
                            getattr(centre, field),
                            delta=1e-12,
                        )

    def test_contact_at_stop_and_restart(self):
        for initial_gap, expected_time in ((4.0, 2.0), (12.0, 4.0)):
            with self.subTest(initial_gap=initial_gap):
                case = replace(
                    self.case,
                    initial_gap_m=initial_gap,
                )
                self.assertAlmostEqual(
                    first_stop_go_contact_time(case),
                    expected_time,
                    delta=1e-9,
                )

    def test_horizon_and_initial_contact(self):
        before = replace(
            self.case,
            timestep_s=4.9,
            sample_count=2,
        )
        inclusive = replace(
            self.case,
            timestep_s=5.0,
            sample_count=2,
        )

        self.assertIsNone(first_stop_go_contact_time(before))
        self.assertAlmostEqual(
            first_stop_go_contact_time(inclusive),
            5.0,
            delta=1e-9,
        )

        zero_horizon = replace(self.case, sample_count=1)
        self.assertIsNone(first_stop_go_contact_time(zero_horizon))

        for gap in (0.0, -1.0):
            case = replace(
                zero_horizon,
                initial_gap_m=gap,
            )
            self.assertEqual(
                first_stop_go_contact_time(case),
                0.0,
            )

    def test_zero_duration_phases(self):
        initially_stopped = replace(
            self.case,
            initial_gap_m=5.0,
            lead_speed_mps=0.0,
            hold_s=0.0,
        )
        self.assertEqual(initially_stopped.stop_time_s, 0.0)
        self.assertEqual(initially_stopped.restart_time_s, 0.0)
        self.assertEqual(
            stop_go_truth_at(initially_stopped, 2.0).gap_m,
            1.0,
        )
        self.assertEqual(
            stop_go_truth_at(initially_stopped, 8.0).gap_m,
            12.0,
        )
        self.assertIsNone(first_stop_go_contact_time(initially_stopped))

        no_hold = replace(
            self.case,
            initial_gap_m=20.0,
            hold_s=0.0,
        )
        self.assertEqual(no_hold.restart_time_s, 2.0)
        self.assertEqual(
            stop_go_truth_at(no_hold, 3.0).lead_speed_mps,
            2.0,
        )

        no_restart = replace(
            self.case,
            restart_speed_mps=0.0,
        )
        self.assertEqual(
            no_restart.cruise_time_s,
            no_restart.restart_time_s,
        )
        self.assertEqual(
            stop_go_truth_at(no_restart, 8.0).lead_speed_mps,
            0.0,
        )
        self.assertAlmostEqual(
            first_stop_go_contact_time(no_restart),
            4.75,
            delta=1e-9,
        )

    def test_stationary_ego_and_no_reverse_motion(self):
        case = replace(
            self.case,
            ego_speed_mps=0.0,
            timestep_s=0.25,
            sample_count=33,
        )
        rows = sample_stop_go_truth(case)

        self.assertTrue(all(row.lead_speed_mps >= 0 for row in rows))
        self.assertTrue(
            all(
                later.lead_rear_x_m >= earlier.lead_rear_x_m
                for earlier, later in zip(rows, rows[1:])
            )
        )
        self.assertIsNone(first_stop_go_contact_time(case))

    def test_invalid_settings_and_queries(self):
        invalid_settings = [
            {"scenario_id": "con"},
            {"scenario_id": "../outside"},
            {"initial_gap_m": math.inf},
            {"ego_speed_mps": True},
            {"lead_deceleration_mps2": 0.0},
            {"lead_acceleration_mps2": 0.0},
            {"hold_s": -1.0},
            {"restart_speed_mps": -1.0},
            {"timestep_s": 0.0},
            {"sample_count": True},
            {"sample_count": 1.5},
            {"timestep_s": 1e308, "sample_count": 3},
            {
                "lead_speed_mps": 1e308,
                "lead_deceleration_mps2": 1e-308,
            },
            {"hold_s": 1e308},
        ]

        for settings in invalid_settings:
            with self.subTest(settings=settings):
                with self.assertRaises(ValueError):
                    replace(self.case, **settings)

        for time_s in (-1, True, None, math.nan, math.inf, 9.0):
            with self.subTest(time_s=time_s):
                with self.assertRaises(ValueError):
                    stop_go_truth_at(self.case, time_s)

        for sample_id in (-1, True, 1.5):
            with self.subTest(sample_id=sample_id):
                with self.assertRaises(ValueError):
                    stop_go_truth_at(
                        self.case,
                        0.0,
                        sample_id=sample_id,
                    )

        with self.assertRaises(ValueError):
            stop_go_truth_at(object(), 0.0)

        for function in (
            sample_stop_go_truth,
            first_stop_go_contact_time,
        ):
            with self.assertRaises(ValueError):
                function(object())

    def test_stable_early_root_and_tiny_horizon(self):
        fast = replace(
            self.case,
            initial_gap_m=1.0,
            ego_speed_mps=1e8,
            lead_speed_mps=0.0,
            hold_s=0.0,
            restart_speed_mps=2.0,
            timestep_s=1.0,
            sample_count=2,
        )

        # Restart equation is 1 - 1e8*t + t^2 = 0.
        # The early root is approximately 1e-8 s.
        self.assertAlmostEqual(
            first_stop_go_contact_time(fast),
            1e-8,
            delta=1e-20,
        )

        tiny = replace(
            self.case,
            initial_gap_m=2e-18,
            ego_speed_mps=1.0,
            lead_speed_mps=0.0,
            hold_s=1.0,
            timestep_s=1e-18,
            sample_count=2,
        )
        self.assertIsNone(first_stop_go_contact_time(tiny))

        touching_at_horizon = replace(
            tiny,
            initial_gap_m=1e-18,
        )
        self.assertEqual(
            first_stop_go_contact_time(touching_at_horizon),
            1e-18,
        )

    def test_existing_fault_replay_and_scoring_integration(self):
        for fixture in stop_go_fixtures():
            scenario = fixture.scenario
            truth = sample_stop_go_truth(scenario)
            before = [asdict(row) for row in truth]
            positive = fixture.reference_contact_time_s is not None

            for drop_all in (False, True):
                with self.subTest(
                    id=scenario.scenario_id,
                    drop_all=drop_all,
                ):
                    config = (
                        FaultConfig(
                            mode="dropout",
                            dropout_probability=1.0,
                        )
                        if drop_all
                        else FaultConfig()
                    )
                    readings, audit = inject_faults(truth, config)

                    times = make_decision_times(
                        [row.time_s for row in truth],
                        readings,
                        scenario.horizon_s,
                        scenario_id=scenario.scenario_id,
                    )
                    result = replay(
                        readings,
                        times,
                        scenario_id=scenario.scenario_id,
                        horizon_s=scenario.horizon_s,
                    )
                    score = score_case(
                        result.decisions,
                        fixture.reference_contact_time_s,
                        scenario.horizon_s,
                    )

                    expected = (
                        ("missed" if positive else "clear_negative")
                        if drop_all
                        else ("useful" if positive else "false_warning")
                    )
                    self.assertEqual(score["outcome"], expected)
                    self.assertEqual(len(audit), len(truth))
                    self.assertEqual(
                        [asdict(row) for row in truth],
                        before,
                    )

                    if not drop_all:
                        self.assertEqual(
                            score["first_warning_time_s"],
                            2.0 if positive else 3.0,
                        )


if __name__ == "__main__":
    unittest.main()
