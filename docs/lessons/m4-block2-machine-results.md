# M4 block 2 — Execute the plan and retain machine-readable evidence

Prepared 1 November 2026. This is the backing copy of the complete teaching block delivered directly in chat. **Proposed learner code/tests below are not implemented or run by the lesson author.** Block 1's actual saved implementation passed 14 focused tests and 145 full tests. The assistant explicitly pushed the existing M4 branch at `3ebd668`; new files still require a selective learner commit to be included remotely.

Acceptance update: the learner saved this block and produced run-a/run-b. Assistant review needed no source fix. Actual eight focused tests passed in 3.764 s; the full 153 tests passed in 29.979 s, both exit 0. Each saved run completes76 main+5 diagnostic cases,343 verified hashes and344 byte-identical files. Independent read-only checks cover662 audit rows/858 decisions, causal selection, all scoring and MAEs. Source/configuration hashes agree. No M4 rendered report/plot, fresh environment or CI is claimed. Continue with the complete [report/CLI block](m4-block3-offline-report.md), delivered directly in chat.

## Purpose and boundaries

A pending plan says what should run. The next layer executes every case, retains its causal evidence and distinguishes an algorithm miss from a failed execution. It reuses the accepted M3 computation; it does not reimplement physics, fault generation, replay or scoring.

Create `release_runner.py` and `test_m4_runner.py`. Keep the existing M2 `experiments.py`/`drivecheck.py` unchanged. This block's entry point is `release_runner.py`; release CLI dispatch, HTML/plots and the failure-study presentation follow. The manifest explicitly says `stage: "machine-results"`; a complete machine run is not yet acceptance of the entire CPU release, clean reproduction or CI.

The default inventory is 76 main cases and five separately summarized diagnostics. A case can complete with a missed warning. A program/export failure produces `failed` with null score/errors/counts; remaining cases are attempted. A run-level interruption can leave later rows `pending`, which must remain unscored.

Save every source truth row, every retained observation (including arrivals beyond the horizon), every source audit row and every decision. Dropout and retained-but-pending delivery are different states. Truth/audit/reference information stays offline and never enters the warning input.

## File 1 — release_runner.py

```python
"""Execute the configured M4 matrix and save core machine-readable evidence."""

import argparse
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import sys

from evaluation import summarize
from faults import FaultConfig
from m1 import sha256
from m3_study import (
    canonical_hash, checked_destination, compute_case, make_context, make_row,
    provenance, truth_hash, write_csv, write_json, write_records,
)
from motion import Scenario, TruthSample, first_contact_time, sample_truth, truth_at
from observations import Observation
from release_config import ROOT, build_plan, fixture_registry, load_configuration
from scenarios import Fixture
from stop_and_go import (
    first_stop_go_contact_time, sample_stop_go_truth, stop_go_truth_at,
)
from warning_policy import Decision

DEFAULT_CONFIG = ROOT / "configs" / "m4-release.json"
EXTRA_SOURCES = (
    "release_config.py", "release_runner.py",
    "test_m4_config.py", "test_m4_runner.py",
)
DIAGNOSTIC_POLICY = {
    "warning_threshold_s": 2.0,
    "max_age_s": 3.0,
    "pre_event_window_s": 3.0,
    "minimum_useful_lead_s": 1.0,
    "decision_clock": "fixed 0.5 s",
}


def prepare(config):
    """Freeze checked truth and pending rows without executing warnings."""
    cases = build_plan(config)
    registry = fixture_registry()
    contexts = {}
    for name in config["scenario_ids"]:
        family, fixture = registry[name]
        if family == "lead_braking":
            functions = (sample_truth, truth_at, first_contact_time)
        else:
            functions = (
                sample_stop_go_truth, stop_go_truth_at, first_stop_go_contact_time,
            )
        contexts[name] = make_context(family, fixture, *functions)
    for row in cases:
        context = contexts[row["scenario_id"]]
        row["truth_sha256"] = context["truth_sha256"]
        row["truth_file"] = f"truth/{row['scenario_id']}/truth.csv"

    fixture = Fixture(
        scenario=Scenario(
            scenario_id="latency_regression", initial_gap_m=30.0,
            ego_speed_mps=10.0, lead_speed_mps=5.0,
            timestep_s=1.0, sample_count=7,
        ),
        reference_contact_time_s=6.0,
        reference_final_gap_m=0.0,
        reference_basis="gap=30-5t; contact at 6 s; final gap at 6 s is 0 m",
    )
    context = make_context(
        "constant_speed_diagnostic", fixture,
        sample_truth, truth_at, first_contact_time,
    )
    contexts[fixture.scenario.scenario_id] = context
    diagnostic_rows = []
    delays = (
        ("delay_0s", 0.0), ("delay_1s", 1.0), ("delay_1p5s", 1.5),
        ("delay_2s", 2.0), ("delay_2p5s", 2.5),
    )
    for index, (name, delay) in enumerate(delays, start=1):
        fault = FaultConfig(mode="clean" if delay == 0 else "latency", latency_s=delay)
        row = make_row(
            context, f"regression-{index:03d}", name, "regression",
            fault, DIAGNOSTIC_POLICY,
        )
        row.update(
            schema="drivecheck.m4.case.v1", seed_base=None,
            seed_role="unused deterministic placeholders",
            reference_final_gap_m=0.0,
        )
        diagnostic_rows.append(row)
    return contexts, cases, diagnostic_rows


def _payload(manifest):
    return {key: value for key, value in manifest.items() if key != "artifact_sha256"}


def _add_error(manifest, error):
    message = f"{type(error).__name__}: {error}"
    previous = manifest["error"]
    manifest["error"] = f"{previous}; {message}" if previous else message


def _set_status(manifest):
    rows = manifest["cases"] + manifest["regression_cases"]
    complete = sum(row["status"] == "complete" for row in rows)
    manifest["status"] = (
        "complete" if complete == len(rows) and manifest["error"] is None
        else "partial" if complete else "failed"
    )


def _save_case(directory, context, row, data):
    """Export evidence before treating an execution as complete."""
    if truth_hash(context["truth"]) != context["truth_sha256"]:
        raise ValueError("cached truth changed")
    if truth_hash(data["truth"]) != context["truth_sha256"]:
        raise ValueError("case truth differs from the frozen snapshot")
    if len(data["audit"]) != len(context["truth"]):
        raise ValueError("fault audit must contain one row per source sample")

    write_records(directory / "observations.csv", data["observations"], Observation)
    write_csv(directory / "fault-audit.csv", data["audit"], list(data["audit"][0]))
    write_records(directory / "decisions.csv", data["replay"].decisions, Decision)
    row.update(
        status="complete", score=data["score"], errors=data["errors"],
        counts={
            "source": len(data["truth"]),
            "observations": len(data["observations"]),
            "decisions": len(data["replay"].decisions),
            "dropped": sum(item["dropped"] for item in data["audit"]),
            "ignored_older_arrivals": data["replay"].ignored_older_arrival_count,
            "pending_arrivals": data["replay"].beyond_horizon_arrival_count,
        },
    )
    write_json(directory / "result.json", row)


def _save_table(destination, rows):
    table = []
    for row in rows:
        score = row["score"] or {}
        errors = row["errors"] or {}
        table.append({
            "section": row["section"], "case_id": row["case_id"],
            "scenario_id": row["scenario_id"], "condition_id": row["condition_id"],
            "seed_base": row["seed_base"], "status": row["status"],
            "reference_contact_time_s": row["reference_contact_time_s"],
            "outcome": score.get("outcome"),
            "first_warning_time_s": score.get("first_warning_time_s"),
            "matched_lead_s": score.get("matched_lead_s"),
            "gap_mae_m": errors.get("gap_mae_m"),
            "closing_speed_mae_mps": errors.get("closing_speed_mae_mps"),
            "fresh_count": errors.get("fresh_count"),
            "unavailable_count": errors.get("unavailable_count"),
            "stale_count": errors.get("stale_count"),
            "error": row["error"],
        })
    write_csv(destination / "cases.csv", table, list(table[0]))


def _artifact_hashes(destination):
    """Exclude the manifest from its own hash inventory."""
    return {
        path.relative_to(destination).as_posix(): sha256(path)
        for path in sorted(destination.rglob("*"))
        if path.is_file() and path != destination / "manifest.json"
    }


def run(config_path, output_dir, *, case_runner=None):
    """Run all declared cases; preserve failed and unattempted rows."""
    if case_runner is not None and not callable(case_runner):
        raise ValueError("case_runner must be callable or None")
    executor = compute_case if case_runner is None else case_runner
    config = load_configuration(config_path)
    output = Path(output_dir)
    destination = checked_destination(output if output.is_absolute() else ROOT / output)
    contexts, cases, diagnostics = prepare(config)
    config_path = Path(config_path)
    config_path = (config_path if config_path.is_absolute() else ROOT / config_path).resolve()
    runtime = provenance()
    runtime["source_sha256"].update({name: sha256(ROOT / name) for name in EXTRA_SOURCES})
    runtime["input_configuration_sha256"] = sha256(config_path)
    runtime["input_configuration_path"] = config_path.relative_to(ROOT).as_posix()
    snapshot = deepcopy(cases + diagnostics)
    manifest = {
        "schema": "drivecheck.m4.machine.v1", "stage": "machine-results",
        "status": "running", "configuration": config,
        "configuration_sha256": canonical_hash(config),
        "plan_sha256": canonical_hash(snapshot), "provenance": runtime,
        "expected_case_count": len(cases), "expected_regression_count": len(diagnostics),
        "cases": cases, "regression_cases": diagnostics,
        "summaries": [], "regression_summaries": [], "seed_summaries": [],
        "error": None, "artifact_sha256": {},
    }

    destination.mkdir(parents=True, exist_ok=False)
    write_json(destination / "manifest.json", manifest)
    try:
        write_json(destination / "configuration.json", config)
        write_json(destination / "plan.json", snapshot)
        for name, context in contexts.items():
            directory = destination / "truth" / name
            directory.mkdir(parents=True)
            fixture = context["fixture"]
            write_records(directory / "truth.csv", context["truth"], TruthSample)
            write_json(directory / "configuration.json", asdict(fixture.scenario))
            write_json(directory / "reference.json", {
                "contact_time_s": fixture.reference_contact_time_s,
                "final_gap_m": fixture.reference_final_gap_m,
                "basis": fixture.reference_basis,
                "truth_content_sha256": context["truth_sha256"],
            })

        for row in cases + diagnostics:
            directory = destination / "cases" / row["case_id"]
            try:
                directory.mkdir(parents=True)
                context = contexts[row["scenario_id"]]
                data = executor(context, FaultConfig(**row["fault"]), dict(row["policy"]))
                _save_case(directory, context, row, data)
            except Exception as error:
                row.update(
                    status="failed", score=None, errors=None, counts=None,
                    error=f"{type(error).__name__}: {error}",
                )
                try:
                    write_json(directory / "result.json", row)
                except Exception as save_error:
                    row["error"] += f"; result save failed: {type(save_error).__name__}: {save_error}"
            write_json(destination / "manifest.json", manifest)
    except Exception as error:
        _add_error(manifest, error)

    try:
        manifest["summaries"] = summarize(cases)
        manifest["regression_summaries"] = summarize(diagnostics)
        bases = sorted({row["seed_base"] for row in cases if row["seed_base"] is not None})
        manifest["seed_summaries"] = [{
            "seed_base": base,
            "summaries": summarize([row for row in cases if row["seed_base"] == base]),
        } for base in bases]
    except Exception as error:
        _add_error(manifest, error)
    _set_status(manifest)
    try:
        _save_table(destination, cases + diagnostics)
        write_json(destination / "results.json", _payload(manifest))
        manifest["artifact_sha256"] = _artifact_hashes(destination)
    except Exception as error:
        _add_error(manifest, error)
        _set_status(manifest)
        # Status-bearing results changed; discard any now-stale hash inventory.
        manifest["artifact_sha256"] = {}
        write_json(destination / "results.json", _payload(manifest))
    write_json(destination / "manifest.json", manifest)
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        manifest = run(args.config, args.output_dir)
    except (ValueError, OSError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    rows = manifest["cases"] + manifest["regression_cases"]
    completed = sum(row["status"] == "complete" for row in rows)
    print(f"machine-results {manifest['status']}: {completed}/{len(rows)} cases")
    if manifest["error"]:
        print(manifest["error"], file=sys.stderr)
    return 0 if manifest["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

`prepare` evaluates clean trajectory/reference checks but never runs warning replay. The execution callback is injected only to test failures. It receives the same causal pipeline inputs as the accepted computation. Full truth and audit remain export/evaluation material.

`results.json` contains scientific data without the artifact hash map. The final manifest hashes those files and excludes itself, avoiding a circular hash. If hashing fails after results were written, status-bearing results are rewritten as incomplete and the hash map is cleared. A catastrophic filesystem failure can still prevent final export and must surface as a nonzero process result; this is not a transactional storage system. An interrupted run's last manifest can remain `running` and must never be accepted as complete.

## File 2 — test_m4_runner.py

```python
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
            "lead_braking_contact", "lead_braking_noncontact",
        ]
        self.config["conditions"] = [
            {"condition_id": "clean", "fault": {"mode": "clean"}, "seed_bases": [None]},
            {"condition_id": "latency_1s", "fault": {"mode": "latency", "latency_s": 1.0}, "seed_bases": [None]},
        ]
        self.config_path = self.directory / "smoke.json"
        self.config_path.write_text(json.dumps(self.config), encoding="utf-8")

    def execute(self, name="run", **kwargs):
        return release_runner.run(self.config_path, self.directory / name, **kwargs)

    def test_independent_four_case_smoke_and_five_diagnostics(self):
        result = self.execute()
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["stage"], "machine-results")
        self.assertEqual(len(result["cases"]), 4)
        self.assertEqual(len(result["regression_cases"]), 5)
        pairs = {(row["scenario_id"], row["condition_id"]): row for row in result["cases"]}
        expected = {
            ("lead_braking_contact", "clean"): ("useful", 2.0),
            ("lead_braking_contact", "latency_1s"): ("late", 3.0),
            ("lead_braking_noncontact", "clean"): ("false_warning", 7.0),
            ("lead_braking_noncontact", "latency_1s"): ("false_warning", 8.0),
        }
        for pair, (outcome, first_warning) in expected.items():
            row = pairs[pair]
            self.assertEqual(row["status"], "complete")
            self.assertEqual(row["score"]["outcome"], outcome)
            self.assertEqual(row["score"]["first_warning_time_s"], first_warning)
        delayed = pairs[("lead_braking_contact", "latency_1s")]
        self.assertAlmostEqual(delayed["score"]["matched_lead_s"], 0.3166247903554, places=9)
        self.assertEqual(delayed["errors"]["gap_mae_m"], 12.5)
        self.assertEqual(delayed["errors"]["closing_speed_mae_mps"], 3.0)
        self.assertEqual(delayed["errors"]["fresh_count"], 5)
        self.assertEqual(delayed["errors"]["unavailable_count"], 1)
        self.assertEqual(delayed["errors"]["stale_count"], 0)
        diagnostics = result["regression_cases"]
        self.assertEqual([row["score"]["outcome"] for row in diagnostics],
                         ["useful", "useful", "late", "late", "missed"])
        self.assertEqual([row["score"]["first_warning_time_s"] for row in diagnostics],
                         [4.0, 5.0, 5.5, 6.0, None])
        self.assertEqual(diagnostics[-1]["counts"]["pending_arrivals"], 3)

    def test_exported_rows_audit_and_hashes_are_real_evidence(self):
        result = self.execute()
        output = self.directory / "run"
        saved = json.loads((output / "results.json").read_text("utf-8"))
        self.assertEqual(saved["cases"], result["cases"])
        with (output / "cases.csv").open(encoding="utf-8", newline="") as stream:
            table = list(csv.DictReader(stream))
        rows = result["cases"] + result["regression_cases"]
        self.assertEqual(len(table), 9)
        self.assertEqual({row["case_id"] for row in table}, {row["case_id"] for row in rows})
        for row in rows:
            case_dir = output / "cases" / row["case_id"]
            with (case_dir / "fault-audit.csv").open(encoding="utf-8", newline="") as stream:
                audit = list(csv.DictReader(stream))
            self.assertEqual(len(audit), row["counts"]["source"])
            self.assertEqual(json.loads((case_dir / "result.json").read_text("utf-8")), row)
        self.assertNotIn("manifest.json", result["artifact_sha256"])
        for relative, expected_hash in result["artifact_sha256"].items():
            self.assertEqual(release_runner.sha256(output / relative), expected_hash)

    def test_case_failure_retains_denominators_and_later_cases(self):
        def fail_one(context, fault, policy):
            if (context["fixture"].scenario.scenario_id == "lead_braking_contact"
                    and fault.mode == "clean"):
                raise RuntimeError("controlled case failure")
            return release_runner.compute_case(context, fault, policy)
        result = self.execute(case_runner=fail_one)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(len(result["cases"]), 4)
        self.assertEqual(sum(row["status"] == "complete" for row in result["cases"]), 3)
        failed = next(row for row in result["cases"] if row["status"] == "failed")
        self.assertIn("controlled case failure", failed["error"])
        self.assertIsNone(failed["score"])
        self.assertIsNone(failed["errors"])
        self.assertIsNone(failed["counts"])
        clean = next(group for group in result["summaries"] if group["condition_id"] == "clean")
        self.assertEqual(clean["planned"]["positive"], 1)
        self.assertEqual(clean["scored"]["positive"], 0)
        self.assertIsNone(clean["rates"]["missed"]["value"])
        self.assertTrue(all(row["status"] == "complete" for row in result["regression_cases"]))
        with patch("release_runner.run", return_value=result):
            self.assertEqual(release_runner.main(["--output-dir", "outputs/unused"]), 1)

    def test_repeated_run_has_identical_saved_bytes(self):
        self.execute("a")
        self.execute("b")
        a, b = self.directory / "a", self.directory / "b"
        paths = [path.relative_to(a) for path in a.rglob("*") if path.is_file()]
        self.assertEqual(set(paths), {path.relative_to(b) for path in b.rglob("*") if path.is_file()})
        for relative in paths:
            self.assertEqual((a / relative).read_bytes(), (b / relative).read_bytes(), str(relative))

    def test_preflight_rejects_invalid_existing_and_outside_destinations(self):
        existing = self.directory / "existing"
        existing.mkdir()
        marker = existing / "keep.txt"
        marker.write_text("preserve", encoding="utf-8")
        with self.assertRaises(ValueError):
            release_runner.run(self.config_path, existing)
        self.assertEqual(marker.read_text("utf-8"), "preserve")
        with self.assertRaises(ValueError):
            release_runner.run(self.config_path, ROOT / "outside-output-test")
        invalid = deepcopy(self.config)
        invalid["warning"]["threshold_s"] = -1
        self.config_path.write_text(json.dumps(invalid), encoding="utf-8")
        with self.assertRaises(ValueError):
            self.execute("invalid")
        self.assertFalse((self.directory / "invalid").exists())

    def test_hash_failure_clears_stale_claim_and_updates_results(self):
        with patch("release_runner._artifact_hashes", side_effect=OSError("controlled hash failure")):
            result = self.execute()
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["artifact_sha256"], {})
        saved = json.loads((self.directory / "run" / "results.json").read_text("utf-8"))
        self.assertEqual(saved["status"], "partial")
        self.assertIn("controlled hash failure", saved["error"])

    def test_case_export_failure_stays_failed_and_other_cases_continue(self):
        original = release_runner.write_records
        def fail_export(path, records, record_type):
            if path.parent.name == "case-001" and path.name == "observations.csv":
                raise OSError("controlled export failure")
            return original(path, records, record_type)
        with patch("release_runner.write_records", side_effect=fail_export):
            result = self.execute()
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["cases"][0]["status"], "failed")
        self.assertIsNone(result["cases"][0]["score"])
        self.assertIn("controlled export failure", result["cases"][0]["error"])
        self.assertTrue(all(row["status"] == "complete" for row in result["cases"][1:]))

    def test_real_cli_and_full_declared_matrix(self):
        output = self.directory / "cli"
        completed = subprocess.run([
            sys.executable, str(ROOT / "release_runner.py"),
            "--config", str(self.config_path), "--output-dir", str(output),
        ], cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        full = release_runner.run(ROOT / "configs" / "m4-release.json", self.directory / "full")
        self.assertEqual(full["status"], "complete")
        self.assertEqual(len(full["cases"]), 76)
        self.assertEqual(len(full["regression_cases"]), 5)
        self.assertTrue(all(row["status"] == "complete" for row in full["cases"] + full["regression_cases"]))
```

The final test invokes the real CLI for a small independent fixture and also executes the declared full matrix without plotting. Its success remains a prediction until you run it. The injected-failure test deliberately exercises a partial CLI result; its printed partial-status line is expected within that test.

## Run the block after saving both files

```powershell
Set-Location 'E:\DriveCheck'
.\.venv\Scripts\python.exe -m unittest -v test_m4_runner
.\.venv\Scripts\python.exe -m unittest -v
.\.venv\Scripts\python.exe .\release_runner.py --config .\configs\m4-release.json --output-dir .\outputs\m4-machine\run-a
.\.venv\Scripts\python.exe .\release_runner.py --config .\configs\m4-release.json --output-dir .\outputs\m4-machine\run-b
Get-Content -LiteralPath .\outputs\m4-machine\run-a\manifest.json -TotalCount 20
Get-Content -LiteralPath .\outputs\m4-machine\run-a\cases.csv -TotalCount 8
Get-FileHash -Algorithm SHA256 -LiteralPath .\outputs\m4-machine\run-a\results.json
Get-FileHash -Algorithm SHA256 -LiteralPath .\outputs\m4-machine\run-b\results.json
```

Use fresh output names if those folders exist. Expected default CLI message is `machine-results complete: 81/81 cases`. The main76/diagnostic5 groups stay separate in JSON/summaries. Expected repeated canonical results hashes match. No all-seed warning outcome table is prescribed: read the real outcomes rather than inventing them from the seed-100 M3 result.

Independent smoke arithmetic: contact at sqrt(11), first warning2 clean/3 delayed, leads1.316625/0.316625. On the negative braking horizon, gap at7 is30 and closing10, so threshold3 warns; with1-second delay that reading arrives8. These are both finite-horizon false-warning episodes. Fixed diagnostic first warnings4/5/5.5/6/None remain separate. Strong diagnostic delay2.5 has source IDs4/5/6 arriving6.5/7.5/8.5 after horizon6: three retained pending arrivals, not three dropouts.

After implementation, inspect the actual audit/observations/decisions and report path/hash/count evidence for review. Completion here means machine exports and tests checked, with HTML/plots/release CLI integration/failure-study presentation/clean reproduction/CI still remaining. Keep the same branch and make the next selective checkpoint after review.
