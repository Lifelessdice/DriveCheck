"""Independent inventory and configuration guards for the release plan."""

from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
import tempfile
import unittest

from faults import FaultConfig
from release_config import (
    ROOT,
    build_plan,
    describe_plan,
    fixture_registry,
    is_stochastic,
    load_configuration,
    validate_configuration,
)


class TestReleaseConfiguration(unittest.TestCase):
    def setUp(self):
        self.config = load_configuration("configs/m4-release.json")

    def test_declared_inventory_has_76_unique_pending_cases(self):
        plan = build_plan(self.config)

        self.assertEqual(len(plan), 76)
        self.assertEqual(
            len({row["case_id"] for row in plan}),
            76,
        )

        self.assertEqual(
            {row["status"] for row in plan},
            {"pending"},
        )

        self.assertTrue(all(row["score"] is None for row in plan))
        self.assertTrue(all(row["errors"] is None for row in plan))

        summary = describe_plan(plan)

        self.assertEqual(
            summary["positive_case_count"],
            38,
        )
        self.assertEqual(
            summary["negative_case_count"],
            38,
        )
        self.assertEqual(
            summary["case_count_by_condition"],
            {
                "clean": 4,
                "dropout_low": 12,
                "dropout_strong": 12,
                "latency_low": 12,
                "latency_strong": 12,
                "noise_low": 12,
                "noise_strong": 12,
            },
        )

    def test_every_scenario_has_19_cases(self):
        plan = build_plan(self.config)

        for name in fixture_registry():
            with self.subTest(scenario_id=name):
                self.assertEqual(
                    sum(row["scenario_id"] == name for row in plan),
                    19,
                )

    def test_native_stream_mapping_and_deterministic_placeholders(self):
        plan = build_plan(self.config)

        expected_bundles = (
            (100, (101, 102, 103, 104)),
            (200, (201, 202, 203, 204)),
            (300, (301, 302, 303, 304)),
        )

        seed_fields = (
            "gap_seed",
            "closing_seed",
            "latency_seed",
            "dropout_seed",
        )

        for base, expected in expected_bundles:
            row = next(row for row in plan if row["seed_base"] == base)

            self.assertEqual(
                tuple(row["fault"][name] for name in seed_fields),
                expected,
            )

        clean = [row for row in plan if row["condition_id"] == "clean"]

        self.assertEqual(len(clean), 4)

        self.assertTrue(all(row["seed_base"] is None for row in clean))
        self.assertTrue(all(row["fault"] == asdict(FaultConfig()) for row in clean))

    def test_m3_policy_parameters_are_preserved(self):
        for row in build_plan(self.config):
            self.assertEqual(
                row["policy"],
                {
                    "warning_threshold_s": 3.0,
                    "max_age_s": 1.25,
                    "pre_event_window_s": 4.0,
                    "minimum_useful_lead_s": 1.0,
                    "decision_clock": ("source schedule plus in-horizon arrivals"),
                },
            )

    def test_jitter_makes_latency_stochastic(self):
        self.assertFalse(
            is_stochastic(
                FaultConfig(
                    mode="latency",
                    latency_s=0.5,
                )
            )
        )

        self.assertTrue(
            is_stochastic(
                FaultConfig(
                    mode="latency",
                    latency_s=0.5,
                    latency_jitter_s=1.5,
                )
            )
        )

        self.assertFalse(
            is_stochastic(
                FaultConfig(
                    mode="dropout",
                    dropout_probability=1.0,
                )
            )
        )

    def test_literal_reference_answers_are_retained(self):
        plan = build_plan(self.config)

        answers = {
            "lead_braking_contact": (
                3.3166247903554,
                -32.5,
                5,
            ),
            "lead_braking_noncontact": (
                None,
                20.0,
                8,
            ),
            "stop_and_go_contact": (
                5.0,
                2.0,
                8,
            ),
            "stop_and_go_noncontact": (
                None,
                5.0,
                8,
            ),
        }

        for name, expected in answers.items():
            row = next(row for row in plan if row["scenario_id"] == name)

            self.assertEqual(
                (
                    row["reference_contact_time_s"],
                    row["reference_final_gap_m"],
                    row["horizon_s"],
                ),
                expected,
            )

    def test_input_and_plan_rows_do_not_share_mutable_state(self):
        before = deepcopy(self.config)
        plan = build_plan(self.config)

        plan[0]["policy"]["max_age_s"] = 99
        plan[0]["configuration"]["initial_gap_m"] = 999
        plan[0]["fault"]["gap_seed"] = 999

        self.assertEqual(self.config, before)

        self.assertEqual(
            plan[1]["policy"]["max_age_s"],
            1.25,
        )
        self.assertEqual(
            plan[1]["configuration"]["initial_gap_m"],
            30,
        )
        self.assertEqual(
            plan[1]["fault"]["gap_seed"],
            101,
        )

    def test_four_seed_bases_give_100_cases(self):
        config = deepcopy(self.config)

        for condition in config["conditions"]:
            if condition["condition_id"] != "clean":
                condition["seed_bases"].append(400)

        # Four scenarios × (one clean + six profiles × four bases).
        self.assertEqual(
            len(build_plan(config)),
            100,
        )

    def test_invalid_ids_and_empty_selections_are_rejected(self):
        invalid_selections = (
            [],
            ["unknown"],
            ["lead_braking_contact"] * 2,
            [True],
        )

        for names in invalid_selections:
            config = deepcopy(self.config)
            config["scenario_ids"] = names

            with self.subTest(names=names):
                with self.assertRaises(ValueError):
                    validate_configuration(config)

        invalid_conditions = (
            [],
            [self.config["conditions"][0]] * 2,
        )

        for conditions in invalid_conditions:
            config = deepcopy(self.config)
            config["conditions"] = conditions

            with self.assertRaises(ValueError):
                validate_configuration(config)

    def test_unknown_fields_and_unsupported_versions_are_rejected(self):
        invalid_settings = (
            ("schema_version", "drivecheck.m4.v999"),
            ("fixture_set", "unknown"),
            ("decision_clock", "fixed_0p1s"),
            ("unexpected", 1),
        )

        for field, value in invalid_settings:
            config = deepcopy(self.config)
            config[field] = value

            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    validate_configuration(config)

        config = deepcopy(self.config)
        config["conditions"][1]["fault"]["gap_std_m"] = 0.2

        with self.assertRaises(ValueError):
            validate_configuration(config)

    def test_invalid_seed_contracts_are_rejected(self):
        invalid_bases = (
            [],
            [None],
            [True],
            [-1],
            [1.5],
            [100, 100],
        )

        for bases in invalid_bases:
            config = deepcopy(self.config)
            config["conditions"][1]["seed_bases"] = bases

            with self.subTest(bases=bases):
                with self.assertRaises(ValueError):
                    validate_configuration(config)

        config = deepcopy(self.config)
        config["conditions"][0]["seed_bases"] = [100]

        with self.assertRaises(ValueError):
            validate_configuration(config)

    def test_invalid_faults_and_policy_are_rejected(self):
        invalid_faults = (
            {
                "mode": "noise",
                "gap_sigma_m": -0.2,
            },
            {
                "mode": "noise",
                "gap_sigma_m": float("nan"),
            },
            {
                "mode": "noise",
                "gap_sigma_m": 0.2,
                "latency_s": 1.0,
            },
            {
                "mode": "noise",
                "gap_sigma_m": 0.2,
                "gap_seed": 101,
            },
            {
                "mode": "dropout",
                "dropout_probability": 1.2,
            },
        )

        for fault in invalid_faults:
            config = deepcopy(self.config)
            config["conditions"][1]["fault"] = fault

            with self.subTest(fault=fault):
                with self.assertRaises(ValueError):
                    validate_configuration(config)

        config = deepcopy(self.config)
        config["scoring"]["minimum_useful_lead_s"] = 5

        with self.assertRaises(ValueError):
            validate_configuration(config)

        config = deepcopy(self.config)
        config["warning"]["threshold_s"] = float("inf")

        with self.assertRaises(ValueError):
            validate_configuration(config)

    def test_json_loader_rejects_duplicate_and_nonstandard_numbers(self):
        (ROOT / "outputs").mkdir(exist_ok=True)

        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            path = Path(directory) / "invalid.json"

            path.write_text(
                '{"schema_version": 1, "schema_version": 2}',
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                ValueError,
                "duplicate JSON key",
            ):
                load_configuration(path)

            path.write_text(
                '{"value": NaN}',
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                ValueError,
                "nonstandard JSON number",
            ):
                load_configuration(path)

            overflow = deepcopy(self.config)
            overflow["warning"]["threshold_s"] = "__overflow__"

            text = json.dumps(overflow).replace(
                '"__overflow__"',
                "1e400",
            )

            path.write_text(text, encoding="utf-8")

            with self.assertRaises(ValueError):
                load_configuration(path)

    def test_plan_is_repeatable_and_contains_no_diagnostic_rows(self):
        first = build_plan(self.config)

        self.assertEqual(
            first,
            build_plan(self.config),
        )
        self.assertEqual(
            {row["section"] for row in first},
            {"matrix"},
        )


if __name__ == "__main__":
    unittest.main()
