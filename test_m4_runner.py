"""Machine-result integration checks with independent timing fixtures."""

from copy import deepcopy
import csv
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import release_runner
from release_config import ROOT, load_configuration


class ReleaseRunnerTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "outputs").mkdir(exist_ok=True)

        self.temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        self.addCleanup(self.temporary.cleanup)

        self.directory = Path(self.temporary.name)

        self.config = deepcopy(load_configuration("configs/m4-release.json"))

        self.config["scenario_ids"] = [
            "lead_braking_contact",
            "lead_braking_noncontact",
        ]

        self.config["conditions"] = [
            {
                "condition_id": "clean",
                "fault": {"mode": "clean"},
                "seed_bases": [None],
            },
            {
                "condition_id": "latency_1s",
                "fault": {
                    "mode": "latency",
                    "latency_s": 1.0,
                },
                "seed_bases": [None],
            },
        ]

        self.config_path = self.directory / "smoke.json"

        self.config_path.write_text(
            json.dumps(self.config),
            encoding="utf-8",
        )

    def execute(self, name="run", **kwargs):
        return release_runner.run(
            self.config_path,
            self.directory / name,
            **kwargs,
        )

    def test_independent_four_case_smoke_and_five_diagnostics(self):
        result = self.execute()

        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["stage"], "machine-results")
        self.assertEqual(len(result["cases"]), 4)
        self.assertEqual(len(result["regression_cases"]), 5)

        pairs = {
            (row["scenario_id"], row["condition_id"]): row for row in result["cases"]
        }

        expected = {
            ("lead_braking_contact", "clean"): (
                "useful",
                2.0,
            ),
            ("lead_braking_contact", "latency_1s"): (
                "late",
                3.0,
            ),
            ("lead_braking_noncontact", "clean"): (
                "false_warning",
                7.0,
            ),
            ("lead_braking_noncontact", "latency_1s"): (
                "false_warning",
                8.0,
            ),
        }

        for pair, (outcome, first_warning) in expected.items():
            row = pairs[pair]

            self.assertEqual(row["status"], "complete")
            self.assertEqual(
                row["score"]["outcome"],
                outcome,
            )
            self.assertEqual(
                row["score"]["first_warning_time_s"],
                first_warning,
            )

        delayed = pairs[("lead_braking_contact", "latency_1s")]

        self.assertAlmostEqual(
            delayed["score"]["matched_lead_s"],
            0.3166247903554,
            places=9,
        )

        self.assertEqual(
            delayed["errors"]["gap_mae_m"],
            12.5,
        )
        self.assertEqual(
            delayed["errors"]["closing_speed_mae_mps"],
            3.0,
        )
        self.assertEqual(
            delayed["errors"]["fresh_count"],
            5,
        )
        self.assertEqual(
            delayed["errors"]["unavailable_count"],
            1,
        )
        self.assertEqual(
            delayed["errors"]["stale_count"],
            0,
        )

        diagnostics = result["regression_cases"]

        self.assertEqual(
            [row["score"]["outcome"] for row in diagnostics],
            ["useful", "useful", "late", "late", "missed"],
        )

        self.assertEqual(
            [row["score"]["first_warning_time_s"] for row in diagnostics],
            [4.0, 5.0, 5.5, 6.0, None],
        )

        self.assertEqual(
            diagnostics[-1]["counts"]["pending_arrivals"],
            3,
        )

    def test_exported_rows_audit_and_hashes_are_real_evidence(self):
        result = self.execute()
        output = self.directory / "run"

        saved = json.loads((output / "results.json").read_text("utf-8"))
        self.assertEqual(
            saved["cases"],
            result["cases"],
        )

        with (output / "cases.csv").open(
            encoding="utf-8",
            newline="",
        ) as stream:
            table = list(csv.DictReader(stream))

        rows = result["cases"] + result["regression_cases"]

        self.assertEqual(len(table), 9)
        self.assertEqual(
            {row["case_id"] for row in table},
            {row["case_id"] for row in rows},
        )

        for row in rows:
            case_dir = output / "cases" / row["case_id"]

            with (case_dir / "fault-audit.csv").open(
                encoding="utf-8",
                newline="",
            ) as stream:
                audit = list(csv.DictReader(stream))

            self.assertEqual(
                len(audit),
                row["counts"]["source"],
            )

            self.assertEqual(
                json.loads((case_dir / "result.json").read_text("utf-8")),
                row,
            )

        self.assertNotIn(
            "manifest.json",
            result["artifact_sha256"],
        )

        for relative, expected_hash in result["artifact_sha256"].items():
            self.assertEqual(
                release_runner.sha256(output / relative),
                expected_hash,
            )

    def test_case_failure_retains_denominators_and_later_cases(self):
        def fail_one(context, fault, policy):
            if (
                context["fixture"].scenario.scenario_id == "lead_braking_contact"
                and fault.mode == "clean"
            ):
                raise RuntimeError("controlled case failure")

            return release_runner.compute_case(
                context,
                fault,
                policy,
            )

        result = self.execute(case_runner=fail_one)

        self.assertEqual(result["status"], "partial")
        self.assertEqual(len(result["cases"]), 4)

        self.assertEqual(
            sum(row["status"] == "complete" for row in result["cases"]),
            3,
        )

        failed = next(row for row in result["cases"] if row["status"] == "failed")

        self.assertIn(
            "controlled case failure",
            failed["error"],
        )
        self.assertIsNone(failed["score"])
        self.assertIsNone(failed["errors"])
        self.assertIsNone(failed["counts"])

        clean = next(
            group for group in result["summaries"] if group["condition_id"] == "clean"
        )

        self.assertEqual(
            clean["planned"]["positive"],
            1,
        )
        self.assertEqual(
            clean["scored"]["positive"],
            0,
        )
        self.assertIsNone(clean["rates"]["missed"]["value"])

        self.assertTrue(
            all(row["status"] == "complete" for row in result["regression_cases"])
        )

        with patch(
            "release_runner.run",
            return_value=result,
        ):
            self.assertEqual(
                release_runner.main(["--output-dir", "outputs/unused"]),
                1,
            )

    def test_repeated_run_has_identical_saved_bytes(self):
        self.execute("a")
        self.execute("b")

        a = self.directory / "a"
        b = self.directory / "b"

        paths = [path.relative_to(a) for path in a.rglob("*") if path.is_file()]

        self.assertEqual(
            set(paths),
            {path.relative_to(b) for path in b.rglob("*") if path.is_file()},
        )

        for relative in paths:
            self.assertEqual(
                (a / relative).read_bytes(),
                (b / relative).read_bytes(),
                str(relative),
            )

    def test_preflight_rejects_invalid_existing_and_outside_destinations(self):
        existing = self.directory / "existing"
        existing.mkdir()

        marker = existing / "keep.txt"
        marker.write_text("preserve", encoding="utf-8")

        with self.assertRaises(ValueError):
            release_runner.run(
                self.config_path,
                existing,
            )

        self.assertEqual(
            marker.read_text("utf-8"),
            "preserve",
        )

        with self.assertRaises(ValueError):
            release_runner.run(
                self.config_path,
                ROOT / "outside-output-test",
            )

        invalid = deepcopy(self.config)
        invalid["warning"]["threshold_s"] = -1

        self.config_path.write_text(
            json.dumps(invalid),
            encoding="utf-8",
        )

        with self.assertRaises(ValueError):
            self.execute("invalid")

        self.assertFalse((self.directory / "invalid").exists())

    def test_hash_failure_clears_stale_claim_and_updates_results(self):
        with patch(
            "release_runner._artifact_hashes",
            side_effect=OSError("controlled hash failure"),
        ):
            result = self.execute()

        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["artifact_sha256"], {})

        saved = json.loads((self.directory / "run" / "results.json").read_text("utf-8"))

        self.assertEqual(saved["status"], "partial")
        self.assertIn(
            "controlled hash failure",
            saved["error"],
        )

    def test_case_export_failure_stays_failed_and_other_cases_continue(self):
        original = release_runner.write_records

        def fail_export(path, records, record_type):
            if path.parent.name == "case-001" and path.name == "observations.csv":
                raise OSError("controlled export failure")

            return original(
                path,
                records,
                record_type,
            )

        with patch(
            "release_runner.write_records",
            side_effect=fail_export,
        ):
            result = self.execute()

        self.assertEqual(result["status"], "partial")
        self.assertEqual(
            result["cases"][0]["status"],
            "failed",
        )
        self.assertIsNone(result["cases"][0]["score"])
        self.assertIn(
            "controlled export failure",
            result["cases"][0]["error"],
        )

        self.assertTrue(all(row["status"] == "complete" for row in result["cases"][1:]))

    def test_real_cli_and_full_declared_matrix(self):
        output = self.directory / "cli"

        completed = subprocess.run(
            [
                sys.executable,
                str(ROOT / "release_runner.py"),
                "--config",
                str(self.config_path),
                "--output-dir",
                str(output),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )

        self.assertEqual(
            completed.returncode,
            0,
            completed.stdout + completed.stderr,
        )

        full = release_runner.run(
            ROOT / "configs" / "m4-release.json",
            self.directory / "full",
        )

        self.assertEqual(full["status"], "complete")
        self.assertEqual(len(full["cases"]), 76)
        self.assertEqual(
            len(full["regression_cases"]),
            5,
        )

        self.assertTrue(
            all(
                row["status"] == "complete"
                for row in (full["cases"] + full["regression_cases"])
            )
        )
