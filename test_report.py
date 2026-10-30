import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from drivecheck import main
from evaluation import aligned_errors
from experiments import DEFAULT_CONFIG, compute_case, run
from m1 import ROOT, sha256
from observations import make_observations
from motion import sample_truth
from replay import make_decision_times, replay
from scenarios import m1_fixtures
from warning_policy import Decision


def fixture_named(name):
    return next(
        fixture for fixture in m1_fixtures() if fixture.scenario.scenario_id == name
    )


def trace_for(fixture, delay_s):
    scenario = fixture.scenario
    observations = make_observations(sample_truth(scenario), delay_s)
    base = [index * scenario.timestep_s for index in range(scenario.sample_count)]
    times = make_decision_times(
        base,
        observations,
        scenario.horizon_s,
        scenario_id=scenario.scenario_id,
    )
    return replay(
        observations,
        times,
        scenario_id=scenario.scenario_id,
        horizon_s=scenario.horizon_s,
    ).decisions


class AlignedErrorTests(unittest.TestCase):
    def test_known_current_time_errors(self):
        fixture = fixture_named("lead_braking_contact")
        delayed = trace_for(fixture, 1.0)
        at_three = [decision for decision in delayed if decision.decision_time_s == 3.0]

        single = aligned_errors(at_three, fixture.scenario)
        self.assertEqual(single["gap_mae_m"], 12.5)
        self.assertEqual(single["closing_speed_mae_mps"], 5.0)

        full = aligned_errors(delayed, fixture.scenario)
        self.assertEqual(full["fresh_count"], 5)
        self.assertEqual(full["unavailable_count"], 1)
        self.assertEqual(full["stale_count"], 0)
        self.assertEqual(full["gap_mae_m"], 12.5)
        self.assertEqual(full["closing_speed_mae_mps"], 3.0)

        clean = aligned_errors(trace_for(fixture, 0.0), fixture.scenario)
        self.assertEqual(clean["gap_mae_m"], 0.0)
        self.assertEqual(clean["closing_speed_mae_mps"], 0.0)

    def test_missing_stale_and_not_closing(self):
        fixture = fixture_named("lead_braking_contact")

        missing = aligned_errors(
            [
                Decision(0.0, reason="unavailable"),
                Decision(1.0, reason="stale"),
            ],
            fixture.scenario,
        )
        self.assertEqual(missing["fresh_count"], 0)
        self.assertEqual(missing["unavailable_count"], 1)
        self.assertEqual(missing["stale_count"], 1)
        self.assertIsNone(missing["gap_mae_m"])
        self.assertIsNone(missing["closing_speed_mae_mps"])

        opening = fixture_named("lead_braking_noncontact")
        result = aligned_errors(
            [
                Decision(
                    0.0,
                    gap_m=40.0,
                    closing_speed_mps=-10.0,
                    reason="not_closing",
                )
            ],
            opening.scenario,
        )
        self.assertEqual(result["fresh_count"], 1)
        self.assertEqual(result["gap_mae_m"], 0.0)


class ReportTests(unittest.TestCase):
    def setUp(self):
        output_root = ROOT / "outputs"
        output_root.mkdir(exist_ok=True)
        temporary = tempfile.TemporaryDirectory(
            prefix="m2-report-test-",
            dir=output_root,
        )
        self.base = Path(temporary.name).resolve()
        self.assertTrue(self.base.is_relative_to(output_root.resolve()))
        self.addCleanup(temporary.cleanup)

    def test_exports_read_back_and_repeat(self):
        first = self.base / "first"
        repeat = self.base / "repeat"

        manifest = run(DEFAULT_CONFIG, first)
        repeated = run(DEFAULT_CONFIG, repeat)

        self.assertEqual(manifest["status"], "complete")
        self.assertEqual(repeated["status"], "complete")
        self.assertEqual(len(manifest["cases"]), 6)
        self.assertTrue(all(case["status"] == "complete" for case in manifest["cases"]))

        for relative, digest in manifest["artifact_sha256"].items():
            self.assertEqual(sha256(first / relative), digest)

        for name in ("configuration.json", "results.json", "cases.csv"):
            self.assertEqual(
                (first / name).read_bytes(),
                (repeat / name).read_bytes(),
            )

        for case in manifest["cases"]:
            directory = case["case_id"]

            for name in (
                "truth.csv",
                "observations.csv",
                "decisions.csv",
                "result.json",
            ):
                self.assertEqual(
                    (first / directory / name).read_bytes(),
                    (repeat / directory / name).read_bytes(),
                )

            for name in ("truth.png", "timeline.png"):
                with Image.open(first / directory / name) as image:
                    image.verify()

        # Both conditions must preserve identical underlying truth.
        for fixture in m1_fixtures():
            cases = [
                case
                for case in manifest["cases"]
                if case["scenario_id"] == fixture.scenario.scenario_id
            ]
            self.assertEqual(
                (first / cases[0]["case_id"] / "truth.csv").read_bytes(),
                (first / cases[1]["case_id"] / "truth.csv").read_bytes(),
            )

        delayed = next(
            case
            for case in manifest["cases"]
            if case["scenario_id"] == "lead_braking_contact"
            and case["condition_id"] == "latency_1s"
        )
        self.assertEqual(delayed["score"]["outcome"], "late")
        self.assertEqual(delayed["errors"]["gap_mae_m"], 12.5)
        self.assertEqual(delayed["errors"]["closing_speed_mae_mps"], 3.0)

        saved = json.loads((first / "results.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["status"], "complete")
        self.assertEqual(len(saved["cases"]), 6)
        self.assertIn("case-006", (first / "report.html").read_text(encoding="utf-8"))

    def test_case_failure_stays_visible(self):
        def injected(fixture, condition, config):
            if (
                fixture.scenario.scenario_id == "lead_braking_contact"
                and condition["condition_id"] == "latency_1s"
            ):
                raise RuntimeError("Injected case failure")
            return compute_case(fixture, condition, config)

        output = self.base / "partial"

        with patch("experiments.compute_case", side_effect=injected):
            manifest = run(DEFAULT_CONFIG, output)

        self.assertEqual(manifest["status"], "partial")
        self.assertEqual(len(manifest["cases"]), 6)
        self.assertEqual(
            sum(case["status"] == "complete" for case in manifest["cases"]),
            5,
        )

        delayed = next(
            group
            for group in manifest["summaries"]
            if group["condition_id"] == "latency_1s"
        )
        self.assertEqual(delayed["unscored"]["positive"], 1)
        self.assertIsNone(delayed["rates"]["missed"]["value"])
        self.assertIn(
            "Injected case failure",
            (output / "report.html").read_text(encoding="utf-8"),
        )

    def test_preflight_writes_nothing(self):
        config = json.loads(DEFAULT_CONFIG.read_text(encoding="utf-8"))
        config["warning"]["threshold_s"] = 0
        bad = self.base / "invalid.json"
        bad.write_text(json.dumps(config), encoding="utf-8")
        destination = self.base / "must-not-exist"

        with self.assertRaises(ValueError):
            run(bad, destination)
        self.assertFalse(destination.exists())

        duplicate = self.base / "duplicate.json"
        duplicate.write_text(
            '{"schema_version":"x","schema_version":"y"}',
            encoding="utf-8",
        )
        with self.assertRaises(ValueError):
            run(duplicate, destination)
        self.assertFalse(destination.exists())

        existing = self.base / "existing"
        existing.mkdir()
        sentinel = existing / "keep.txt"
        sentinel.write_text("preserve", encoding="utf-8")

        with self.assertRaises(ValueError):
            run(DEFAULT_CONFIG, existing)
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "preserve")

        outside = ROOT / f"outside-{self.base.name}"
        self.assertFalse(outside.exists())

        with self.assertRaises(ValueError):
            run(DEFAULT_CONFIG, outside)
        self.assertFalse(outside.exists())

    def test_report_failure_and_cli_status(self):
        config = json.loads(DEFAULT_CONFIG.read_text(encoding="utf-8"))
        config["scenario_ids"] = ["constant_speed_original"]
        config["conditions"] = [config["conditions"][0]]

        small = self.base / "small.json"
        small.write_text(json.dumps(config), encoding="utf-8")
        output = self.base / "report-failure"

        with patch(
            "experiments.write_report",
            side_effect=RuntimeError("Injected report failure"),
        ):
            manifest = run(small, output)

        self.assertEqual(manifest["status"], "failed")

        saved = json.loads((output / "results.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["status"], "failed")
        self.assertIn("Injected report failure", saved["error"])

        with patch("drivecheck.run", return_value=manifest):
            with patch("builtins.print"):
                self.assertEqual(main([]), 1)


if __name__ == "__main__":
    unittest.main()
