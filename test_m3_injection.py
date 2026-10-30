"""Known-answer transforms, seeded injection and causal integration."""

from dataclasses import asdict, replace
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from evaluation import score_case
from faults import FaultConfig, apply_draws, inject_faults
from motion import Scenario, sample_truth
from observations import make_observations
from replay import make_decision_times, replay
from scenarios import m1_fixtures
from warning_policy import decide


class FaultInjectionTests(unittest.TestCase):
    """Check faults without changing truth or the warning/scoring policies."""

    def setUp(self):
        self.scenario = Scenario(
            scenario_id="fault_injection",
            initial_gap_m=30.0,
            ego_speed_mps=10.0,
            lead_speed_mps=5.0,
            timestep_s=1.0,
            sample_count=5,
        )
        self.truth = sample_truth(self.scenario)

    def transform(self, config, *, sample=None, **overrides):
        """Supply deterministic default draws for arithmetic fixtures."""
        draws = {
            "z_gap": 0.0,
            "z_closing": 0.0,
            "u_latency": 0.5,
            "u_dropout": 0.5,
        }
        draws.update(overrides)

        source = self.truth[2] if sample is None else sample
        return apply_draws(source, config, **draws)

    def test_explicit_noise_known_answer(self):
        sample = self.truth[2]
        before = asdict(sample)

        reading, audit = self.transform(
            FaultConfig(
                mode="noise",
                gap_sigma_m=2.0,
                closing_sigma_mps=0.5,
            ),
            z_gap=-1.0,
            z_closing=2.0,
        )

        # At 2 s: gap 20-2=18 m and closing speed 5+1=6 m/s.
        self.assertEqual(reading.gap_m, 18.0)
        self.assertEqual(reading.closing_speed_mps, 6.0)
        self.assertEqual(reading.measurement_time_s, 2.0)
        self.assertEqual(reading.arrival_time_s, 2.0)
        self.assertEqual(audit["gap_error_m"], -2.0)
        self.assertEqual(audit["closing_error_mps"], 1.0)
        self.assertEqual(asdict(sample), before)

        clean = make_observations([sample])[0]
        self.assertFalse(decide(clean, 2.0).is_warning)
        self.assertTrue(decide(reading, 2.0).is_warning)

    def test_latency_jitter_known_answer(self):
        reading, audit = self.transform(
            FaultConfig(
                mode="latency",
                latency_s=0.25,
                latency_jitter_s=0.5,
            ),
            u_latency=0.5,
        )

        self.assertEqual(reading.sample_id, 2)
        self.assertEqual(reading.measurement_time_s, 2.0)
        self.assertEqual(reading.arrival_time_s, 2.5)
        self.assertEqual(reading.gap_m, 20.0)
        self.assertEqual(reading.closing_speed_mps, 5.0)
        self.assertEqual(audit["delay_s"], 0.5)

    def test_dropout_boundary(self):
        config = FaultConfig(
            mode="dropout",
            dropout_probability=0.2,
        )

        dropped, dropped_audit = self.transform(
            config,
            u_dropout=0.19,
        )
        retained, retained_audit = self.transform(
            config,
            u_dropout=0.2,
        )

        self.assertIsNone(dropped)
        self.assertTrue(dropped_audit["dropped"])
        self.assertIsNotNone(retained)
        self.assertFalse(retained_audit["dropped"])
        self.assertEqual(dropped_audit["sample_id"], 2)

    def test_clean_and_fixed_latency_match_m2(self):
        for delay_s in (0.0, 0.75):
            with self.subTest(delay_s=delay_s):
                config = (
                    FaultConfig()
                    if delay_s == 0
                    else FaultConfig(
                        mode="latency",
                        latency_s=delay_s,
                    )
                )

                readings, audit = inject_faults(self.truth, config)

                self.assertEqual(
                    readings,
                    make_observations(self.truth, delay_s),
                )
                self.assertEqual(len(audit), len(self.truth))
                self.assertTrue(all(not row["dropped"] for row in audit))

    def test_full_dropout_preserves_clock_and_misses_contact(self):
        scenario = Scenario(
            scenario_id="all_drop",
            initial_gap_m=30.0,
            ego_speed_mps=10.0,
            lead_speed_mps=5.0,
            timestep_s=1.0,
            sample_count=7,
        )
        truth = sample_truth(scenario)

        retained, _ = inject_faults(
            truth,
            FaultConfig(
                mode="dropout",
                dropout_probability=0.0,
            ),
        )
        missing, audit = inject_faults(
            truth,
            FaultConfig(
                mode="dropout",
                dropout_probability=1.0,
            ),
        )

        self.assertEqual(len(retained), 7)
        self.assertEqual(missing, [])
        self.assertEqual(len(audit), 7)
        self.assertTrue(all(row["dropped"] for row in audit))

        times = make_decision_times(
            [row.time_s for row in truth],
            missing,
            scenario.horizon_s,
            scenario_id=scenario.scenario_id,
        )
        self.assertEqual(times, [0, 1, 2, 3, 4, 5, 6])

        result = replay(
            missing,
            times,
            scenario_id=scenario.scenario_id,
            horizon_s=scenario.horizon_s,
        )
        self.assertTrue(
            all(decision.reason == "unavailable" for decision in result.decisions)
        )

        # Independent geometry: 30 m / 5 m/s closing = contact at 6 s.
        score = score_case(result.decisions, 6.0, 6.0)
        self.assertEqual(score["outcome"], "missed")

    def test_repeated_runs_preserve_truth_and_reference(self):
        fixture = next(
            item
            for item in m1_fixtures()
            if item.scenario.scenario_id == "lead_braking_contact"
        )
        truth = sample_truth(fixture.scenario)
        before = [asdict(row) for row in truth]
        reference = fixture.reference_contact_time_s

        configurations = [
            FaultConfig(
                mode="noise",
                gap_sigma_m=0.5,
                closing_sigma_mps=0.1,
            ),
            FaultConfig(
                mode="latency",
                latency_s=0.25,
                latency_jitter_s=0.5,
            ),
            FaultConfig(
                mode="dropout",
                dropout_probability=0.3,
            ),
        ]

        for config in configurations:
            with self.subTest(mode=config.mode):
                settings_before = asdict(config)

                first = inject_faults(truth, config)
                second = inject_faults(truth, config)

                self.assertEqual(first, second)
                self.assertEqual(
                    [asdict(row) for row in truth],
                    before,
                )
                self.assertEqual(asdict(config), settings_before)
                self.assertEqual(
                    fixture.reference_contact_time_s,
                    reference,
                )

                times = make_decision_times(
                    [row.time_s for row in truth],
                    first[0],
                    fixture.scenario.horizon_s,
                    scenario_id=fixture.scenario.scenario_id,
                )
                first_replay = replay(
                    first[0],
                    times,
                    scenario_id=fixture.scenario.scenario_id,
                    horizon_s=fixture.scenario.horizon_s,
                )
                second_replay = replay(
                    second[0],
                    times,
                    scenario_id=fixture.scenario.scenario_id,
                    horizon_s=fixture.scenario.horizon_s,
                )
                self.assertEqual(first_replay, second_replay)

    def test_retained_late_arrivals_are_not_dropout(self):
        readings, audit = inject_faults(
            self.truth,
            FaultConfig(mode="latency", latency_s=10.0),
        )

        self.assertEqual(len(readings), 5)
        self.assertTrue(all(not row["dropped"] for row in audit))

        result = replay(
            readings,
            [row.time_s for row in self.truth],
            scenario_id=self.scenario.scenario_id,
            horizon_s=self.scenario.horizon_s,
        )

        self.assertEqual(result.beyond_horizon_arrival_count, 5)
        self.assertTrue(
            all(decision.reason == "unavailable" for decision in result.decisions)
        )

    def test_draw_order_includes_dropped_rows(self):
        calls = []

        def fixed_draw(label, value):
            def draw(*args):
                calls.append(label)
                return value

            return draw

        dropout_draws = iter([0.1, 0.9, 0.2, 0.8, 0.7])

        def next_dropout():
            calls.append("dropout")
            return next(dropout_draws)

        fake_rngs = {
            "gap": SimpleNamespace(gauss=fixed_draw("gap", 1.0)),
            "closing": SimpleNamespace(gauss=fixed_draw("closing", -1.0)),
            "latency": SimpleNamespace(random=fixed_draw("latency", 0.5)),
            "dropout": SimpleNamespace(random=next_dropout),
        }
        config = FaultConfig(
            mode="dropout",
            dropout_probability=0.3,
        )

        with patch(
            "faults.make_rngs",
            return_value=fake_rngs,
        ) as factory:
            readings, audit = inject_faults(self.truth, config)

        factory.assert_called_once_with(config)
        self.assertEqual(
            calls,
            ["gap", "closing", "latency", "dropout"] * 5,
        )
        self.assertEqual(
            [row.sample_id for row in readings],
            [1, 3, 4],
        )
        self.assertEqual(len(audit), 5)

    def test_bad_source_streams_fail_before_rng_creation(self):
        first, second = self.truth[:2]
        bad_streams = [
            [None],
            [object()],
            [first, first],
            [second, first],
            [first, replace(second, sample_id=0)],
            [first, replace(second, time_s=0.0)],
            [first, replace(second, scenario_id="other")],
            [replace(first, sample_id=True)],
            [replace(first, ego_speed_mps=-1.0)],
        ]
        config = FaultConfig(
            mode="dropout",
            dropout_probability=1.0,
        )

        for rows in bad_streams:
            with self.subTest(rows=rows):
                with patch("faults.make_rngs") as factory:
                    with self.assertRaises(ValueError):
                        inject_faults(rows, config)

                    factory.assert_not_called()

        # Direct single-row calls must validate too.
        with self.assertRaises(ValueError):
            self.transform(FaultConfig(), sample=object())

    def test_invalid_truth_values_are_not_hidden_by_dropout(self):
        fields = (
            "time_s",
            "ego_front_x_m",
            "lead_rear_x_m",
            "ego_speed_mps",
            "lead_speed_mps",
            "gap_m",
            "closing_speed_mps",
        )
        config = FaultConfig(
            mode="dropout",
            dropout_probability=1.0,
        )

        for field in fields:
            for value in (True, "bad", float("nan"), float("inf")):
                with self.subTest(field=field, value=value):
                    invalid = replace(
                        self.truth[0],
                        **{field: value},
                    )

                    with self.assertRaises(ValueError):
                        inject_faults([invalid], config)

    def test_invalid_draws_are_rejected(self):
        invalid_draws = [
            {"z_gap": float("nan")},
            {"z_closing": float("inf")},
            {"z_gap": True},
            {"u_latency": -0.1},
            {"u_latency": 1.0},
            {"u_dropout": 1.0},
            {"u_dropout": None},
        ]

        for draws in invalid_draws:
            with self.subTest(draws=draws):
                with self.assertRaises(ValueError):
                    self.transform(FaultConfig(), **draws)

    def test_computed_overflow_is_rejected(self):
        examples = [
            (
                FaultConfig(mode="noise", gap_sigma_m=1e308),
                self.truth[2],
                {"z_gap": 2.0},
            ),
            (
                FaultConfig(mode="noise", gap_sigma_m=1e308),
                replace(self.truth[2], gap_m=1e308),
                {"z_gap": 1.0},
            ),
            (
                FaultConfig(mode="latency", latency_s=1e308),
                replace(self.truth[2], time_s=1e308),
                {},
            ),
            (
                FaultConfig(
                    mode="latency",
                    latency_s=1e308,
                    latency_jitter_s=1e308,
                ),
                self.truth[2],
                {"u_latency": 0.9},
            ),
        ]

        for config, sample, draws in examples:
            with self.subTest(mode=config.mode, draws=draws):
                with self.assertRaises(ValueError):
                    self.transform(config, sample=sample, **draws)

    def test_empty_source_and_invalid_configuration(self):
        self.assertEqual(
            inject_faults([], FaultConfig()),
            ([], []),
        )

        for invalid in (None, {}, "noise"):
            with self.subTest(config=invalid):
                with self.assertRaises(ValueError):
                    inject_faults([], invalid)

                with self.assertRaises(ValueError):
                    self.transform(invalid)

    def test_gapped_ids_and_signed_values_are_preserved(self):
        source = [self.truth[1], self.truth[3]]
        readings, audit = inject_faults(source, FaultConfig())

        self.assertEqual(
            [row.sample_id for row in readings],
            [1, 3],
        )
        self.assertEqual(
            [row["sample_id"] for row in audit],
            [1, 3],
        )

        signed = sample_truth(
            Scenario(
                scenario_id="opening_overlap",
                initial_gap_m=-1.0,
                ego_speed_mps=4.0,
                lead_speed_mps=6.0,
                timestep_s=1.0,
                sample_count=1,
            )
        )[0]

        reading, _ = self.transform(
            FaultConfig(mode="noise"),
            sample=signed,
            z_gap=100.0,
            z_closing=-100.0,
        )
        self.assertEqual(reading.gap_m, -1.0)
        self.assertEqual(reading.closing_speed_mps, -2.0)

    def test_changing_one_seed_preserves_other_draws(self):
        original = FaultConfig(
            mode="noise",
            gap_sigma_m=0.5,
            closing_sigma_mps=0.1,
        )
        changed = replace(original, gap_seed=999)

        _, first = inject_faults(self.truth, original)
        _, second = inject_faults(self.truth, changed)

        for field in (
            "z_closing",
            "u_latency",
            "u_dropout",
            "closing_error_mps",
            "delay_s",
            "arrival_time_s",
            "dropped",
        ):
            with self.subTest(field=field):
                self.assertEqual(
                    [row[field] for row in first],
                    [row[field] for row in second],
                )


if __name__ == "__main__":
    unittest.main()
