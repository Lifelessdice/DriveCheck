"""Acceptance checks for the integrated M3 study."""

import contextlib
import csv
import io
import json
import tempfile
import unittest
from dataclasses import replace
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch

from PIL import Image

import m3_study as study


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def tiny_plot(path, *args):
    """Use a small image for export-orchestration tests."""
    Image.new("RGB", (8, 8), "white").save(path)


class LocalLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.targets = []

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in {"href", "src"} and value:
                self.targets.append(value)


class StudyTests(unittest.TestCase):
    def setUp(self):
        output_root = study.ROOT / "outputs"
        output_root.mkdir(exist_ok=True)

        self.temporary = tempfile.TemporaryDirectory(
            dir=output_root,
            prefix="m3-tests-",
        )
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)

    def run_study(self, name, **kwargs):
        return study.run(
            self.base / name,
            plotter=tiny_plot,
            **kwargs,
        )

    def test_plan_profiles_and_policies(self):
        contexts, plan = study.prepare(100)
        matrix = [entry[3] for entry in plan if entry[3]["section"] == "matrix"]
        regression = [entry[3] for entry in plan if entry[3]["section"] == "regression"]

        self.assertEqual(len(contexts), 5)
        self.assertEqual(len(matrix), 28)
        self.assertEqual(len(regression), 5)
        self.assertEqual(
            len({entry[3]["case_id"] for entry in plan}),
            33,
        )
        self.assertEqual(
            {row["family"] for row in matrix},
            {"lead_braking", "stop_and_go"},
        )

        for row in matrix:
            self.assertEqual(
                row["policy"],
                study.MATRIX_POLICY,
            )
            self.assertEqual(row["fault"]["gap_seed"], 101)
            self.assertEqual(row["fault"]["dropout_seed"], 104)

        for row in regression:
            self.assertEqual(
                row["policy"]["warning_threshold_s"],
                2.0,
            )
            self.assertEqual(
                row["policy"]["decision_clock"],
                "fixed 0.5 s",
            )
            self.assertEqual(
                row["reference_contact_time_s"],
                6.0,
            )

        profiles = study.profiles(200)
        self.assertEqual(len(profiles), 7)
        self.assertEqual(profiles["noise_low"].gap_seed, 201)
        self.assertEqual(
            profiles["dropout_strong"].dropout_probability,
            0.4,
        )

    def test_exports_repeat_and_readback(self):
        first = self.run_study("first")
        second = self.run_study("second")
        first_dir = self.base / "first"
        second_dir = self.base / "second"

        self.assertEqual(first["status"], "complete")
        self.assertEqual(second["status"], "complete")
        self.assertEqual(len(first["cases"]), 28)
        self.assertEqual(len(first["regression_cases"]), 5)

        rows = first["cases"] + first["regression_cases"]
        self.assertTrue(all(row["status"] == "complete" for row in rows))

        for group in first["summaries"]:
            self.assertEqual(
                group["planned"],
                {"positive": 2, "negative": 2},
            )
            self.assertEqual(group["scored"], group["planned"])
            self.assertEqual(
                group["unscored"],
                {"positive": 0, "negative": 0},
            )

        self.assertEqual(
            [row["score"]["outcome"] for row in first["regression_cases"]],
            ["useful", "useful", "late", "late", "missed"],
        )
        self.assertEqual(
            [row["score"]["first_warning_time_s"] for row in first["regression_cases"]],
            [4.0, 5.0, 5.5, 6.0, None],
        )

        clean = {
            row["scenario_id"]: row["score"]
            for row in first["cases"]
            if row["condition_id"] == "clean"
        }
        expected_clean = {
            "lead_braking_contact": (2.0, "useful"),
            "lead_braking_noncontact": (7.0, "false_warning"),
            "stop_and_go_contact": (2.0, "useful"),
            "stop_and_go_noncontact": (3.0, "false_warning"),
        }

        for scenario_id, (time, outcome) in expected_clean.items():
            self.assertEqual(
                clean[scenario_id]["first_warning_time_s"],
                time,
            )
            self.assertEqual(
                clean[scenario_id]["outcome"],
                outcome,
            )

        for relative, expected_hash in first["artifact_sha256"].items():
            path = first_dir / relative
            self.assertTrue(path.is_file())
            self.assertEqual(study.sha256(path), expected_hash)

            if path.suffix in {".json", ".csv"}:
                self.assertEqual(
                    path.read_bytes(),
                    (second_dir / relative).read_bytes(),
                    relative,
                )

        self.assertEqual(
            first["configuration_sha256"],
            study.canonical_hash(first["configuration"]),
        )

        for name, expected_hash in first["provenance"]["source_sha256"].items():
            self.assertEqual(
                study.sha256(study.ROOT / name),
                expected_hash,
            )

        with (first_dir / "cases.csv").open(
            encoding="utf-8",
            newline="",
        ) as stream:
            exported = list(csv.DictReader(stream))

        self.assertEqual(len(exported), 33)
        self.assertEqual(
            {row["case_id"] for row in exported},
            {row["case_id"] for row in rows},
        )

        for scenario_id in {row["scenario_id"] for row in first["cases"]}:
            hashes = {
                row["truth_sha256"]
                for row in first["cases"]
                if row["scenario_id"] == scenario_id
            }
            self.assertEqual(len(hashes), 1)

        parser = LocalLinks()
        parser.feed((first_dir / "report.html").read_text(encoding="utf-8"))
        self.assertTrue(parser.targets)

        for target in parser.targets:
            resolved = (first_dir / target).resolve()
            self.assertTrue(resolved.is_relative_to(first_dir))
            self.assertTrue(resolved.is_file(), target)

        figures = list(first_dir.rglob("timeline.png"))
        self.assertEqual(len(figures), 12)

        for path in figures:
            with Image.open(path) as image:
                image.verify()

    def test_real_plots_for_both_families(self):
        _, plan = study.prepare()
        chosen = [
            entry
            for entry in plan
            if entry[3]["condition_id"] == "clean"
            and entry[3]["reference_contact_time_s"] is not None
            and entry[3]["section"] == "matrix"
        ]
        self.assertEqual(len(chosen), 2)

        for context, fault, policy, row in chosen:
            data = study.compute_case(context, fault, policy)
            path = self.base / f"{row['scenario_id']}.png"

            study.save_timeline(
                path,
                context,
                data,
                policy,
                row["scenario_id"],
            )

            with Image.open(path) as image:
                self.assertGreaterEqual(image.width, 800)
                image.verify()

    def test_case_failure_and_cli_status(self):
        original = study.compute_case

        def fail_one(context, fault, policy):
            scenario_id = context["fixture"].scenario.scenario_id

            if (
                scenario_id == "lead_braking_contact"
                and fault.mode == "noise"
                and fault.gap_sigma_m == 0.2
            ):
                raise RuntimeError("injected case failure")

            return original(context, fault, policy)

        with patch.object(
            study,
            "compute_case",
            side_effect=fail_one,
        ):
            manifest = self.run_study("case-failure")

        rows = manifest["cases"] + manifest["regression_cases"]
        failed = [row for row in rows if row["status"] == "failed"]

        self.assertEqual(manifest["status"], "partial")
        self.assertEqual(len(rows), 33)
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0]["case_id"], "case-002")
        self.assertIsNone(failed[0]["score"])

        group = next(
            item
            for item in manifest["summaries"]
            if item["condition_id"] == "noise_low"
        )
        self.assertEqual(
            group["scored"],
            {"positive": 1, "negative": 2},
        )
        self.assertEqual(
            group["unscored"],
            {"positive": 1, "negative": 0},
        )
        self.assertIn("case-002", group["unscored_case_ids"])

        report = (self.base / "case-failure" / "report.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("injected case failure", report)

        with patch.object(study, "run", return_value=manifest):
            with contextlib.redirect_stdout(io.StringIO()):
                exit_code = study.main(
                    [
                        "--output-dir",
                        str(self.base / "unused"),
                    ]
                )

        self.assertEqual(exit_code, 1)

    def test_report_failure_keeps_machine_data(self):
        with patch.object(
            study,
            "write_report",
            side_effect=RuntimeError("injected report failure"),
        ):
            manifest = self.run_study("report-failure")

        destination = self.base / "report-failure"
        summary = read_json(destination / "study-summary.json")

        self.assertEqual(manifest["status"], "partial")
        self.assertEqual(summary["status"], "partial")
        self.assertIn(
            "injected report failure",
            summary["error"],
        )
        self.assertTrue(
            all(
                row["status"] == "complete"
                for row in summary["cases"] + summary["regression_cases"]
            )
        )
        self.assertTrue((destination / "cases.csv").is_file())
        self.assertNotIn(
            "report.html",
            manifest["artifact_sha256"],
        )

        for relative, expected_hash in manifest["artifact_sha256"].items():
            self.assertEqual(
                study.sha256(destination / relative),
                expected_hash,
            )

    def test_preflight_guards(self):
        existing = self.base / "existing"
        existing.mkdir()
        sentinel = existing / "keep.txt"
        sentinel.write_text("preserve", encoding="utf-8")

        with self.assertRaises(ValueError):
            study.run(existing, plotter=tiny_plot)

        self.assertEqual(
            sentinel.read_text(encoding="utf-8"),
            "preserve",
        )

        with self.assertRaises(ValueError):
            study.run(
                study.ROOT / "forbidden-m3-study",
                plotter=tiny_plot,
            )

        for index, kwargs in enumerate(
            (
                {"seed_base": -1},
                {"seed_base": True},
                {"all_plots": "yes"},
                {"plotter": 42},
            )
        ):
            destination = self.base / f"invalid-{index}"

            with self.assertRaises(ValueError):
                study.run(destination, **kwargs)

            self.assertFalse(destination.exists())

        fixtures = study.stop_go_fixtures()
        broken = [
            replace(
                fixtures[0],
                reference_final_gap_m=999.0,
            ),
            fixtures[1],
        ]
        destination = self.base / "bad-reference"

        with patch.object(
            study,
            "stop_go_fixtures",
            return_value=broken,
        ):
            with self.assertRaises(ValueError):
                study.run(destination, plotter=tiny_plot)

        self.assertFalse(destination.exists())

        destination = self.base / "missing-source"

        with patch.object(
            study,
            "SOURCE_FILES",
            study.SOURCE_FILES + ("missing-m3-source.py",),
        ):
            with self.assertRaises(ValueError):
                study.run(destination, plotter=tiny_plot)

        self.assertFalse(destination.exists())

    def test_all_plots_changes_rendering_not_science(self):
        default = self.run_study("default-plots")
        all_plots = self.run_study(
            "all-plots",
            all_plots=True,
        )

        self.assertEqual(default["cases"], all_plots["cases"])
        self.assertEqual(
            default["regression_cases"],
            all_plots["regression_cases"],
        )
        self.assertEqual(
            default["summaries"],
            all_plots["summaries"],
        )

        self.assertEqual(
            len(list((self.base / "default-plots").rglob("timeline.png"))),
            12,
        )
        self.assertEqual(
            len(list((self.base / "all-plots").rglob("timeline.png"))),
            33,
        )

        for row in default["cases"] + default["regression_cases"]:
            relative = Path("cases") / row["case_id"]

            for filename in (
                "observations.csv",
                "fault-audit.csv",
                "decisions.csv",
                "result.json",
            ):
                self.assertEqual(
                    (self.base / "default-plots" / relative / filename).read_bytes(),
                    (self.base / "all-plots" / relative / filename).read_bytes(),
                )


if __name__ == "__main__":
    unittest.main()
