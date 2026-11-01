"""Execute the configured M4 matrix and save machine-readable evidence."""

import argparse
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import sys

from evaluation import summarize
from faults import FaultConfig
from m1 import sha256
from m3_study import (
    canonical_hash,
    checked_destination,
    compute_case,
    make_context,
    make_row,
    provenance,
    truth_hash,
    write_csv,
    write_json,
    write_records,
)
from motion import (
    Scenario,
    TruthSample,
    first_contact_time,
    sample_truth,
    truth_at,
)
from observations import Observation
from release_config import (
    ROOT,
    build_plan,
    fixture_registry,
    load_configuration,
)
from scenarios import Fixture
from stop_and_go import (
    first_stop_go_contact_time,
    sample_stop_go_truth,
    stop_go_truth_at,
)
from warning_policy import Decision

DEFAULT_CONFIG = ROOT / "configs" / "m4-release.json"

EXTRA_SOURCES = (
    "release_config.py",
    "release_runner.py",
    "test_m4_config.py",
    "test_m4_runner.py",
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
            functions = (
                sample_truth,
                truth_at,
                first_contact_time,
            )
        else:
            functions = (
                sample_stop_go_truth,
                stop_go_truth_at,
                first_stop_go_contact_time,
            )

        contexts[name] = make_context(
            family,
            fixture,
            *functions,
        )

    for row in cases:
        context = contexts[row["scenario_id"]]

        row["truth_sha256"] = context["truth_sha256"]
        row["truth_file"] = f"truth/{row['scenario_id']}/truth.csv"

    fixture = Fixture(
        scenario=Scenario(
            scenario_id="latency_regression",
            initial_gap_m=30.0,
            ego_speed_mps=10.0,
            lead_speed_mps=5.0,
            timestep_s=1.0,
            sample_count=7,
        ),
        reference_contact_time_s=6.0,
        reference_final_gap_m=0.0,
        reference_basis=("gap=30-5t; contact at 6 s; " "final gap at 6 s is 0 m"),
    )

    context = make_context(
        "constant_speed_diagnostic",
        fixture,
        sample_truth,
        truth_at,
        first_contact_time,
    )

    contexts[fixture.scenario.scenario_id] = context
    diagnostic_rows = []

    delays = (
        ("delay_0s", 0.0),
        ("delay_1s", 1.0),
        ("delay_1p5s", 1.5),
        ("delay_2s", 2.0),
        ("delay_2p5s", 2.5),
    )

    for index, (name, delay) in enumerate(delays, start=1):
        fault = FaultConfig(
            mode="clean" if delay == 0 else "latency",
            latency_s=delay,
        )

        row = make_row(
            context,
            f"regression-{index:03d}",
            name,
            "regression",
            fault,
            DIAGNOSTIC_POLICY,
        )

        row.update(
            schema="drivecheck.m4.case.v1",
            seed_base=None,
            seed_role="unused deterministic placeholders",
            reference_final_gap_m=0.0,
        )

        diagnostic_rows.append(row)

    return contexts, cases, diagnostic_rows


def _payload(manifest):
    """Keep the artifact hash inventory outside canonical result data."""
    return {key: value for key, value in manifest.items() if key != "artifact_sha256"}


def _add_error(manifest, error):
    message = f"{type(error).__name__}: {error}"
    previous = manifest["error"]

    manifest["error"] = f"{previous}; {message}" if previous else message


def _set_status(manifest):
    rows = manifest["cases"] + manifest["regression_cases"]

    complete = sum(row["status"] == "complete" for row in rows)

    manifest["status"] = (
        "complete"
        if complete == len(rows) and manifest["error"] is None
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

    write_records(
        directory / "observations.csv",
        data["observations"],
        Observation,
    )

    write_csv(
        directory / "fault-audit.csv",
        data["audit"],
        list(data["audit"][0]),
    )

    write_records(
        directory / "decisions.csv",
        data["replay"].decisions,
        Decision,
    )

    row.update(
        status="complete",
        score=data["score"],
        errors=data["errors"],
        counts={
            "source": len(data["truth"]),
            "observations": len(data["observations"]),
            "decisions": len(data["replay"].decisions),
            "dropped": sum(item["dropped"] for item in data["audit"]),
            "ignored_older_arrivals": (data["replay"].ignored_older_arrival_count),
            "pending_arrivals": (data["replay"].beyond_horizon_arrival_count),
        },
    )

    write_json(directory / "result.json", row)


def _save_table(destination, rows):
    table = []

    for row in rows:
        score = row["score"] or {}
        errors = row["errors"] or {}

        table.append(
            {
                "section": row["section"],
                "case_id": row["case_id"],
                "scenario_id": row["scenario_id"],
                "condition_id": row["condition_id"],
                "seed_base": row["seed_base"],
                "status": row["status"],
                "reference_contact_time_s": (row["reference_contact_time_s"]),
                "outcome": score.get("outcome"),
                "first_warning_time_s": score.get("first_warning_time_s"),
                "matched_lead_s": score.get("matched_lead_s"),
                "gap_mae_m": errors.get("gap_mae_m"),
                "closing_speed_mae_mps": errors.get("closing_speed_mae_mps"),
                "fresh_count": errors.get("fresh_count"),
                "unavailable_count": errors.get("unavailable_count"),
                "stale_count": errors.get("stale_count"),
                "error": row["error"],
            }
        )

    write_csv(
        destination / "cases.csv",
        table,
        list(table[0]),
    )


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
    config_path = (
        config_path if config_path.is_absolute() else ROOT / config_path
    ).resolve()

    runtime = provenance()

    runtime["source_sha256"].update(
        {name: sha256(ROOT / name) for name in EXTRA_SOURCES}
    )

    runtime["input_configuration_sha256"] = sha256(config_path)
    runtime["input_configuration_path"] = config_path.relative_to(ROOT).as_posix()

    snapshot = deepcopy(cases + diagnostics)

    manifest = {
        "schema": "drivecheck.m4.machine.v1",
        "stage": "machine-results",
        "status": "running",
        "configuration": config,
        "configuration_sha256": canonical_hash(config),
        "plan_sha256": canonical_hash(snapshot),
        "provenance": runtime,
        "expected_case_count": len(cases),
        "expected_regression_count": len(diagnostics),
        "cases": cases,
        "regression_cases": diagnostics,
        "summaries": [],
        "regression_summaries": [],
        "seed_summaries": [],
        "error": None,
        "artifact_sha256": {},
    }

    destination.mkdir(parents=True, exist_ok=False)
    write_json(destination / "manifest.json", manifest)

    try:
        write_json(
            destination / "configuration.json",
            config,
        )
        write_json(
            destination / "plan.json",
            snapshot,
        )

        for name, context in contexts.items():
            directory = destination / "truth" / name
            directory.mkdir(parents=True)

            fixture = context["fixture"]

            write_records(
                directory / "truth.csv",
                context["truth"],
                TruthSample,
            )

            write_json(
                directory / "configuration.json",
                asdict(fixture.scenario),
            )

            write_json(
                directory / "reference.json",
                {
                    "contact_time_s": (fixture.reference_contact_time_s),
                    "final_gap_m": (fixture.reference_final_gap_m),
                    "basis": fixture.reference_basis,
                    "truth_content_sha256": (context["truth_sha256"]),
                },
            )

        for row in cases + diagnostics:
            directory = destination / "cases" / row["case_id"]

            try:
                directory.mkdir(parents=True)

                context = contexts[row["scenario_id"]]

                data = executor(
                    context,
                    FaultConfig(**row["fault"]),
                    dict(row["policy"]),
                )

                _save_case(
                    directory,
                    context,
                    row,
                    data,
                )

            except Exception as error:
                row.update(
                    status="failed",
                    score=None,
                    errors=None,
                    counts=None,
                    error=f"{type(error).__name__}: {error}",
                )

                try:
                    write_json(
                        directory / "result.json",
                        row,
                    )
                except Exception as save_error:
                    row["error"] += (
                        "; result save failed: "
                        f"{type(save_error).__name__}: "
                        f"{save_error}"
                    )

            write_json(
                destination / "manifest.json",
                manifest,
            )

    except Exception as error:
        _add_error(manifest, error)

    try:
        manifest["summaries"] = summarize(cases)
        manifest["regression_summaries"] = summarize(diagnostics)

        bases = sorted(
            {row["seed_base"] for row in cases if row["seed_base"] is not None}
        )

        manifest["seed_summaries"] = [
            {
                "seed_base": base,
                "summaries": summarize(
                    [row for row in cases if row["seed_base"] == base]
                ),
            }
            for base in bases
        ]

    except Exception as error:
        _add_error(manifest, error)

    _set_status(manifest)

    try:
        _save_table(destination, cases + diagnostics)

        write_json(
            destination / "results.json",
            _payload(manifest),
        )

        manifest["artifact_sha256"] = _artifact_hashes(destination)

    except Exception as error:
        _add_error(manifest, error)
        _set_status(manifest)

        # Changed status-bearing results invalidate previous hashes.
        manifest["artifact_sha256"] = {}

        write_json(
            destination / "results.json",
            _payload(manifest),
        )

    write_json(destination / "manifest.json", manifest)

    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
    )

    args = parser.parse_args(argv)

    try:
        manifest = run(args.config, args.output_dir)
    except (ValueError, OSError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2

    rows = manifest["cases"] + manifest["regression_cases"]

    completed = sum(row["status"] == "complete" for row in rows)

    print(f"machine-results {manifest['status']}: " f"{completed}/{len(rows)} cases")

    if manifest["error"]:
        print(manifest["error"], file=sys.stderr)

    return 0 if manifest["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
