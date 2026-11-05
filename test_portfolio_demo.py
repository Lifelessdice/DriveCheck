"""Portfolio export preserves evidence and rejects destructive output plans."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import portfolio_demo


class TestPortfolioDemo(unittest.TestCase):
    def setUp(self):
        (portfolio_demo.ROOT / "outputs").mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=portfolio_demo.ROOT / "outputs")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "run"
        (self.source / "report").mkdir(parents=True)
        for number in (1, 2, 3):
            (self.source / "report" / f"pair-{number:02d}.png").write_bytes(b"fixture bytes")
        self.methods = {
            name: {"positive_count": 38, "negative_count": 38,
                   "outcomes": {"useful": 31, "late": 2, "missed": 5,
                                "false_warning": false_count,
                                "clear_negative": 38 - false_count}}
            for name, false_count in (("raw", 26), ("age_projection", 35))}
        portfolio_demo.write_json(self.source / "manifest.json", {
            "config_sha256": portfolio_demo.CONFIG_SHA256,
            "summary": {"evaluation": {"methods": self.methods, "complete_pairs": 76,
                "directional_changes": {"gap_mae_m": {
                    "loss": 0, "not_comparable": 1, "unchanged": 38, "win": 37}}}}})
        portfolio_demo.write_json(self.source / "report-manifest.json", {
            "plot_selection": [{"case_id": case, "path": f"report/pair-{number:02d}.png"}
                               for number, case in enumerate(portfolio_demo.PLOT_CASES, 1)]})
        (self.source / "cases.csv").write_text("preserved,fixture\n", encoding="utf-8")

    def test_existing_output_is_preserved_without_audit_or_writes(self):
        output = self.root / "existing"
        output.mkdir()
        sentinel = output / "keep.txt"
        sentinel.write_bytes(b"keep existing work")
        before = portfolio_demo.inventory(self.source)
        with patch.object(portfolio_demo, "verify") as audit:
            with self.assertRaisesRegex(ValueError, "fresh, separate"):
                portfolio_demo.build(self.source, output)
            audit.assert_not_called()
        self.assertEqual(sentinel.read_bytes(), b"keep existing work")
        self.assertEqual(portfolio_demo.inventory(self.source), before)

    def test_invalid_evidence_creates_no_destination(self):
        output = self.root / "rejected"
        with patch.object(portfolio_demo, "verify", side_effect=ValueError("bad source")):
            with self.assertRaisesRegex(ValueError, "bad source"):
                portfolio_demo.build(self.source, output)
        self.assertFalse(output.exists())

    def test_packaging_copies_all_evidence_without_changing_source(self):
        output = self.root / "demo"
        before = portfolio_demo.inventory(self.source)
        with patch.object(portfolio_demo, "verify", return_value={"status": "complete"}):
            record = portfolio_demo.build(self.source, output)
        self.assertEqual(record["status"], "complete")
        self.assertEqual(portfolio_demo.inventory(self.source), before)
        self.assertEqual(portfolio_demo.inventory(output / "evidence"), before)
        self.assertEqual({name: value for name, value in portfolio_demo.inventory(output).items()
                          if name != "manifest.json"}, record["artifact_sha256"])
        self.assertTrue(record["source_preserved"])
        self.assertIn("31/38", (output / "index.html").read_text("utf-8"))
        self.assertEqual(json.loads((output / "manifest.json").read_text("utf-8")), record)

    def test_different_plot_selection_cannot_receive_fixed_captions(self):
        portfolio_demo.write_json(self.source / "report-manifest.json", {"plot_selection": []})
        output = self.root / "wrong-narrative"
        with patch.object(portfolio_demo, "verify", return_value={"status": "complete"}):
            with self.assertRaisesRegex(ValueError, "three-case portfolio narrative"):
                portfolio_demo.build(self.source, output)
        self.assertFalse(output.exists())

    def test_different_outcomes_cannot_receive_fixed_conclusion(self):
        path = self.source / "manifest.json"
        value = json.loads(path.read_text("utf-8"))
        value["summary"]["evaluation"]["methods"]["raw"]["outcomes"]["missed"] = 0
        portfolio_demo.write_json(path, value)
        output = self.root / "wrong-results"
        with patch.object(portfolio_demo, "verify", return_value={"status": "complete"}):
            with self.assertRaisesRegex(ValueError, "fixed portfolio narrative"):
                portfolio_demo.build(self.source, output)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
