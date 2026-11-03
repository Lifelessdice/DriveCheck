"""Offline comparison completeness, escaping, hash binding and CLI status checks."""

from copy import deepcopy
import csv
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from contextlib import redirect_stderr, redirect_stdout

import c1_compare
from c1_report import (
    digest, group_summary, load_machine, metric_changes, read_json, render,
    selected_plots, write_json,
)
from m1 import ROOT


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def fixture(directory, *, failed=False):
    cases = []
    for index, positive in enumerate((True, False), 1):
        case_id = f"evaluation-{index:03d}"
        folder = directory / "cases" / case_id
        folder.mkdir(parents=True)
        truth = [{"time_s": t, "gap_m": 10 - 5 * t, "closing_speed_mps": 5}
                 for t in (0, 1, 2)]
        observations = [{"measurement_time_s": t, "arrival_time_s": t,
                         "gap_m": 10 - 5 * t, "closing_speed_mps": 5}
                        for t in (0, 1, 2)]
        write_csv(folder / "truth.csv", truth)
        write_csv(folder / "observations.csv", observations)
        case = {
            "case_id": case_id, "split": "evaluation", "scenario_id": f"fixture_{index}",
            "family": "synthetic", "condition_id": "clean", "seed_base": None,
            "reference_contact_time_s": 2.0 if positive else None,
            "horizon_s": 2.0, "artifact_dir": f"cases/{case_id}", "status": "complete",
            "policy": {"warning_threshold_s": 1.0, "max_age_s": 1.25,
                       "pre_event_window_s": 2.0, "minimum_useful_lead_s": 1.0},
            "configuration": {}, "fault": {}, "methods": {},
        }
        for method in ("raw", "age_projection"):
            decisions = [{"decision_time_s": t, "gap_m": 10 - 5 * t,
                          "closing_speed_mps": 5, "observation_age_s": 0,
                          "ttc_s": 2 - t, "is_warning": t >= 1,
                          "reason": "ttc_clear" if t == 0 else "ttc_warning"}
                         for t in (0, 1, 2)]
            write_csv(folder / f"{method}-decisions.csv", decisions)
            write_json(folder / f"{method}-records.json", [])
            case["methods"][method] = {
                "status": "complete", "error": None,
                "score": {"outcome": "useful" if positive else "false_warning",
                          "first_warning_time_s": 1.0,
                          "matched_lead_s": 1.0 if positive else None},
                "errors": {"gap_mae_m": 0.0, "closing_speed_mae_mps": 0.0,
                           "fresh_count": 3, "unavailable_count": 0, "stale_count": 0},
                "artifacts": {"decisions": f"cases/{case_id}/{method}-decisions.csv",
                              "records": f"cases/{case_id}/{method}-records.json"},
            }
        if failed and index == 2:
            case["status"] = "partial"
            case["methods"]["age_projection"].update(
                status="failed", score=None, errors=None, artifacts={},
                error="<script>alert('failure')</script>",
            )
        write_json(folder / "metrics.json", case)
        cases.append(case)
    manifest = {"schema": "drivecheck.c1.v1", "status": "partial" if failed else "complete",
                "cases": cases, "summary": {}, "config": {}, "config_sha256": "fixture",
                "frozen_selection": {}, "source_sha256": {}}
    write_json(directory / "case-plan.json", [
        {key: value for key, value in case.items() if key not in {"methods", "status"}}
        for case in cases])
    manifest["artifact_sha256"] = {
        path.relative_to(directory).as_posix(): digest(path)
        for path in directory.rglob("*") if path.is_file()}
    write_json(directory / "manifest.json", manifest)
    return manifest


class C1ReportTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "outputs").mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        self.directory = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def test_partial_rows_escaped_and_evaluated_denominators_retained(self):
        manifest = fixture(self.directory, failed=True)
        before = (self.directory / "manifest.json").read_bytes()
        with patch("c1_report.selected_plots", return_value=[]):
            package = render(self.directory)
        html = (self.directory / "report" / "report.html").read_text("utf-8")
        self.assertEqual(package["status"], "partial")
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<script>", html)
        self.assertIn("evaluation-001", html)
        self.assertIn("evaluation-002", html)
        self.assertIn("age_projection / failed", html)
        rows = [row for row in group_summary(manifest["cases"]) if row["condition"] == "ALL"]
        raw, alternative = rows
        self.assertEqual((raw["evaluated_negative"], raw["false_warning"]), (1, 1))
        self.assertEqual((alternative["planned_negative"], alternative["evaluated_negative"]), (1, 0))
        self.assertEqual(alternative["failed_or_partial"], 1)
        self.assertEqual((self.directory / "manifest.json").read_bytes(), before)

    def test_real_plot_package_hashes_and_rerender_protection(self):
        fixture(self.directory)
        package = render(self.directory)
        self.assertEqual(package["status"], "complete")
        self.assertTrue(package["plot_selection"])
        self.assertEqual(package["machine_manifest_sha256"], digest(self.directory / "manifest.json"))
        for relative, expected in package["artifact_sha256"].items():
            self.assertEqual(digest(self.directory / relative), expected)
        with self.assertRaises(ValueError):
            render(self.directory)

    def test_missing_method_and_false_completion_are_rejected(self):
        manifest = fixture(self.directory, failed=True)
        manifest["status"] = "complete"
        write_json(self.directory / "manifest.json", manifest)
        with self.assertRaises(ValueError):
            load_machine(self.directory)
        manifest["status"] = "partial"
        del manifest["cases"][0]["methods"]["raw"]
        write_json(self.directory / "manifest.json", manifest)
        with self.assertRaises(ValueError):
            load_machine(self.directory)

    def test_frozen_inventory_truncation_and_unlisted_files_are_rejected(self):
        manifest = fixture(self.directory)
        original = deepcopy(manifest)
        manifest["cases"].pop()
        write_json(self.directory / "manifest.json", manifest)
        with self.assertRaises(ValueError):
            load_machine(self.directory)
        write_json(self.directory / "manifest.json", original)
        (self.directory / "unlisted.txt").write_text("extra", encoding="utf-8")
        with self.assertRaises(ValueError):
            load_machine(self.directory)

    def test_tampered_evidence_and_path_escape_are_rejected(self):
        manifest = fixture(self.directory)
        target = self.directory / "cases" / "evaluation-001" / "truth.csv"
        original = target.read_bytes()
        target.write_bytes(original + b"tampered")
        with self.assertRaises(ValueError):
            load_machine(self.directory)
        target.write_bytes(original)
        manifest["artifact_sha256"]["../escape"] = "invalid"
        write_json(self.directory / "manifest.json", manifest)
        with self.assertRaises(ValueError):
            load_machine(self.directory)

    def test_metric_directions_use_core_tolerance_and_show_losses(self):
        case = fixture(self.directory)["cases"][0]
        case["methods"]["age_projection"]["errors"]["gap_mae_m"] = 1e-10
        self.assertEqual(metric_changes(case)["gap_mae_m"], "loss")
        case["methods"]["age_projection"]["errors"]["gap_mae_m"] = 1e-13
        self.assertEqual(metric_changes(case)["gap_mae_m"], "unchanged")

    def test_plot_selection_retains_warning_loss_without_gap_error_loss(self):
        cases = fixture(self.directory)["cases"]
        negative = cases[1]
        negative["methods"]["raw"]["score"].update(
            outcome="clear_negative", first_warning_time_s=None,
        )
        negative["methods"]["raw"]["errors"]["gap_mae_m"] = 2.0
        negative["methods"]["age_projection"]["errors"]["gap_mae_m"] = 1.0
        selection = selected_plots(cases)
        self.assertEqual(selection[0][0], "First evaluation false-warning regression")
        self.assertIs(selection[0][1], negative)
        self.assertIs(selection[1][1], cases[0])
        self.assertEqual(metric_changes(negative)["gap_mae_m"], "win")
        self.assertEqual(metric_changes(negative)["false-warning episode"], "loss")

        other = deepcopy(cases)
        other[1]["methods"]["raw"]["score"]["outcome"] = "false_warning"
        other[0]["methods"]["age_projection"]["score"].update(
            outcome="late", matched_lead_s=0.25,
        )
        alternate = selected_plots(other)
        self.assertEqual(alternate[0][0], "First evaluation loss on another reported metric")
        self.assertIs(alternate[0][1], other[0])

    def test_render_failure_records_failed_package(self):
        fixture(self.directory)
        with patch("c1_report.plot_case", side_effect=RuntimeError("plot failed")):
            with self.assertRaises(RuntimeError):
                render(self.directory)
        package = read_json(self.directory / "report-manifest.json")
        self.assertEqual(package["status"], "failed")
        self.assertIn("plot failed", package["error"])

    def test_cli_status_preserves_input_runtime_and_partial_failures(self):
        arguments = ["--config", "configs/c1-comparison.json", "--output-dir", str(self.directory)]
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            with patch.object(c1_compare, "run", return_value={"status": "complete"}), \
                    patch.object(c1_compare, "render", return_value={"status": "complete"}):
                self.assertEqual(c1_compare.main(arguments), 0)
            with patch.object(c1_compare, "run", return_value={"status": "partial"}), \
                    patch.object(c1_compare, "render", return_value={"status": "partial"}):
                self.assertEqual(c1_compare.main(arguments), 1)
            with patch.object(c1_compare, "run", side_effect=ValueError("bad config")):
                with self.assertRaises(SystemExit) as error:
                    c1_compare.main(arguments)
                self.assertEqual(error.exception.code, 2)
            with patch.object(c1_compare, "run", return_value={"status": "complete"}), \
                    patch.object(c1_compare, "render", side_effect=RuntimeError("render failed")):
                self.assertEqual(c1_compare.main(arguments), 1)


if __name__ == "__main__":
    unittest.main()
