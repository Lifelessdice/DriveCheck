import csv
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from PIL import Image

from m1 import ROOT, SOURCE_FILES, run, sha256
from scenarios import m1_fixtures


class ExportTests(unittest.TestCase):
    def setUp(self):
        output_root = (ROOT / "outputs").resolve()
        self.assertEqual(output_root, ROOT / "outputs")
        output_root.mkdir(exist_ok=True)

        temporary = tempfile.TemporaryDirectory(
            prefix="m1-test-",
            dir=output_root,
        )
        self.base = Path(temporary.name).resolve()

        # Temporary cleanup is confined to the project's output tree.
        self.assertTrue(self.base.is_relative_to(output_root))
        self.addCleanup(temporary.cleanup)

    def test_exports_read_back_and_repeat(self):
        output = self.base / "first"
        result = run(output)

        self.assertEqual(result["status"], "complete")
        self.assertEqual(len(result["cases"]), 3)

        # These sequences come from independent distance calculations.
        expected_gaps = {
            "constant_speed_original": [30, 25, 20, 15, 10],
            "lead_braking_contact": [30, 25, 17.5, 5, -12.5, -32.5],
            "lead_braking_noncontact": [40, 50, 57.5, 60, 57.5, 50, 40, 30, 20],
        }

        expected_fields = [
            "scenario_id",
            "sample_id",
            "time_s",
            "ego_front_x_m",
            "lead_rear_x_m",
            "ego_speed_mps",
            "lead_speed_mps",
            "gap_m",
            "closing_speed_mps",
        ]

        for case in result["cases"]:
            identifier = case["scenario_id"]
            gaps = expected_gaps[identifier]

            with (output / f"{identifier}.csv").open(
                encoding="utf-8", newline=""
            ) as csv_file:
                reader = csv.DictReader(csv_file)
                self.assertEqual(reader.fieldnames, expected_fields)
                rows = list(reader)

            self.assertEqual(case["rows"], len(gaps))
            self.assertEqual(len(rows), len(gaps))
            self.assertEqual(case["horizon_s"], len(gaps) - 1)

            for sample_id, (row, expected_gap) in enumerate(zip(rows, gaps)):
                self.assertEqual(row["scenario_id"], identifier)
                self.assertEqual(int(row["sample_id"]), sample_id)
                self.assertEqual(float(row["time_s"]), sample_id)
                self.assertAlmostEqual(float(row["gap_m"]), expected_gap)
                self.assertGreaterEqual(float(row["lead_speed_mps"]), 0)

            sidecar = json.loads(
                (output / f"{identifier}.json").read_text(encoding="utf-8")
            )

            self.assertTrue(sidecar["truth_only"])
            self.assertEqual(sidecar["units"]["speed"], "m/s")
            self.assertEqual(sidecar["configuration"]["scenario_id"], identifier)
            self.assertEqual(sidecar["reference_check"], "passed")
            self.assertEqual(sidecar["computed"], case["computed"])
            self.assertAlmostEqual(sidecar["reference"]["final_gap_m"], gaps[-1])

            event = sidecar["computed"]["first_contact_time_s"]
            reference_event = sidecar["reference"]["first_contact_time_s"]

            if identifier == "lead_braking_contact":
                self.assertAlmostEqual(event, 3.3166247903554)
                self.assertAlmostEqual(reference_event, 3.3166247903554)
            else:
                self.assertIsNone(event)
                self.assertIsNone(reference_event)

            self.assertIsNone(sidecar["provenance"]["seed"])

            for name in SOURCE_FILES:
                self.assertEqual(
                    sidecar["provenance"]["source_sha256"][name],
                    sha256(ROOT / name),
                )

            self.assertEqual(
                set(case["artifacts"]),
                {f"{identifier}.{suffix}" for suffix in ("csv", "json", "png")},
            )

            for filename, digest in case["artifacts"].items():
                self.assertEqual(sha256(output / filename), digest)

            with Image.open(output / f"{identifier}.png") as picture:
                self.assertEqual(picture.format, "PNG")
                self.assertGreater(picture.width, 0)
                picture.verify()

        saved_manifest = json.loads(
            (output / "manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(saved_manifest, result)

        # Repeatability is checked on this machine with unchanged inputs/runtime.
        repeated = run(self.base / "repeat")
        self.assertEqual(repeated, result)

    def test_wrong_reference_records_failed_run(self):
        fixture = replace(
            m1_fixtures()[0],
            reference_final_gap_m=99.0,
        )
        output = self.base / "failed"

        with self.assertRaisesRegex(ValueError, "reference mismatch"):
            run(output, fixtures=[fixture])

        manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))

        self.assertEqual(manifest["status"], "failed")
        self.assertEqual(manifest["cases"], [])
        self.assertIn("constant_speed_original", manifest["error"])

        # Replacing one fixture does not mutate the default reference.
        self.assertEqual(m1_fixtures()[0].reference_final_gap_m, 10.0)

    def test_invalid_destination_writes_nothing(self):
        outside_outputs = ROOT / f"m1-invalid-{self.base.name}"
        self.assertFalse(outside_outputs.exists())

        with self.assertRaises(ValueError):
            run(outside_outputs)

        self.assertFalse(outside_outputs.exists())

        empty_output = self.base / "empty"

        with self.assertRaises(ValueError):
            run(empty_output, fixtures=[])

        self.assertFalse(empty_output.exists())


if __name__ == "__main__":
    unittest.main()
