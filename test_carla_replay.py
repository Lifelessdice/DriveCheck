"""Literal imported-replay outcomes and input-preserving export boundaries."""

from contextlib import redirect_stderr, redirect_stdout
import csv
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import carla_replay
from evaluation import aligned_errors


ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG = ROOT / "configs" / "carla-replay.json"
CONTACT = ROOT / "examples" / "carla" / "contact.json"
NONCONTACT = ROOT / "examples" / "carla" / "noncontact.json"


class CarlaReplayTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "outputs").mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.configuration = json.loads(DEFAULT_CONFIG.read_text("utf-8"))
        self.count = 0

    def config(self):
        path = self.root / "configuration.json"
        path.write_text(json.dumps(self.configuration, indent=2) + "\n", encoding="utf-8")
        return path

    def run_fixture(self, source=CONTACT):
        self.count += 1
        destination = self.root / f"run-{self.count}"
        result = carla_replay.run(source, self.config(), destination)
        return result, destination

    def custom_input(self, payload):
        path = self.root / "export.json"
        path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
        return path

    def test_literal_contact_latency_warns_raw_late_projected_usefully(self):
        before = CONTACT.read_bytes()
        result, destination = self.run_fixture()
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["reference_contact_time_s"], 2.0)
        raw, projected = (result["methods"][name] for name in ("raw", "age_projection"))
        self.assertEqual(raw["score"]["first_warning_time_s"], 2.0)
        self.assertEqual(raw["score"]["outcome"], "late")
        self.assertEqual(raw["score"]["matched_lead_s"], 0.0)
        self.assertEqual(projected["score"]["first_warning_time_s"], 1.0)
        self.assertEqual(projected["score"]["outcome"], "useful")
        self.assertEqual(projected["score"]["matched_lead_s"], 1.0)
        self.assertEqual(raw["errors"]["gap_mae_m"], 5.0)
        self.assertEqual(projected["errors"]["gap_mae_m"], 0.0)
        for method in (raw, projected):
            self.assertEqual(method["errors"]["fresh_count"], 2)
            self.assertEqual(method["errors"]["unavailable_count"], 1)
            self.assertEqual(method["counts"]["beyond_horizon_arrival_count"], 1)
        self.assertEqual(CONTACT.read_bytes(), before)
        self.assertEqual((destination / "source-export.json").read_bytes(), before)
        self.assertIn("synthetic-contract-fixture", (destination / "report.html").read_text("utf-8"))
        self.assertIn("not radar", (destination / "report.html").read_text("utf-8"))
        with (destination / "frame-map.csv").open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual([int(row["source_frame_id"]) for row in rows], [100, 101, 102])
        self.assertEqual([float(row["source_elapsed_seconds"]) for row in rows], [10, 11, 12])
        self.assertEqual([float(row["time_s"]) for row in rows], [0, 1, 2])
        for name, expected in result["artifact_sha256"].items():
            self.assertEqual(hashlib.sha256((destination / name).read_bytes()).hexdigest(), expected)

    def test_literal_noncontact_is_clear_for_both_methods(self):
        result, _ = self.run_fixture(NONCONTACT)
        self.assertEqual(result["status"], "complete")
        self.assertIsNone(result["reference_contact_time_s"])
        for method in result["methods"].values():
            self.assertEqual(method["score"]["outcome"], "clear_negative")
            self.assertIsNone(method["score"]["first_warning_time_s"])
            self.assertEqual(method["errors"]["closing_speed_mae_mps"], 0.0)

    def test_collision_reference_is_not_inferred_from_zero_geometric_gap(self):
        data = json.loads(CONTACT.read_text("utf-8"))
        data["collisions"] = []
        result, _ = self.run_fixture(self.custom_input(data))
        self.assertIsNone(result["reference_contact_time_s"])
        self.assertEqual(result["methods"]["raw"]["score"]["outcome"], "false_warning")
        self.assertEqual(result["methods"]["age_projection"]["score"]["outcome"], "false_warning")

    def test_empty_dropout_stream_is_missing_not_zero_error(self):
        self.configuration["fault"] = {"mode": "dropout", "dropout_probability": 1.0}
        result, destination = self.run_fixture()
        self.assertEqual(result["status"], "complete")
        for method in result["methods"].values():
            self.assertEqual(method["score"]["outcome"], "missed")
            self.assertEqual(method["errors"]["unavailable_count"], 3)
            self.assertEqual(method["errors"]["fresh_count"], 0)
            self.assertIsNone(method["errors"]["gap_mae_m"])
        with (destination / "observations.csv").open(encoding="utf-8", newline="") as stream:
            self.assertEqual(list(csv.DictReader(stream)), [])

    def test_stale_readings_are_rejected_before_projection(self):
        self.configuration["warning"]["max_age_s"] = 0.5
        result, _ = self.run_fixture()
        for method in result["methods"].values():
            self.assertEqual(method["score"]["outcome"], "missed")
            self.assertEqual(method["errors"]["stale_count"], 2)
            self.assertIsNone(method["errors"]["gap_mae_m"])

    def test_irregular_arrival_clock_uses_imported_interpolation_for_errors(self):
        data = json.loads(CONTACT.read_text("utf-8"))
        data["provenance"]["fixed_delta_seconds"] = None
        for frame, timestamp in zip(data["frames"], (10.0, 10.5, 12.0)):
            frame["elapsed_seconds"] = timestamp
        self.configuration["fault"]["latency_s"] = 0.25
        with patch.object(carla_replay, "aligned_errors", wraps=aligned_errors) as evaluator:
            result, destination = self.run_fixture(self.custom_input(data))
        self.assertEqual(result["status"], "complete")
        self.assertEqual(json.loads((destination / "clock.json").read_text("utf-8")),
                         [0, 0.25, 0.5, 0.75, 2.0])
        self.assertEqual(evaluator.call_count, 2)
        for call in evaluator.call_args_list:
            self.assertEqual(call.kwargs["truth_at_time"](0.25).gap_m, 7.5)

    def test_one_frame_zero_horizon_remains_a_valid_replay(self):
        data = json.loads(NONCONTACT.read_text("utf-8"))
        data["frames"] = data["frames"][:1]
        result, _ = self.run_fixture(self.custom_input(data))
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["horizon_s"], 0)
        for method in result["methods"].values():
            self.assertEqual(method["counts"]["decision_count"], 1)
            self.assertEqual(method["errors"]["unavailable_count"], 1)

    def test_configuration_rejects_unknown_duplicate_invalid_and_combined_settings(self):
        original = json.dumps(self.configuration)
        invalid = []
        for methods in ([], ["raw", "raw"], ["unknown"], "raw", [["raw"]]):
            data = json.loads(original)
            data["methods"] = methods
            invalid.append(json.dumps(data).encode())
        for key, value in (("extra", 1), ("schema_version", "unknown"), ("mapping", [])):
            data = json.loads(original)
            data[key] = value
            invalid.append(json.dumps(data).encode())
        data = json.loads(original)
        data["warning"]["warning_threshold_s"] = True
        invalid.append(json.dumps(data).encode())
        data = json.loads(original)
        data["fault"]["gap_sigma_m"] = 1
        invalid.append(json.dumps(data).encode())
        invalid.append(original.replace('"methods":', '"methods": [], "methods":').encode())
        invalid.append(original.replace('"max_age_s": 1.25', '"max_age_s": NaN').encode())
        invalid.append(original.replace('"max_age_s": 1.25', '"max_age_s": 1e999').encode())
        for content in invalid:
            with self.subTest(content=content[:100]):
                with self.assertRaises((ValueError, TypeError)):
                    carla_replay.load_configuration(content)

    def test_bad_input_or_configuration_never_creates_an_output(self):
        bad = self.custom_input({"schema_version": "unknown"})
        before = bad.read_bytes()
        destination = self.root / "bad"
        with self.assertRaises(ValueError):
            carla_replay.run(bad, self.config(), destination)
        self.assertFalse(destination.exists())
        self.assertEqual(bad.read_bytes(), before)
        config = self.config()
        config.write_bytes(b'{"schema_version":"unknown"}')
        with self.assertRaises(ValueError):
            carla_replay.run(CONTACT, config, destination)
        self.assertFalse(destination.exists())

    def test_existing_destination_and_input_ancestor_are_preserved(self):
        destination = self.root / "existing"
        destination.mkdir()
        sentinel = destination / "keep.txt"
        sentinel.write_bytes(b"keep prior work")
        for candidate in (destination, self.root, ROOT / "outputs"):
            with self.subTest(destination=candidate):
                with self.assertRaises(ValueError):
                    carla_replay.run(CONTACT, self.config(), candidate)
        self.assertEqual(sentinel.read_bytes(), b"keep prior work")

    def test_source_and_destination_must_stay_inside_unredirected_project_paths(self):
        for source, output in ((ROOT.parent / "not-a-project-input.json", self.root / "new"),
                               (CONTACT, ROOT / "not-an-output"),
                               (CONTACT, ROOT.parent / "not-a-project-output")):
            with self.subTest(source=source, output=output):
                with self.assertRaises(ValueError):
                    carla_replay.run(source, self.config(), output)

    def test_input_symlink_is_rejected_before_writes_when_supported(self):
        alias = self.root / "linked-export.json"
        try:
            alias.symlink_to(CONTACT)
        except OSError:
            self.skipTest("symbolic-link creation unavailable")
        destination = self.root / "linked-out"
        with self.assertRaisesRegex(ValueError, "redirect"):
            carla_replay.run(alias, self.config(), destination)
        self.assertFalse(destination.exists())

    def test_one_method_failure_is_retained_while_the_other_completes(self):
        original = carla_replay.replay_with_estimator

        def controlled(*args, **kwargs):
            if kwargs["method"] == "raw":
                raise RuntimeError("controlled raw failure")
            return original(*args, **kwargs)

        with patch.object(carla_replay, "replay_with_estimator", side_effect=controlled):
            result, destination = self.run_fixture()
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["methods"]["raw"]["status"], "failed")
        self.assertIn("controlled raw failure", result["methods"]["raw"]["error"])
        self.assertEqual(result["methods"]["age_projection"]["score"]["outcome"], "useful")
        self.assertEqual(json.loads((destination / "results.json").read_text("utf-8"))["status"], "partial")

    def test_shared_failure_retains_all_requested_methods_and_failed_report(self):
        with patch.object(carla_replay, "inject_faults", side_effect=RuntimeError("controlled input failure")):
            result, destination = self.run_fixture()
        self.assertEqual(result["status"], "failed")
        self.assertEqual(set(result["methods"]), {"raw", "age_projection"})
        self.assertTrue(all(row["status"] == "failed" for row in result["methods"].values()))
        self.assertIn("controlled input failure", result["error"])
        self.assertTrue((destination / "report.html").is_file())

    def test_plot_failure_keeps_complete_scores_but_labels_run_partial(self):
        with patch.object(carla_replay, "save_plot", side_effect=RuntimeError("controlled plot failure")):
            result, destination = self.run_fixture()
        self.assertEqual(result["status"], "partial")
        self.assertTrue(all(row["status"] == "complete" for row in result["methods"].values()))
        self.assertIn("controlled plot failure", result["plot_error"])
        self.assertEqual(json.loads((destination / "results.json").read_text("utf-8"))["status"], "partial")

    def test_report_failure_updates_final_results_and_manifest_consistently(self):
        with patch.object(carla_replay, "save_report", side_effect=OSError("controlled report failure")):
            result, destination = self.run_fixture()
        saved = json.loads((destination / "results.json").read_text("utf-8"))
        manifest = json.loads((destination / "manifest.json").read_text("utf-8"))
        self.assertEqual(result["status"], "partial")
        self.assertEqual(saved["status"], manifest["status"])
        self.assertEqual(saved["error"], manifest["error"])
        self.assertIn("controlled report failure", saved["error"])

    def test_repeated_runs_have_equal_artifacts_and_unchanged_inputs(self):
        config = self.config()
        before = {path: path.read_bytes() for path in (CONTACT, NONCONTACT, config)}
        first, _ = self.run_fixture()
        second, _ = self.run_fixture()
        self.assertEqual(first, second)
        for path, content in before.items():
            self.assertEqual(path.read_bytes(), content)

    def test_cli_roundtrip_and_nonzero_preflight_and_partial_statuses(self):
        destination = self.root / "cli"
        result = subprocess.run([sys.executable, "-E", "-s", str(ROOT / "carla_replay.py"),
            "--input", str(NONCONTACT), "--config", str(self.config()),
            "--output-dir", str(destination)], cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("complete", result.stdout)
        self.assertTrue((destination / "report.html").is_file())
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(carla_replay.main(["--input", str(CONTACT), "--config", str(self.config()),
                                               "--output-dir", str(destination)]), 2)
            with patch.object(carla_replay, "run", return_value={"status": "partial", "methods": {"raw": {}}}):
                self.assertEqual(carla_replay.main(["--input", str(CONTACT), "--config", str(self.config()),
                    "--output-dir", str(self.root / "partial-cli")]), 1)


if __name__ == "__main__":
    unittest.main()
