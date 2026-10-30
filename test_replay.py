import unittest
from dataclasses import replace

from motion import sample_truth
from observations import Observation, make_observations
from replay import make_decision_times, replay
from scenarios import m1_fixtures
from warning_policy import decide


class WarningPolicyTests(unittest.TestCase):
    def test_known_ttc_branches(self):
        cases = [
            (10, 5, 2.0, True, "ttc_warning"),
            (15, 5, 3.0, True, "ttc_warning"),
            (15.5, 5, 3.1, False, "ttc_clear"),
            (10, 0, None, False, "not_closing"),
            (10, -2, None, False, "not_closing"),
            (0, -2, 0.0, True, "contact_or_overlap"),
            (-1, -2, 0.0, True, "contact_or_overlap"),
        ]

        for gap, closing, expected_ttc, warning, reason in cases:
            with self.subTest(gap=gap, closing=closing):
                reading = Observation("fixture", 0, 0.0, 0.0, gap, closing)
                decision = decide(reading, 0.0)

                if expected_ttc is None:
                    self.assertIsNone(decision.ttc_s)
                else:
                    self.assertAlmostEqual(decision.ttc_s, expected_ttc)

                self.assertEqual(decision.is_warning, warning)
                self.assertEqual(decision.reason, reason)

    def test_age_and_unavailable_states(self):
        unavailable = decide(None, 0.0)

        self.assertEqual(unavailable.reason, "unavailable")
        self.assertIsNone(unavailable.sample_id)
        self.assertIsNone(unavailable.ttc_s)
        self.assertFalse(unavailable.is_warning)

        reading = Observation("fixture", 0, 0.0, 1.0, 10.0, 5.0)

        fresh = decide(reading, 1.0)
        self.assertEqual(fresh.observation_age_s, 1.0)
        self.assertEqual(fresh.ttc_s, 2.0)
        self.assertTrue(fresh.is_warning)

        boundary = decide(reading, 1.25)
        self.assertTrue(boundary.is_warning)

        stale = decide(reading, 1.2501)
        self.assertEqual(stale.reason, "stale")
        self.assertIsNone(stale.ttc_s)
        self.assertFalse(stale.is_warning)
        self.assertEqual(stale.gap_m, 10.0)

        stale_contact = decide(
            replace(reading, gap_m=0.0),
            1.2501,
        )
        self.assertEqual(stale_contact.reason, "stale")
        self.assertIsNone(stale_contact.ttc_s)

    def test_invalid_parameters_and_unarrived_readings(self):
        changes = [
            {"now_s": -1},
            {"now_s": True},
            {"warning_threshold_s": 0},
            {"warning_threshold_s": float("nan")},
            {"max_age_s": -1},
            {"max_age_s": float("inf")},
        ]

        for change in changes:
            settings = {
                "now_s": 0.0,
                "warning_threshold_s": 3.0,
                "max_age_s": 1.25,
            }
            settings.update(change)

            with self.subTest(change=change):
                with self.assertRaises(ValueError):
                    decide(None, **settings)

        future = Observation("fixture", 0, 1.0, 2.0, 10.0, 5.0)

        with self.assertRaises(ValueError):
            decide(future, 1.0)

        with self.assertRaises(ValueError):
            decide({}, 0.0)

    def test_nonfinite_ttc_is_rejected(self):
        reading = Observation("fixture", 0, 0.0, 0.0, 1e308, 1e-308)

        with self.assertRaises(ValueError):
            decide(reading, 0.0)


class ReplayTests(unittest.TestCase):
    def test_arrival_boundary_and_staleness(self):
        reading = Observation("fixture", 0, 0.0, 1.0, 10.0, 5.0)

        result = replay(
            [reading],
            [0.0, 0.999, 1.0, 1.25, 1.2501],
            scenario_id="fixture",
            horizon_s=1.2501,
        )

        self.assertEqual(
            [decision.reason for decision in result.decisions],
            [
                "unavailable",
                "unavailable",
                "ttc_warning",
                "ttc_warning",
                "stale",
            ],
        )
        self.assertEqual(
            result.decisions[2].observation_age_s,
            1.0,
        )

    def test_out_of_order_arrivals_keep_newest_measurement(self):
        older = Observation("fixture", 0, 1.0, 3.0, 15.0, 5.0)
        newer = Observation("fixture", 1, 2.0, 2.5, 10.0, 5.0)

        readings = [older, newer]
        before = list(readings)

        result = replay(
            readings,
            [0.0, 2.5, 3.0],
            scenario_id="fixture",
            horizon_s=3.0,
        )

        self.assertEqual(
            [decision.sample_id for decision in result.decisions],
            [None, 1, 1],
        )
        self.assertEqual(result.ignored_older_arrival_count, 1)
        self.assertEqual(readings, before)

    def test_all_simultaneous_arrivals_are_consumed(self):
        older = Observation("fixture", 0, 0.0, 2.0, 50.0, 5.0)
        newer = Observation("fixture", 1, 1.0, 2.0, 10.0, 5.0)

        result = replay(
            [newer, older],
            [0.0, 2.0],
            scenario_id="fixture",
            horizon_s=2.0,
        )

        final = result.decisions[-1]
        self.assertEqual(final.sample_id, 1)
        self.assertEqual(final.ttc_s, 2.0)
        self.assertTrue(final.is_warning)

    def test_clock_union_and_zero_horizon(self):
        readings = [
            Observation("fixture", 0, 0.0, 0.5, 10.0, 5.0),
            Observation("fixture", 1, 1.0, 1.5, 10.0, 5.0),
            Observation("fixture", 2, 2.0, 2.5, 5.0, 5.0),
        ]

        times = make_decision_times(
            [2.0, 0.0, 1.0, 1.0],
            readings,
            2.0,
            scenario_id="fixture",
        )

        self.assertEqual(times, [0.0, 0.5, 1.0, 1.5, 2.0])

        zero_times = make_decision_times(
            [],
            [],
            0.0,
            scenario_id="fixture",
        )
        result = replay(
            [],
            zero_times,
            scenario_id="fixture",
            horizon_s=0.0,
        )

        self.assertEqual(zero_times, [0.0])
        self.assertEqual(len(result.decisions), 1)
        self.assertEqual(result.decisions[0].reason, "unavailable")

    def test_invalid_clocks_are_rejected(self):
        invalid_clocks = [
            [],
            [0.0, 0.0, 1.0],
            [0.0, 0.8, 0.5, 1.0],
            [0.5, 1.0],
            [0.0, 0.5],
            [0.0, float("nan"), 1.0],
            [0.0, True],
            [0.0, 1.1],
        ]

        for times in invalid_clocks:
            with self.subTest(times=times):
                with self.assertRaises(ValueError):
                    replay(
                        [],
                        times,
                        scenario_id="fixture",
                        horizon_s=1.0,
                    )

        with self.assertRaises(ValueError):
            make_decision_times(
                [0.0, 1.1],
                [],
                1.0,
                scenario_id="fixture",
            )

        with self.assertRaises(ValueError):
            make_decision_times(
                [0.0],
                [{}],
                1.0,
                scenario_id="fixture",
            )

    def test_arrivals_at_and_after_horizon(self):
        at_horizon = Observation("fixture", 0, 0.0, 2.0, 10.0, 5.0)
        after_horizon = Observation("fixture", 1, 1.0, 2.1, 0.0, 1.0)

        result = replay(
            [at_horizon, after_horizon],
            [0.0, 2.0],
            max_age_s=3.0,
            scenario_id="fixture",
            horizon_s=2.0,
        )

        self.assertEqual(result.decisions[-1].sample_id, 0)
        self.assertTrue(result.decisions[-1].is_warning)
        self.assertEqual(result.beyond_horizon_arrival_count, 1)

    def test_future_values_do_not_change_past_decisions(self):
        initial = Observation("fixture", 0, 0.0, 0.0, 30.0, 5.0)
        future = Observation("fixture", 1, 1.0, 2.0, 10.0, 5.0)
        changed_future = replace(
            future,
            gap_m=1000.0,
            closing_speed_mps=0.0,
        )

        settings = {
            "scenario_id": "fixture",
            "horizon_s": 3.0,
        }
        times = [0.0, 1.0, 2.0, 3.0]

        original = replay([initial, future], times, **settings)
        changed = replay(
            [initial, changed_future],
            times,
            **settings,
        )

        # Only decisions at or after arrival may depend on these values.
        self.assertEqual(
            original.decisions[:2],
            changed.decisions[:2],
        )
        self.assertTrue(original.decisions[2].is_warning)
        self.assertFalse(changed.decisions[2].is_warning)

    def test_m1_first_warning_times(self):
        fixture = next(
            fixture
            for fixture in m1_fixtures()
            if fixture.scenario.scenario_id == "lead_braking_contact"
        )
        scenario = fixture.scenario
        truth = sample_truth(scenario)
        before = tuple(truth)

        base_times = [
            index * scenario.timestep_s for index in range(scenario.sample_count)
        ]

        for delay_s, expected_first_s in (
            (0.0, 2.0),
            (0.5, 2.5),
            (1.0, 3.0),
        ):
            with self.subTest(delay_s=delay_s):
                readings = make_observations(truth, delay_s)

                times = make_decision_times(
                    base_times,
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

                first_warning_s = next(
                    decision.decision_time_s
                    for decision in result.decisions
                    if decision.is_warning
                )

                self.assertEqual(first_warning_s, expected_first_s)
                self.assertEqual(tuple(truth), before)

                if delay_s == 1.0:
                    decision = next(
                        decision
                        for decision in result.decisions
                        if decision.decision_time_s == 3.0
                    )
                    self.assertEqual(decision.measurement_time_s, 2.0)
                    self.assertEqual(decision.arrival_time_s, 3.0)
                    self.assertEqual(decision.observation_age_s, 1.0)
                    self.assertEqual(decision.ttc_s, 1.75)


if __name__ == "__main__":
    unittest.main()
