"""Frozen paired CPU comparison of raw held state and source-age projection."""

from collections import Counter
from copy import deepcopy
from dataclasses import asdict
import json
import math
from pathlib import Path
import platform

from c1_replay import replay_with_estimator
from evaluation import aligned_errors, score_case
from faults import FaultConfig, inject_faults
from m1 import sha256
from m3_study import canonical_hash, make_context, write_csv, write_json, write_records
from motion import first_contact_time, require_finite, sample_truth, truth_at
from observations import Observation
from release_config import is_stochastic, load_configuration as load_m4_configuration
from release_runner import prepare as prepare_m4
from replay import make_decision_times, replay
from scenarios import Fixture
from stop_and_go import (
    first_stop_go_contact_time, sample_stop_go_truth, stop_go_truth_at,
)
from warning_policy import Decision


ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG = ROOT / "configs" / "c1-comparison.json"
SCHEMA = "drivecheck.c1.v1"
METHODS = ("raw", "age_projection")
TOLERANCE = 1e-12
SOURCE_FILES = (
    "c1_comparison.py", "c1_estimators.py", "c1_replay.py", "warning_policy.py",
    "replay.py", "evaluation.py", "faults.py", "motion.py", "stop_and_go.py",
    "scenarios.py", "release_config.py", "release_runner.py", "m3_study.py",
    "m3_regression.py", "m1.py", "observations.py", "requirements-lock.txt",
)


def _keys(value, fields, label):
    if not isinstance(value, dict) or set(value) != set(fields):
        raise ValueError(f"invalid fields in {label}")


def _unique_keys(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _reject_constant(value):
    raise ValueError(f"nonstandard JSON number: {value}")


def _contained_file(value, label):
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a project-relative path")
    path = (ROOT / value).resolve()
    if not path.is_relative_to(ROOT) or not path.is_file():
        raise ValueError(f"{label} must identify an existing contained file")
    return path


def validate_configuration(config):
    """Reject ambiguous splits and preserve every baseline experimental policy."""
    _keys(config, {
        "schema_version", "baseline_config", "alternative",
        "development_seed_bases", "evaluation_seed_bases", "evaluation_transform",
        "include_diagnostics",
    }, "comparison")
    if config["schema_version"] != SCHEMA or config["alternative"] != "age_projection":
        raise ValueError("unsupported comparison schema or alternative")
    _contained_file(config["baseline_config"], "baseline_config")
    for name in ("development_seed_bases", "evaluation_seed_bases"):
        values = config[name]
        if (not isinstance(values, list) or not values
                or any(isinstance(v, bool) or not isinstance(v, int) or v < 0 for v in values)
                or len(set(values)) != len(values)):
            raise ValueError(f"{name} requires distinct nonnegative integer bases")
    if set(config["development_seed_bases"]) & set(config["evaluation_seed_bases"]):
        raise ValueError("development and evaluation seed bases must be disjoint")
    development_streams = {base + offset for base in config["development_seed_bases"]
                           for offset in (1, 2, 3, 4)}
    evaluation_streams = {base + offset for base in config["evaluation_seed_bases"]
                          for offset in (1, 2, 3, 4)}
    if development_streams & evaluation_streams:
        raise ValueError("derived development and evaluation stream seeds must be disjoint")
    transform = config["evaluation_transform"]
    _keys(transform, {"length_scale", "time_scale"}, "evaluation_transform")
    for name, value in transform.items():
        require_finite(name, value, positive=True)
    if transform["length_scale"] == 1 and transform["time_scale"] == 1:
        raise ValueError("evaluation must use different physical configurations")
    if type(config["include_diagnostics"]) is not bool:
        raise ValueError("include_diagnostics must be boolean")
    return deepcopy(config)


def load_configuration(path=DEFAULT_CONFIG):
    path = Path(path).resolve()
    if not path.is_relative_to(ROOT) or not path.is_file():
        raise ValueError("comparison config must be an existing contained file")
    return validate_configuration(json.loads(
        path.read_text(encoding="utf-8"), object_pairs_hook=_unique_keys,
        parse_constant=_reject_constant,
    ))


def _scaled_context(context, length_scale, time_scale):
    """Scale independent references analytically before evaluating any method."""
    original = context["fixture"]
    settings = asdict(original.scenario)
    for key, value in list(settings.items()):
        if key == "scenario_id":
            settings[key] = f"eval_{value}"
        elif key.endswith("_mps2"):
            settings[key] = value * length_scale / time_scale ** 2
        elif key.endswith("_mps"):
            settings[key] = value * length_scale / time_scale
        elif key.endswith("_m"):
            settings[key] = value * length_scale
        elif key.endswith("_s"):
            settings[key] = value * time_scale
    scenario = type(original.scenario)(**settings)
    event = original.reference_contact_time_s
    fixture = Fixture(
        scenario=scenario,
        reference_contact_time_s=None if event is None else event * time_scale,
        reference_final_gap_m=original.reference_final_gap_m * length_scale,
        reference_basis=(
            f"Independent similarity transform x'=L*x, t'=T*t with "
            f"L={length_scale}, T={time_scale}; speeds scale L/T, acceleration L/T^2. "
            f"The original analytic reference is: {original.reference_basis}"
        ),
    )
    functions = (
        (sample_truth, truth_at, first_contact_time)
        if context["family"] == "lead_braking"
        else (sample_stop_go_truth, stop_go_truth_at, first_stop_go_contact_time)
    )
    return make_context(context["family"], fixture, *functions)


def prepare_plan(config):
    """Freeze both physical splits and validate references without warning runs."""
    config = validate_configuration(config)
    baseline = load_m4_configuration(_contained_file(config["baseline_config"], "baseline_config"))
    entries = []
    diagnostic_contexts = None
    diagnostic_rows = None
    for split in ("development", "evaluation"):
        split_config = deepcopy(baseline)
        for condition in split_config["conditions"]:
            fault = FaultConfig(**condition["fault"])
            condition["seed_bases"] = (
                list(config[f"{split}_seed_bases"]) if is_stochastic(fault) else [None]
            )
        contexts, rows, diagnostics = prepare_m4(split_config)
        if split == "development":
            diagnostic_contexts, diagnostic_rows = contexts, diagnostics
        for index, row in enumerate(rows, 1):
            context = contexts[row["scenario_id"]]
            if split == "evaluation":
                context = _scaled_context(context, **config["evaluation_transform"])
            fixture = context["fixture"]
            row = deepcopy(row)
            row.update(
                case_id=f"{split}-{index:03d}", split=split,
                scenario_id=fixture.scenario.scenario_id,
                horizon_s=fixture.scenario.horizon_s,
                configuration=asdict(fixture.scenario),
                reference_contact_time_s=fixture.reference_contact_time_s,
                reference_final_gap_m=fixture.reference_final_gap_m,
                reference_basis=fixture.reference_basis,
                truth_sha256=context["truth_sha256"],
            )
            row["artifact_dir"] = f"cases/{row['case_id']}"
            row["truth_file"] = f"{row['artifact_dir']}/truth.csv"
            entries.append({"row": row, "context": context})
    if config["include_diagnostics"]:
        for index, row in enumerate(diagnostic_rows, 1):
            row = deepcopy(row)
            row.update(case_id=f"diagnostic-{index:03d}", split="diagnostic")
            row["artifact_dir"] = f"cases/{row['case_id']}"
            row["truth_file"] = f"{row['artifact_dir']}/truth.csv"
            entries.append({"row": row, "context": diagnostic_contexts[row["scenario_id"]]})
    identities = [entry["row"]["case_id"] for entry in entries]
    if len(set(identities)) != len(identities):
        raise ValueError("duplicate comparison case identity")
    dev = {canonical_hash({k: v for k, v in e["row"]["configuration"].items()
                           if k != "scenario_id"}) for e in entries
           if e["row"]["split"] == "development"}
    evaluation = {canonical_hash({k: v for k, v in e["row"]["configuration"].items()
                                  if k != "scenario_id"}) for e in entries
                  if e["row"]["split"] == "evaluation"}
    if dev & evaluation:
        raise ValueError("physical scenario configurations overlap between splits")
    return entries


def _method_summary(cases, method):
    complete = [case for case in cases if case["methods"][method]["status"] == "complete"]
    positive = [case for case in complete if case["reference_contact_time_s"] is not None]
    negative = [case for case in complete if case["reference_contact_time_s"] is None]
    outcomes = Counter(case["methods"][method]["score"]["outcome"] for case in complete)
    rates = {}
    for key, count, denominator in (
        ("useful", outcomes["useful"], len(positive)),
        ("late", outcomes["late"], len(positive)),
        ("missed", outcomes["missed"], len(positive)),
        ("without_useful_warning", outcomes["late"] + outcomes["missed"], len(positive)),
        ("false_warning_episode", outcomes["false_warning"], len(negative)),
    ):
        rates[key] = {"numerator": count, "denominator": denominator,
                      "rate": count / denominator if denominator else None}
    return {
        "planned": len(cases), "complete": len(complete),
        "failed": len(cases) - len(complete),
        "planned_positive_count": sum(c["reference_contact_time_s"] is not None for c in cases),
        "planned_negative_count": sum(c["reference_contact_time_s"] is None for c in cases),
        "positive_count": len(positive), "negative_count": len(negative),
        "outcomes": dict(outcomes), "rates": rates,
    }


def _change(raw, alternative, *, higher_is_better=False):
    if raw is None or alternative is None:
        return {"raw": raw, "age_projection": alternative,
                "delta": None, "direction": "not_comparable"}
    delta = alternative - raw
    if math.isclose(raw, alternative, rel_tol=TOLERANCE, abs_tol=TOLERANCE):
        direction = "unchanged"
    else:
        direction = "win" if ((delta > 0) == higher_is_better) else "loss"
    return {"raw": raw, "age_projection": alternative, "delta": delta,
            "direction": direction}


def pair_changes(case):
    methods = case["methods"]
    if any(methods[name]["status"] != "complete" for name in METHODS):
        return {"execution": {"direction": "not_comparable", "delta": None,
                              "raw": methods["raw"]["status"],
                              "age_projection": methods["age_projection"]["status"]}}
    raw, alt = methods["raw"], methods["age_projection"]
    changes = {name: _change(raw["errors"][name], alt["errors"][name])
               for name in ("gap_mae_m", "closing_speed_mae_mps")}
    if case["reference_contact_time_s"] is None:
        changes["false_warning"] = _change(
            int(raw["score"]["outcome"] == "false_warning"),
            int(alt["score"]["outcome"] == "false_warning"),
        )
    else:
        for name in ("missed", "late"):
            changes[name] = _change(int(raw["score"]["outcome"] == name),
                                    int(alt["score"]["outcome"] == name))
        changes["without_useful_warning"] = _change(
            int(raw["score"]["outcome"] != "useful"),
            int(alt["score"]["outcome"] != "useful"),
        )
        both_useful = raw["score"]["outcome"] == alt["score"]["outcome"] == "useful"
        changes["useful_lead_s"] = _change(
            raw["score"]["matched_lead_s"] if both_useful else None,
            alt["score"]["matched_lead_s"] if both_useful else None,
            higher_is_better=True,
        )
    return changes


def _summarize_group(cases):
    directions = {}
    for case in cases:
        for metric, change in case["changes"].items():
            counts = directions.setdefault(metric, {key: 0 for key in (
                "win", "loss", "unchanged", "not_comparable")})
            counts[change["direction"]] += 1
    return {
        "planned_pairs": len(cases), "planned_method_records": len(cases) * 2,
        "complete_pairs": sum(c["status"] == "complete" for c in cases),
        "partial_pairs": sum(c["status"] == "partial" for c in cases),
        "failed_pairs": sum(c["status"] == "failed" for c in cases),
        "methods": {method: _method_summary(cases, method) for method in METHODS},
        "directional_changes": directions,
    }


def summarize_pairs(cases):
    result = {split: _summarize_group([c for c in cases if c["split"] == split])
              for split in ("development", "evaluation", "diagnostic")}
    result["groups"] = []
    for split, family, condition in sorted({
        (c["split"], c["family"], c["condition_id"]) for c in cases
    }):
        members = [c for c in cases if (c["split"], c["family"], c["condition_id"])
                   == (split, family, condition)]
        result["groups"].append({"split": split, "family": family,
                                 "condition_id": condition, **_summarize_group(members)})
    result["comparison_tolerance"] = {"relative": TOLERANCE, "absolute": TOLERANCE}
    return result


def _input_identity(truth, readings, times, fault, policy, reference):
    return canonical_hash({
        "truth": [asdict(s) for s in truth],
        "observations": [asdict(s) for s in readings], "decision_times_s": list(times),
        "fault": fault, "policy": policy, "reference_contact_time_s": reference,
    })


def _run_pair(entry, destination, method_runner):
    case, context = deepcopy(entry["row"]), entry["context"]
    case["methods"] = {method: {"status": "pending", "score": None, "errors": None,
                                "counts": None, "error": None, "artifacts": {}}
                       for method in METHODS}
    directory = destination / case["artifact_dir"]
    directory.mkdir(parents=True)
    truth = context["truth"]
    policy = case["policy"]
    try:
        readings, audit = inject_faults(truth, FaultConfig(**case["fault"]))
        readings = tuple(readings)
        times = tuple(
            [index * 0.5 for index in range(13)] if case["split"] == "diagnostic"
            else make_decision_times(
                [sample.time_s for sample in truth], readings, case["horizon_s"],
                scenario_id=case["scenario_id"],
            )
        )
        reference = case["reference_contact_time_s"]
        identity = _input_identity(truth, readings, times, case["fault"], policy, reference)
        case.update(
            input_sha256=identity,
            observation_sha256=canonical_hash([asdict(r) for r in readings]),
            clock_sha256=canonical_hash(list(times)),
        )
        write_records(directory / "truth.csv", truth, type(truth[0]))
        write_records(directory / "observations.csv", readings, Observation)
        write_json(directory / "audit.json", audit)
        write_json(directory / "clock.json", list(times))
        for method in METHODS:
            result = case["methods"][method]
            try:
                before = _input_identity(truth, readings, times, case["fault"], policy, reference)
                if before != identity:
                    raise ValueError("shared inputs were modified by a preceding method")
                output = method_runner(
                    readings, times, warning_threshold_s=policy["warning_threshold_s"],
                    max_age_s=policy["max_age_s"], scenario_id=case["scenario_id"],
                    horizon_s=case["horizon_s"], method=method,
                )
                if _input_identity(truth, readings, times, case["fault"], policy, reference) != identity:
                    raise ValueError("method changed frozen shared inputs")
                if [d.decision_time_s for d in output.replay.decisions] != list(times):
                    raise ValueError("method changed the decision clock")
                if len(output.records) != len(times):
                    raise ValueError("method omitted source/estimate records")
                if method == "raw":
                    baseline = replay(
                        readings, times, policy["warning_threshold_s"], policy["max_age_s"],
                        scenario_id=case["scenario_id"], horizon_s=case["horizon_s"],
                    )
                    if output.replay != baseline:
                        raise ValueError("raw adapter differs from the usable baseline")
                result["score"] = score_case(
                    output.replay.decisions, reference, case["horizon_s"],
                    pre_event_window_s=policy["pre_event_window_s"],
                    minimum_useful_lead_s=policy["minimum_useful_lead_s"],
                )
                result["errors"] = aligned_errors(
                    output.replay.decisions, context["fixture"].scenario,
                    truth_at_time=context["truth_at_time"],
                )
                result["counts"] = {
                    "decision_count": len(times),
                    "ignored_older_arrival_count": output.replay.ignored_older_arrival_count,
                    "beyond_horizon_arrival_count": output.replay.beyond_horizon_arrival_count,
                }
                decisions = directory / f"{method}-decisions.csv"
                records = directory / f"{method}-records.json"
                write_records(decisions, output.replay.decisions, Decision)
                write_json(records, [asdict(r) for r in output.records])
                result["artifacts"] = {"decisions": decisions.relative_to(destination).as_posix(),
                                       "records": records.relative_to(destination).as_posix()}
                result["status"] = "complete"
            except Exception as error:
                result.update(status="failed", score=None, errors=None, counts=None,
                              error=f"{type(error).__name__}: {error}")
        if all(case["methods"][m]["status"] == "complete" for m in METHODS):
            a, b = (case["methods"][m] for m in METHODS)
            if a["counts"] != b["counts"]:
                raise ValueError("methods changed source scheduling or observation coverage")
    except Exception as error:
        for result in case["methods"].values():
            result.update(status="failed", score=None, errors=None, counts=None,
                          error=f"{type(error).__name__}: {error}")
    complete = sum(result["status"] == "complete" for result in case["methods"].values())
    case["status"] = "complete" if complete == 2 else "partial" if complete else "failed"
    case["changes"] = pair_changes(case)
    write_json(directory / "metrics.json", case)
    return case


def _flat_rows(cases):
    rows = []
    for case in cases:
        for method in METHODS:
            result = case["methods"][method]
            score, errors = result["score"] or {}, result["errors"] or {}
            rows.append({
                "case_id": case["case_id"], "split": case["split"],
                "scenario_id": case["scenario_id"], "family": case["family"],
                "condition_id": case["condition_id"], "seed_base": case["seed_base"],
                "method": method, "status": result["status"],
                "reference_contact_time_s": case["reference_contact_time_s"],
                "outcome": score.get("outcome"), "matched_lead_s": score.get("matched_lead_s"),
                "gap_mae_m": errors.get("gap_mae_m"),
                "closing_speed_mae_mps": errors.get("closing_speed_mae_mps"),
                "fresh_count": errors.get("fresh_count"), "error": result["error"],
            })
    return rows


def run(config_path=DEFAULT_CONFIG, output_dir=None, *, method_runner=None):
    """Execute the complete preregistered comparison; retain failed pairs."""
    config_path = Path(config_path).resolve()
    config = load_configuration(config_path)
    entries = prepare_plan(config)
    runner = replay_with_estimator if method_runner is None else method_runner
    if not callable(runner):
        raise ValueError("method_runner must be callable or None")
    if output_dir is None:
        raise ValueError("a fresh output directory is required")
    destination = Path(output_dir).resolve()
    output_root = (ROOT / "outputs").resolve()
    if (not destination.is_relative_to(output_root) or destination == output_root
            or destination.exists()):
        raise ValueError("output must be a new directory strictly inside project outputs")
    source_files = [ROOT / name for name in SOURCE_FILES]
    source_files.extend([config_path, _contained_file(config["baseline_config"], "baseline_config")])
    source_hashes = {p.relative_to(ROOT).as_posix(): sha256(p) for p in source_files}
    planned_rows = [entry["row"] for entry in entries]
    selection = {
        "method": "age_projection", "tunable_parameters": {},
        "question": "Does projecting eligible old gap address the observed held-gap latency failure?",
        "selection_basis": "M4 development fixed-delay failure; selected before evaluation outcomes",
        "config_sha256": canonical_hash(config), "plan_sha256": canonical_hash(planned_rows),
        "source_sha256": source_hashes,
        "holdout_limits": "Scaled analytic synthetic relatives, not new real traffic families; no significance claim",
        "comparison_tolerance": {"relative": TOLERANCE, "absolute": TOLERANCE},
    }
    destination.mkdir(parents=True)
    write_json(destination / "configuration.json", config)
    write_json(destination / "case-plan.json", planned_rows)
    # Persist the method, split, full inputs and source identity before any outcomes.
    write_json(destination / "frozen-selection.json", selection)
    manifest = {
        "schema": SCHEMA, "status": "running", "config": config,
        "config_sha256": canonical_hash(config), "frozen_selection": selection,
        "source_sha256": source_hashes,
        "runtime": {"python": platform.python_version(), "platform": platform.system()},
        "cases": [], "summary": None, "error": None, "artifact_sha256": {},
    }
    write_json(destination / "manifest.json", manifest)
    try:
        for entry in entries:
            manifest["cases"].append(_run_pair(entry, destination, runner))
            write_json(destination / "manifest.json", manifest)
        manifest["summary"] = summarize_pairs(manifest["cases"])
        manifest["status"] = (
            "complete" if all(c["status"] == "complete" for c in manifest["cases"]) else "partial"
        )
        write_json(destination / "summary.json", manifest["summary"])
        flat = _flat_rows(manifest["cases"])
        write_csv(destination / "cases.csv", flat, list(flat[0]))
    except Exception as error:
        manifest["status"] = "failed"
        manifest["error"] = f"{type(error).__name__}: {error}"
        raise
    finally:
        manifest["artifact_sha256"] = {
            p.relative_to(destination).as_posix(): sha256(p)
            for p in sorted(destination.rglob("*"))
            if p.is_file() and p != destination / "manifest.json"
        }
        write_json(destination / "manifest.json", manifest)
    return manifest
