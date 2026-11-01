"""Offline rendering, evidence validation and CLI regression checks."""

from copy import deepcopy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

import drivecheck
import release_report
import release_runner
from release_config import ROOT, load_configuration


class ReleaseReportTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "outputs").mkdir(exist_ok=True)

        self.temp = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        self.addCleanup(self.temp.cleanup)

        self.base = Path(self.temp.name)

        config = deepcopy(load_configuration("configs/m4-release.json"))

        config["scenario_ids"] = [
            "lead_braking_contact",
            "lead_braking_noncontact",
        ]

        config["conditions"] = [
            {
                "condition_id": "clean",
                "fault": {"mode": "clean"},
                "seed_bases": [None],
            }
        ]

        self.config = self.base / "config.json"
        self.config.write_text(
            json.dumps(config),
            encoding="utf-8",
        )

        self.output = self.base / "run"

        self.machine = release_runner.run(
            self.config,
            self.output,
        )

    @staticmethod
    def stub_plot(path, row, directory):
        # A valid tiny PNG isolates lifecycle tests from plotting cost.
        Image.new(
            "RGB",
            (2, 2),
            "white",
        ).save(path)

    def refresh_machine(self, manifest):
        # Simulate a self-consistent producer error with updated hashes.
        release_runner.write_json(
            self.output / "results.json",
            release_runner._payload(manifest),
        )

        manifest["artifact_sha256"] = release_runner._artifact_hashes(self.output)

        release_runner.write_json(
            self.output / "manifest.json",
            manifest,
        )

    def test_every_case_denominators_links_and_machine_bytes_preserved(self):
        before = (self.output / "manifest.json").read_bytes()

        result = release_report.generate(
            self.output,
            plotter=self.stub_plot,
        )

        self.assertEqual(result["status"], "complete")
        self.assertEqual(
            len(result["plot_case_ids"]),
            7,
        )

        html = (self.output / "report" / "report.html").read_text("utf-8")

        for row in self.machine["cases"] + self.machine["regression_cases"]:
            self.assertIn(
                f"id='{row['case_id']}'",
                html,
            )

        self.assertIn(
            "1/1 (100.0%)",
            html,
        )
        self.assertIn(
            "unavailable alarming data, not stale rejection",
            html,
        )

        observed = release_report.diagnostic_observed(
            self.output,
            self.machine,
        )

        self.assertIn(
            "<td>arrival_time_s</td><td>6.5</td>",
            observed,
        )
        self.assertIn(
            "<td>reason</td><td>ttc_clear</td>",
            observed,
        )

        self.assertGreater(
            release_report.check_links(self.output),
            30,
        )
        self.assertEqual(
            (self.output / "manifest.json").read_bytes(),
            before,
        )

        for relative, expected in result["artifact_sha256"].items():
            self.assertEqual(
                release_report.digest(self.output / relative),
                expected,
            )

    def test_tampered_machine_evidence_is_rejected_before_report_writes(self):
        target = self.output / "cases" / "case-001" / "decisions.csv"

        target.write_bytes(target.read_bytes() + b"tampered")

        with self.assertRaisesRegex(
            ValueError,
            "hash mismatch",
        ):
            release_report.generate(
                self.output,
                plotter=self.stub_plot,
            )

        self.assertFalse((self.output / "report").exists())
        self.assertFalse((self.output / "release-manifest.json").exists())

    def test_consistently_truncated_matrix_is_rejected(self):
        manifest = deepcopy(self.machine)

        removed = manifest["cases"].pop()
        manifest["expected_case_count"] -= 1

        manifest["summaries"] = release_report.summarize(manifest["cases"])

        plan = release_report.read_json(self.output / "plan.json")
        plan = [row for row in plan if row["case_id"] != removed["case_id"]]

        release_runner.write_json(
            self.output / "plan.json",
            plan,
        )

        manifest["plan_sha256"] = release_runner.canonical_hash(plan)

        self.refresh_machine(manifest)

        with self.assertRaisesRegex(
            ValueError,
            "configured matrix coverage",
        ):
            release_report.generate(
                self.output,
                plotter=self.stub_plot,
            )

        self.assertFalse((self.output / "report").exists())

    def test_false_complete_status_is_rejected(self):
        manifest = deepcopy(self.machine)
        manifest["error"] = "controlled run-level failure"

        self.refresh_machine(manifest)

        with self.assertRaisesRegex(
            ValueError,
            "overall machine status",
        ):
            release_report.generate(
                self.output,
                plotter=self.stub_plot,
            )

    def test_rehashed_contradictory_csv_is_rejected(self):
        records = release_report.read_csv(self.output / "cases.csv")

        records[0]["outcome"] = "missed"

        release_runner.write_csv(
            self.output / "cases.csv",
            records,
            list(records[0]),
        )

        self.refresh_machine(deepcopy(self.machine))

        with self.assertRaisesRegex(
            ValueError,
            "CSV case values",
        ):
            release_report.generate(
                self.output,
                plotter=self.stub_plot,
            )

    def test_rehashed_jittered_diagnostic_cannot_be_called_fixed_delay(self):
        manifest = deepcopy(self.machine)

        changed = manifest["regression_cases"][-1]
        changed["fault"]["latency_jitter_s"] = 0.1

        plan = release_report.read_json(self.output / "plan.json")

        planned = next(row for row in plan if row["case_id"] == changed["case_id"])

        planned["fault"] = deepcopy(changed["fault"])

        release_runner.write_json(
            self.output / "plan.json",
            plan,
        )

        manifest["plan_sha256"] = release_runner.canonical_hash(plan)

        release_runner.write_json(
            self.output / "cases" / changed["case_id"] / "result.json",
            changed,
        )

        self.refresh_machine(manifest)

        with self.assertRaisesRegex(
            ValueError,
            "diagnostic contract",
        ):
            release_report.generate(
                self.output,
                plotter=self.stub_plot,
            )

    def test_failed_case_text_is_escaped_and_stays_unscored(self):
        other = self.base / "partial"

        def fail(context, fault, policy):
            if context["fixture"].scenario.scenario_id == "lead_braking_contact":
                raise RuntimeError("<script>bad</script>")

            return release_runner.compute_case(
                context,
                fault,
                policy,
            )

        release_runner.run(
            self.config,
            other,
            case_runner=fail,
        )

        result = release_report.generate(
            other,
            plotter=self.stub_plot,
        )

        self.assertEqual(result["status"], "partial")

        html = (other / "report" / "report.html").read_text("utf-8")

        self.assertIn(
            "&lt;script&gt;bad&lt;/script&gt;",
            html,
        )
        self.assertNotIn(
            "<script>bad</script>",
            html,
        )
        self.assertIn(
            "0/0 (N/A)",
            html,
        )

    def test_plot_html_and_hash_failures_cannot_claim_complete_package(self):
        targets = (
            "plot_case",
            "write_html",
            "package_hashes",
        )

        for index, target in enumerate(targets):
            destination = self.base / f"failure-{index}"

            release_runner.run(
                self.config,
                destination,
            )

            with patch(
                f"release_report.{target}",
                side_effect=RuntimeError("controlled report failure"),
            ):
                result = release_report.generate(
                    destination,
                    plotter=(None if target == "plot_case" else self.stub_plot),
                )

            self.assertEqual(
                result["status"],
                "partial",
            )
            self.assertEqual(
                result["artifact_sha256"],
                {},
            )
            self.assertIn(
                "controlled report failure",
                result["error"],
            )

            machine = json.loads((destination / "manifest.json").read_text("utf-8"))

            self.assertEqual(
                machine["status"],
                "complete",
            )

    def test_real_plot_and_movable_contained_bundle(self):
        def one_real(path, row, directory):
            if row["case_id"] == "case-001":
                release_report.plot_case(
                    path,
                    row,
                    directory,
                )
            else:
                self.stub_plot(
                    path,
                    row,
                    directory,
                )

        release_report.generate(
            self.output,
            plotter=one_real,
        )

        with Image.open(self.output / "report" / "case-001.png") as image:
            self.assertGreater(
                image.width,
                1000,
            )

        copied = self.base / "copied-run"

        shutil.copytree(
            self.output,
            copied,
        )

        self.assertGreater(
            release_report.check_links(copied),
            30,
        )

    def test_cli_dispatch_keeps_m2_and_executes_m4(self):
        with patch(
            "drivecheck.run",
            return_value={
                "status": "complete",
                "cases": [],
                "expected_case_count": 0,
                "error": None,
            },
        ):
            self.assertEqual(
                drivecheck.main(
                    [
                        "--config",
                        "configs/m2-experiment.json",
                        "--output-dir",
                        str(self.base / "m2"),
                    ]
                ),
                0,
            )

        destination = self.base / "cli"

        with patch(
            "release_report.plot_case",
            side_effect=self.stub_plot,
        ):
            self.assertEqual(
                drivecheck.main(
                    [
                        "--config",
                        str(self.config),
                        "--output-dir",
                        str(destination),
                    ]
                ),
                0,
            )

        with patch(
            "drivecheck.generate",
            side_effect=RuntimeError("controlled packaging failure"),
        ):
            self.assertEqual(
                drivecheck.main(
                    [
                        "--config",
                        str(self.config),
                        "--output-dir",
                        str(self.base / "cli-failed"),
                    ]
                ),
                1,
            )

        invalid = self.base / "unknown.json"

        invalid.write_text(
            '{"schema_version":"unknown"}',
            encoding="utf-8",
        )

        untouched = self.base / "untouched"

        self.assertEqual(
            drivecheck.main(
                [
                    "--config",
                    str(invalid),
                    "--output-dir",
                    str(untouched),
                ]
            ),
            2,
        )

        self.assertFalse(untouched.exists())
