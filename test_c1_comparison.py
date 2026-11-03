"""Independent split, inventory, pairing, failure and repetition evidence."""

from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import c1_comparison as comparison
from c1_replay import replay_with_estimator
from faults import inject_faults
from m3_study import canonical_hash


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.sandbox = tempfile.TemporaryDirectory(dir=comparison.ROOT / "outputs")
        self.addCleanup(self.sandbox.cleanup)
        self.root = Path(self.sandbox.name)

    def fixture_configuration(self):
        # Test-only episodes never use the frozen final holdout inputs.
        config = comparison.load_configuration()
        config.update(development_seed_bases=[9000], evaluation_seed_bases=[9100],
                      evaluation_transform={"length_scale": 1.7, "time_scale": 1.4},
                      include_diagnostics=False)
        path = self.root / "test-plan.json"
        path.write_text(json.dumps(config), encoding="utf-8")
        return path, config

    def test_frozen_default_inventory_and_independent_scaled_references(self):
        config = comparison.load_configuration()
        before = deepcopy(config)
        plan = comparison.prepare_plan(config)
        self.assertEqual(config, before)
        self.assertEqual(Counter(e["row"]["split"] for e in plan),
                         {"development": 76, "evaluation": 76, "diagnostic": 5})
        self.assertEqual(len({e["row"]["case_id"] for e in plan}), 157)
        evaluation = {e["row"]["scenario_id"]: e["row"] for e in plan
                      if e["row"]["split"] == "evaluation"}
        expected = {
            "eval_lead_braking_contact": (4.14578098794425, -48.75),
            "eval_lead_braking_noncontact": (None, 30.0),
            "eval_stop_and_go_contact": (6.25, 3.0),
            "eval_stop_and_go_noncontact": (None, 7.5),
        }
        self.assertEqual(set(evaluation), set(expected))
        for scenario_id, (event, final_gap) in expected.items():
            row = evaluation[scenario_id]
            if event is None:
                self.assertIsNone(row["reference_contact_time_s"])
            else:
                self.assertAlmostEqual(row["reference_contact_time_s"], event)
            self.assertAlmostEqual(row["reference_final_gap_m"], final_gap)
            self.assertEqual(row["truth_file"], f"{row['artifact_dir']}/truth.csv")
        dev_rows = [e["row"] for e in plan if e["row"]["split"] == "development"]
        counts = Counter(row["condition_id"] for row in dev_rows)
        self.assertEqual(counts["clean"], 4)
        self.assertTrue(all(value == 12 for key, value in counts.items() if key != "clean"))

    def test_invalid_and_overlapping_splits_are_rejected(self):
        original = comparison.load_configuration()
        variants = [
            {"extra": 1}, {"development_seed_bases": []},
            {"development_seed_bases": [True]}, {"evaluation_seed_bases": [100]},
            {"evaluation_seed_bases": [101]}, {"evaluation_seed_bases": [1000, 1000]},
            {"evaluation_transform": {"length_scale": 1.0, "time_scale": 1.0}},
            {"evaluation_transform": {"length_scale": float("nan"), "time_scale": 1.25}},
            {"alternative": "kalman"}, {"include_diagnostics": 1},
            {"baseline_config": "../outside.json"},
        ]
        for changes in variants:
            with self.subTest(changes=changes):
                config = deepcopy(original)
                config.update(changes)
                with self.assertRaises(ValueError):
                    comparison.validate_configuration(config)

    def test_inputs_generated_once_and_all_method_records_retained(self):
        path, _ = self.fixture_configuration()
        destination = self.root / "paired"
        with patch("c1_comparison.inject_faults", wraps=inject_faults) as injector:
            manifest = comparison.run(path, destination)
        self.assertEqual(manifest["status"], "complete")
        self.assertEqual(len(manifest["cases"]), 56)
        self.assertEqual(injector.call_count, 56)
        for split in ("development", "evaluation"):
            summary = manifest["summary"][split]
            self.assertEqual(summary["planned_pairs"], 28)
            self.assertEqual(summary["planned_method_records"], 56)
            self.assertEqual(summary["complete_pairs"], 28)
        frozen = json.loads((destination / "frozen-selection.json").read_text())
        plan = json.loads((destination / "case-plan.json").read_text())
        self.assertEqual(frozen["plan_sha256"], canonical_hash(plan))
        self.assertEqual(frozen, manifest["frozen_selection"])
        for case in manifest["cases"]:
            self.assertEqual(set(case["methods"]), {"raw", "age_projection"})
            clock = json.loads((destination / case["artifact_dir"] / "clock.json").read_text())
            for method in comparison.METHODS:
                record_path = destination / case["methods"][method]["artifacts"]["records"]
                records = json.loads(record_path.read_text())
                self.assertEqual([r["decision"]["decision_time_s"] for r in records], clock)
            self.assertTrue((destination / case["truth_file"]).is_file())

    def test_fresh_runs_reproduce_every_machine_artifact(self):
        path, _ = self.fixture_configuration()
        first = comparison.run(path, self.root / "a")
        second = comparison.run(path, self.root / "b")
        self.assertEqual(first, second)
        for relative in ("manifest.json", *first["artifact_sha256"]):
            self.assertEqual((self.root / "a" / relative).read_bytes(),
                             (self.root / "b" / relative).read_bytes())

    def test_one_failed_method_does_not_disappear_or_stop_later_cases(self):
        path, _ = self.fixture_configuration()
        first = True

        def injected(*args, **kwargs):
            nonlocal first
            if first and kwargs["method"] == "raw":
                first = False
                raise ValueError("controlled raw failure")
            return replay_with_estimator(*args, **kwargs)

        manifest = comparison.run(path, self.root / "failed", method_runner=injected)
        self.assertEqual(manifest["status"], "partial")
        self.assertEqual(len(manifest["cases"]), 56)
        case = manifest["cases"][0]
        self.assertEqual(case["status"], "partial")
        self.assertEqual(case["methods"]["raw"]["status"], "failed")
        self.assertIsNone(case["methods"]["raw"]["score"])
        self.assertIn("controlled raw failure", case["methods"]["raw"]["error"])
        self.assertEqual(case["methods"]["age_projection"]["status"], "complete")
        self.assertTrue(all(c["status"] == "complete" for c in manifest["cases"][1:]))
        raw = manifest["summary"]["development"]["methods"]["raw"]
        self.assertEqual(raw["planned"], 28)
        self.assertEqual(raw["complete"], 27)
        self.assertEqual(raw["planned_positive_count"], 14)
        self.assertEqual(raw["positive_count"], 13)

    def test_preflight_preserves_existing_output_and_rejects_invalid_runner(self):
        path, _ = self.fixture_configuration()
        destination = self.root / "new"
        with self.assertRaises(ValueError):
            comparison.run(path, destination, method_runner=7)
        self.assertFalse(destination.exists())
        destination.mkdir()
        marker = destination / "keep.txt"
        marker.write_text("preserve", encoding="utf-8")
        with self.assertRaises(ValueError):
            comparison.run(path, destination)
        self.assertEqual(marker.read_text(), "preserve")
        with self.assertRaises(ValueError):
            comparison.run(path, comparison.ROOT / "docs" / "never-create")

    def test_shared_input_mutation_fails_the_pair_and_preserves_later_cases(self):
        path, _ = self.fixture_configuration()
        altered = False

        def injected(observations, times, **kwargs):
            nonlocal altered
            if not altered:
                altered = True
                object.__setattr__(observations[0], "gap_m", observations[0].gap_m + 1)
            return replay_with_estimator(observations, times, **kwargs)

        manifest = comparison.run(path, self.root / "mutation", method_runner=injected)
        self.assertEqual(manifest["status"], "partial")
        self.assertEqual(manifest["cases"][0]["status"], "failed")
        self.assertTrue(all(c["status"] == "complete" for c in manifest["cases"][1:]))

    def test_metric_specific_changes_preserve_a_lead_loss_beside_error_win(self):
        case = {
            "reference_contact_time_s": 5.0,
            "methods": {
                "raw": {"status": "complete", "score": {"outcome": "useful", "matched_lead_s": 3.0},
                        "errors": {"gap_mae_m": 1.0, "closing_speed_mae_mps": 0.0}},
                "age_projection": {"status": "complete", "score": {"outcome": "useful", "matched_lead_s": 2.5},
                                   "errors": {"gap_mae_m": 0.5, "closing_speed_mae_mps": 0.0}},
            },
        }
        changes = comparison.pair_changes(case)
        self.assertEqual(changes["gap_mae_m"]["direction"], "win")
        self.assertEqual(changes["closing_speed_mae_mps"]["direction"], "unchanged")
        self.assertEqual(changes["useful_lead_s"]["direction"], "loss")
        self.assertEqual(changes["useful_lead_s"]["delta"], -0.5)


if __name__ == "__main__":
    unittest.main()
