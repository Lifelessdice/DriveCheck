"""Independent audit controls for changed, omitted and incomplete evidence."""

from contextlib import redirect_stdout
import csv
import hashlib
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from c1_comparison import DEFAULT_CONFIG, ROOT, load_configuration, run
from tools.verify_c1 import main, verify


def read(path):
    return json.loads(path.read_text("utf-8"))


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def refresh_hashes(directory, manifest):
    """Update file checksums so negative controls reach semantic validation."""
    manifest["artifact_sha256"] = {
        path.relative_to(directory).as_posix(): digest(path)
        for path in directory.rglob("*") if path.is_file() and path.name != "manifest.json"
        and path.name != "report-manifest.json" and "report" not in path.relative_to(directory).parts
    }
    write(directory / "manifest.json", manifest)


class C1AuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (ROOT / "outputs").mkdir(exist_ok=True)
        cls.temporary = tempfile.TemporaryDirectory(prefix="c1-audit-", dir=ROOT / "outputs")
        cls.root = Path(cls.temporary.name)
        config = load_configuration(DEFAULT_CONFIG)
        config.update(development_seed_bases=[9000], evaluation_seed_bases=[9100],
                      evaluation_transform={"length_scale": 1.7, "time_scale": 1.4},
                      include_diagnostics=False)
        cls.config_path = cls.root / "input.json"
        write(cls.config_path, config)
        cls.reference = cls.root / "reference"
        result = run(cls.config_path, cls.reference)
        if result["status"] != "complete":
            raise AssertionError("audit fixture comparison did not complete")

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def copy(self):
        path = self.root / self._testMethodName
        shutil.copytree(self.reference, path)
        return path

    def test_complete_machine_is_independently_accepted(self):
        result = verify(self.reference)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["paired_cases"], 56)
        self.assertEqual(result["method_records"], 112)
        self.assertEqual(result["split_counts"], {"development": 28, "evaluation": 28})
        self.assertGreater(result["decision_rows"], 0)

    def test_rehashed_decision_tampering_fails_semantic_checks(self):
        directory = self.copy()
        manifest = read(directory / "manifest.json")
        artifact = manifest["cases"][0]["methods"]["raw"]["artifacts"]["decisions"]
        path = directory / artifact
        with path.open(encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            names, rows = reader.fieldnames, list(reader)
        row = next(row for row in rows if row["gap_m"])
        row["gap_m"] = "999.0"
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=names)
            writer.writeheader()
            writer.writerows(rows)
        refresh_hashes(directory, manifest)
        with self.assertRaisesRegex(ValueError, "causal state/TTC mismatch"):
            verify(directory)

    def test_unlisted_artifact_is_rejected(self):
        directory = self.copy()
        write(directory / "unlisted.json", {"extra": True})
        with self.assertRaisesRegex(ValueError, "inventory/hash"):
            verify(directory)

    def test_incomplete_pair_cannot_claim_complete_acceptance(self):
        directory = self.copy()
        manifest = read(directory / "manifest.json")
        case = manifest["cases"][0]
        case["status"] = "partial"
        case["methods"]["age_projection"]["status"] = "failed"
        write(directory / case["artifact_dir"] / "metrics.json", case)
        refresh_hashes(directory, manifest)
        with self.assertRaisesRegex(ValueError, "incomplete pair"):
            verify(directory)

    def test_omitted_planned_pair_is_rejected(self):
        directory = self.copy()
        manifest = read(directory / "manifest.json")
        manifest["cases"].pop()
        write(directory / "manifest.json", manifest)
        with self.assertRaisesRegex(ValueError, "planned case omitted"):
            verify(directory)

    def test_optional_report_is_bound_to_exact_machine_and_file_inventory(self):
        directory = self.copy()
        report = directory / "report"
        report.mkdir()
        case = read(directory / "manifest.json")["cases"][0]
        html = report / "report.html"
        html.write_text(f'<a href="../{case["artifact_dir"]}/metrics.json">Evidence</a>',
                        encoding="utf-8")
        package = {"schema": "drivecheck.c1.report.v1", "status": "complete",
                   "machine_status": "complete", "error": None,
                   "machine_manifest_sha256": digest(directory / "manifest.json"),
                   "artifact_sha256": {"report/report.html": digest(html)}}
        write(directory / "report-manifest.json", package)
        self.assertEqual(verify(directory)["local_links"], 1)
        html.write_text("changed", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "report package"):
            verify(directory)

    def test_cli_returns_nonzero_for_partial_status(self):
        directory = self.copy()
        manifest = read(directory / "manifest.json")
        manifest["status"] = "partial"
        write(directory / "manifest.json", manifest)
        with redirect_stdout(io.StringIO()) as output:
            status = main([str(directory)])
        self.assertEqual(status, 1)
        self.assertIn("not complete", output.getvalue())


if __name__ == "__main__":
    unittest.main()
