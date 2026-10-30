"""Configuration-driven M2 experiments with complete case accounting."""

import json
import platform
from dataclasses import asdict
from importlib import metadata
from pathlib import Path

from evaluation import aligned_errors, score_case, summarize
from m1 import ROOT, matches, save_plot, sha256, write_json
from motion import first_contact_time, require_finite, sample_truth
from observations import make_observations
from replay import make_decision_times, replay
from reporting import CASE_FILES, save_case, write_report
from scenarios import m1_fixtures
from warning_policy import validate_warning_settings

DEFAULT_CONFIG = ROOT / "configs" / "m2-experiment.json"

SOURCE_FILES = (
    "motion.py",
    "scenarios.py",
    "m1.py",
    "observations.py",
    "warning_policy.py",
    "replay.py",
    "evaluation.py",
    "experiments.py",
    "reporting.py",
    "drivecheck.py",
    "test_motion.py",
    "test_m1.py",
    "test_m2.py",
    "test_replay.py",
    "test_evaluation.py",
    "test_report.py",
    "requirements.txt",
)


def _project_path(value):
    path = Path(value)
    resolved = (path if path.is_absolute() else ROOT / path).resolve()

    if not resolved.is_relative_to(ROOT):
        raise ValueError("paths must remain inside the project")

    return resolved


def _unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError(f"nonstandard JSON number: {value}")


def _keys(value, expected, label):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise ValueError(f"invalid fields in {label}")


def load_configuration(path):
    """Validate the entire experiment before creating output files."""

    path = _project_path(path)
    config = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_unique_keys,
        parse_constant=_reject_constant,
    )

    _keys(
        config,
        {
            "schema_version",
            "fixture_set",
            "scenario_ids",
            "conditions",
            "warning",
            "scoring",
            "decision_clock",
        },
        "configuration",
    )

    if config["schema_version"] != "drivecheck.m2.v1":
        raise ValueError("unsupported experiment schema")
    if config["fixture_set"] != "m1":
        raise ValueError("this runner supports fixture_set m1")
    if config["decision_clock"] != "sample_times_union_arrivals_within_horizon":
        raise ValueError("unsupported decision clock")

    available = {fixture.scenario.scenario_id: fixture for fixture in m1_fixtures()}
    identifiers = config["scenario_ids"]

    if not isinstance(identifiers, list) or not identifiers:
        raise ValueError("scenario_ids must be a nonempty list")
    if any(not isinstance(name, str) or name not in available for name in identifiers):
        raise ValueError("unknown scenario_id")
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("duplicate scenario_id")

    conditions = config["conditions"]

    if not isinstance(conditions, list) or not conditions:
        raise ValueError("conditions must be a nonempty list")

    seen = set()
    allowed = "abcdefghijklmnopqrstuvwxyz0123456789_-"

    for condition in conditions:
        _keys(condition, {"condition_id", "latency_s", "seed"}, "condition")
        name = condition["condition_id"]

        if (
            not isinstance(name, str)
            or not name
            or any(character not in allowed for character in name)
        ):
            raise ValueError("condition_id must use lowercase letters, digits, _ or -")
        if name in seen:
            raise ValueError("duplicate condition_id")

        seen.add(name)
        require_finite("latency_s", condition["latency_s"], minimum=0)

        if condition["seed"] is not None:
            raise ValueError("fixed-latency conditions have no random seed")

    _keys(config["warning"], {"threshold_s", "max_age_s"}, "warning")
    validate_warning_settings(
        config["warning"]["threshold_s"],
        config["warning"]["max_age_s"],
    )

    _keys(
        config["scoring"],
        {"pre_event_window_s", "minimum_useful_lead_s"},
        "scoring",
    )
    window = config["scoring"]["pre_event_window_s"]
    useful = config["scoring"]["minimum_useful_lead_s"]
    require_finite("pre_event_window_s", window, positive=True)
    require_finite("minimum_useful_lead_s", useful, positive=True)

    if useful > window:
        raise ValueError("minimum useful lead exceeds matching window")

    return config, [available[name] for name in identifiers], path


def compute_case(fixture, condition, config):
    """Generate truth, replay observations and evaluate offline."""

    scenario = fixture.scenario
    truth = sample_truth(scenario)

    if not matches(
        first_contact_time(scenario),
        fixture.reference_contact_time_s,
    ) or not matches(truth[-1].gap_m, fixture.reference_final_gap_m):
        raise ValueError("independent M1 fixture mismatch")

    observations = make_observations(truth, condition["latency_s"])
    base_times = [index * scenario.timestep_s for index in range(scenario.sample_count)]
    times = make_decision_times(
        base_times,
        observations,
        scenario.horizon_s,
        scenario_id=scenario.scenario_id,
    )

    replay_result = replay(
        observations,
        times,
        warning_threshold_s=config["warning"]["threshold_s"],
        max_age_s=config["warning"]["max_age_s"],
        scenario_id=scenario.scenario_id,
        horizon_s=scenario.horizon_s,
    )

    score = score_case(
        replay_result.decisions,
        fixture.reference_contact_time_s,
        scenario.horizon_s,
        **config["scoring"],
    )

    return {
        "truth": truth,
        "observations": observations,
        "replay": replay_result,
        "score": score,
        "errors": aligned_errors(replay_result.decisions, scenario),
    }


def _provenance(config_path):
    packages = {
        distribution.metadata.get("Name", "unknown"): distribution.version
        for distribution in metadata.distributions()
    }

    return {
        "generator": "DriveCheck M2",
        "python_version": platform.python_version(),
        "platform": platform.system(),
        "packages": dict(sorted(packages.items())),
        "source_sha256": {name: sha256(ROOT / name) for name in SOURCE_FILES},
        "configuration_path": config_path.relative_to(ROOT).as_posix(),
        "configuration_sha256": sha256(config_path),
        "randomness": "none; fixed observation latency",
    }


def _result_payload(manifest):
    # Artifact hashes stay in the manifest, outside canonical result data.
    return {key: value for key, value in manifest.items() if key != "artifact_sha256"}


def run(config_path=DEFAULT_CONFIG, output_dir="outputs/m2-first"):
    """Return the run manifest; unsuccessful cases remain in its case list."""

    config, fixtures, config_path = load_configuration(config_path)
    output = _project_path(output_dir)
    allowed = (ROOT / "outputs").resolve()

    if allowed != ROOT / "outputs":
        raise ValueError("outputs must not redirect to another directory")
    if output == allowed or not output.is_relative_to(allowed):
        raise ValueError("use a child directory inside outputs")
    if output.exists():
        raise ValueError("use a fresh output directory")

    provenance = _provenance(config_path)
    plan = []

    for fixture in fixtures:
        for condition in config["conditions"]:
            scenario = fixture.scenario
            case = {
                "case_id": f"case-{len(plan) + 1:03d}",
                "scenario_id": scenario.scenario_id,
                "condition_id": condition["condition_id"],
                "status": "pending",
                "horizon_s": scenario.horizon_s,
                "reference_contact_time_s": fixture.reference_contact_time_s,
                "reference_basis": fixture.reference_basis,
                "configuration": asdict(scenario),
                "condition": dict(condition),
                "warning": dict(config["warning"]),
                "scoring": dict(config["scoring"]),
                "score": None,
                "errors": None,
                "error": None,
            }
            plan.append((fixture, condition, case))

    manifest = {
        "schema_version": "drivecheck.m2.v1",
        "status": "running",
        "expected_case_count": len(plan),
        "configuration": config,
        "provenance": provenance,
        "cases": [case for _, _, case in plan],
        "summaries": [],
        "artifact_sha256": {},
        "error": None,
    }

    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "manifest.json", manifest)

    try:
        write_json(output / "configuration.json", config)

        for fixture, condition, case in plan:
            directory = output / case["case_id"]

            try:
                directory.mkdir()
                data = compute_case(fixture, condition, config)

                save_case(
                    directory,
                    fixture,
                    condition,
                    data,
                    config["warning"],
                )

                case.update(
                    {
                        "status": "complete",
                        "score": data["score"],
                        "errors": data["errors"],
                        "observation_count": len(data["observations"]),
                        "decision_count": len(data["replay"].decisions),
                        "ignored_older_arrival_count": data[
                            "replay"
                        ].ignored_older_arrival_count,
                        "beyond_horizon_arrival_count": data[
                            "replay"
                        ].beyond_horizon_arrival_count,
                    }
                )
                write_json(directory / "result.json", case)

                if any(not (directory / name).is_file() for name in CASE_FILES):
                    raise ValueError("required case artifact is missing")

            except Exception as error:
                case.update(
                    {
                        "status": "failed",
                        "score": None,
                        "errors": None,
                        "error": f"{type(error).__name__}: {error}",
                    }
                )

                try:
                    write_json(directory / "result.json", case)
                except Exception as save_error:
                    case["error"] += f"; result save also failed: {save_error}"

            write_json(output / "manifest.json", manifest)

        manifest["summaries"] = summarize(manifest["cases"])
        completed = sum(case["status"] == "complete" for case in manifest["cases"])
        final_status = (
            "complete"
            if completed == len(plan)
            else "partial" if completed else "failed"
        )

        report_view = dict(manifest, status=final_status)
        write_json(output / "results.json", _result_payload(report_view))
        write_report(output, report_view)
        manifest["status"] = final_status

    except Exception as error:
        manifest["status"] = "failed"
        manifest["error"] = f"{type(error).__name__}: {error}"

    finally:
        write_json(output / "results.json", _result_payload(manifest))

        artifact_paths = [
            output / name
            for name in (
                "configuration.json",
                "results.json",
                "cases.csv",
                "report.html",
            )
        ]
        artifact_paths.extend(
            output / case["case_id"] / name
            for case in manifest["cases"]
            for name in CASE_FILES
        )

        try:
            manifest["artifact_sha256"] = {
                path.relative_to(output).as_posix(): sha256(path)
                for path in artifact_paths
                if path.is_file()
            }
        except Exception as error:
            manifest["status"] = "failed"
            manifest["error"] = f"Artifact hashing failed: {error}"
            manifest["artifact_sha256"] = {}
            write_json(output / "results.json", _result_payload(manifest))

        write_json(output / "manifest.json", manifest)

    return manifest
