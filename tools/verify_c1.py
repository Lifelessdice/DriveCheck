"""Independently audit saved C1 hashes, causal decisions and metric evidence."""

import argparse
from collections import Counter
import csv
from dataclasses import asdict, fields
import hashlib
from html.parser import HTMLParser
import json
import math
from pathlib import Path
from urllib.parse import unquote, urlsplit

from evaluation import score_case
from faults import FaultConfig
from motion import Scenario, TruthSample, first_contact_time, truth_at
from observations import Observation, validate_observations
from release_config import fixture_registry, is_stochastic
from stop_and_go import StopGoScenario, first_stop_go_contact_time, stop_go_truth_at
from warning_policy import Decision


ROOT = Path(__file__).resolve().parents[1]
METHODS = ("raw", "age_projection")


def _check(condition, message):
    if not condition:
        raise ValueError(message)


def _digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode("utf-8")).hexdigest()


def _contained(root, name):
    _check(isinstance(name, str) and bool(name), "invalid artifact path")
    relative = Path(name)
    result = (root / relative).resolve()
    _check(not relative.is_absolute() and result.is_relative_to(root),
           f"artifact path escapes root: {name}")
    return result


def _read(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            _check(key not in result, f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def reject(value):
        raise ValueError(f"non-finite JSON value: {value}")

    result = json.loads(path.read_text("utf-8"), object_pairs_hook=unique,
                        parse_constant=reject)
    _canonical(result)  # Also rejects exponent overflow such as 1e999.
    return result


def _records(path, record_type):
    expected = [field.name for field in fields(record_type)]
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        _check(reader.fieldnames == expected, f"CSV schema mismatch: {path.name}")
        rows = []
        for values in reader:
            row = {}
            _check(set(values) == set(expected), "invalid CSV row shape")
            for key, value in values.items():
                if value == "":
                    row[key] = None
                elif key in {"scenario_id", "reason"}:
                    row[key] = value
                elif key == "is_warning":
                    _check(value in {"True", "False"}, "invalid warning boolean")
                    row[key] = value == "True"
                elif key == "sample_id":
                    row[key] = int(value)
                else:
                    row[key] = float(value)
                    _check(math.isfinite(row[key]), "non-finite CSV value")
            rows.append(row)
    return rows


def _inventory(directory):
    result = {}
    for path in sorted(directory.rglob("*")):
        _check(not path.is_symlink(), "symbolic links are not evidence artifacts")
        _check(path.resolve().is_relative_to(directory), "redirected evidence artifact")
        if path.is_file():
            result[path.relative_to(directory).as_posix()] = _digest(path)
    return result


def _coverage(config, cases):
    development, evaluation = (config[f"{split}_seed_bases"]
                               for split in ("development", "evaluation"))
    _check(not set(development) & set(evaluation), "overlapping split seed bases")
    streams = [{base + offset for base in bases for offset in range(1, 5)}
               for bases in (development, evaluation)]
    _check(not streams[0] & streams[1], "overlapping split RNG streams")
    baseline = _read(_contained(ROOT, config["baseline_config"]))
    expected = Counter()
    for split, bases in (("development", development), ("evaluation", evaluation)):
        for scenario_id in baseline["scenario_ids"]:
            name = scenario_id if split == "development" else f"eval_{scenario_id}"
            for condition in baseline["conditions"]:
                seeds = bases if is_stochastic(FaultConfig(**condition["fault"])) else [None]
                for base in seeds:
                    expected[(split, name, condition["condition_id"], base)] += 1
    if config["include_diagnostics"]:
        for name in ("delay_0s", "delay_1s", "delay_1p5s", "delay_2s", "delay_2p5s"):
            expected[("diagnostic", "latency_regression", name, None)] += 1
    observed = Counter((c["split"], c["scenario_id"], c["condition_id"], c["seed_base"])
                       for c in cases)
    _check(observed == expected, "full planned split/case/seed coverage disagrees")
    configs = [{_canonical({k: v for k, v in c["configuration"].items()
                           if k != "scenario_id"}) for c in cases if c["split"] == split}
               for split in ("development", "evaluation")]
    _check(not configs[0] & configs[1], "physical configurations overlap between splits")
    return baseline


def _scenario(case, config, baseline):
    """Check saved physical settings against independently scaled source fixtures."""
    if case["split"] == "diagnostic":
        scenario = Scenario("latency_regression", 30.0, 10.0, 5.0,
                            timestep_s=1.0, sample_count=7)
        expected_reference = 6.0
        expected_final_gap = 0.0
        delays = {"delay_0s": 0.0, "delay_1s": 1.0, "delay_1p5s": 1.5,
                  "delay_2s": 2.0, "delay_2p5s": 2.5}
        delay = delays[case["condition_id"]]
        expected_fault = FaultConfig(mode="clean" if delay == 0 else "latency", latency_s=delay)
        policy = {"warning_threshold_s": 2.0, "max_age_s": 3.0,
                  "pre_event_window_s": 3.0, "minimum_useful_lead_s": 1.0,
                  "decision_clock": "fixed 0.5 s"}
    else:
        original_id = case["scenario_id"]
        if case["split"] == "evaluation":
            original_id = original_id.removeprefix("eval_")
        family, fixture = fixture_registry()[original_id]
        _check(case["family"] == family, "scenario family changed")
        settings = asdict(fixture.scenario)
        expected_reference = fixture.reference_contact_time_s
        expected_final_gap = fixture.reference_final_gap_m
        condition = next(c for c in baseline["conditions"]
                         if c["condition_id"] == case["condition_id"])
        seed_base = case["seed_base"]
        seeds = {} if seed_base is None else {
            name: seed_base + offset for offset, name in enumerate(
                ("gap_seed", "closing_seed", "latency_seed", "dropout_seed"), start=1)}
        expected_fault = FaultConfig(**condition["fault"], **seeds)
        if case["split"] == "evaluation":
            length, time = (config["evaluation_transform"][name]
                            for name in ("length_scale", "time_scale"))
            settings["scenario_id"] = "eval_" + settings["scenario_id"]
            for key in settings:
                if key.endswith("_mps2"):
                    settings[key] = settings[key] * length / time ** 2
                elif key.endswith("_mps"):
                    settings[key] = settings[key] * length / time
                elif key.endswith("_m"):
                    settings[key] *= length
                elif key.endswith("_s"):
                    settings[key] *= time
            if expected_reference is not None:
                expected_reference *= time
            expected_final_gap *= length
        scenario = type(fixture.scenario)(**settings)
        policy = {"warning_threshold_s": baseline["warning"]["threshold_s"],
                  "max_age_s": baseline["warning"]["max_age_s"],
                  **baseline["scoring"],
                  "decision_clock": "source schedule plus in-horizon arrivals"}
    _check(asdict(scenario) == case["configuration"], "physical configuration changed")
    _check(scenario.horizon_s == case["horizon_s"], "horizon changed")
    _check(expected_reference == case["reference_contact_time_s"], "reference changed")
    _check(expected_final_gap == case["reference_final_gap_m"], "final-gap reference changed")
    _check(asdict(expected_fault) == case["fault"], "fault profile/seed mapping changed")
    _check(policy == case["policy"], "warning/scoring policy changed")
    if isinstance(scenario, StopGoScenario):
        evaluator, solver = stop_go_truth_at, first_stop_go_contact_time
    else:
        evaluator, solver = truth_at, first_contact_time
    actual_event = solver(scenario)
    _check((actual_event is None and expected_reference is None) or
           (actual_event is not None and expected_reference is not None and
            math.isclose(actual_event, expected_reference, rel_tol=0, abs_tol=1e-9)),
           "independent event/model check failed")
    return scenario, evaluator


def _expected_decision(source, now, method, policy):
    base = asdict(Decision(now))
    if source is None:
        return base, None
    age = now - source["measurement_time_s"]
    base.update({key: source[key] for key in (
        "sample_id", "measurement_time_s", "arrival_time_s", "gap_m", "closing_speed_mps")})
    base["observation_age_s"] = age
    if age > policy["max_age_s"]:
        base["reason"] = "stale"
        return base, None
    gap, closing = source["gap_m"], source["closing_speed_mps"]
    if method == "age_projection":
        gap -= closing * age
    _check(math.isfinite(gap), "non-finite projected state")
    estimate = {"source": source, "estimate_time_s": now,
                "gap_m": gap, "closing_speed_mps": closing}
    base["gap_m"] = gap
    if gap <= 0:
        base.update(ttc_s=0.0, is_warning=True, reason="contact_or_overlap")
    elif closing <= 0:
        base["reason"] = "not_closing"
    else:
        ttc = gap / closing
        _check(math.isfinite(ttc), "non-finite TTC")
        warning = ttc <= policy["warning_threshold_s"]
        base.update(ttc_s=ttc, is_warning=warning,
                    reason="ttc_warning" if warning else "ttc_clear")
    return base, estimate


def _case(directory, case, config, baseline):
    _check(case["status"] == "complete", "incomplete pair in acceptance evidence")
    _check(set(case["methods"]) == set(METHODS), "missing comparison method")
    folder = _contained(directory, case["artifact_dir"])
    _check(_read(folder / "metrics.json") == case, "case metrics disagree with manifest")
    scenario, evaluator = _scenario(case, config, baseline)
    truth = _records(folder / "truth.csv", TruthSample)
    expected_truth = [asdict(evaluator(scenario, i * scenario.timestep_s, sample_id=i))
                      for i in range(scenario.sample_count)]
    _check(truth == expected_truth, "truth CSV differs from the checked model")
    # CSV has no integer/float type metadata; retain model-native JSON identity
    # after checking every saved value against its independently evaluated row.
    truth = expected_truth
    _check(_canonical(truth) == case["truth_sha256"], "truth identity changed")
    readings = _records(folder / "observations.csv", Observation)
    validate_observations([Observation(**r) for r in readings], case["scenario_id"],
                          case["horizon_s"])
    audit = _read(folder / "audit.json")
    _check(len(audit) == len(truth), "fault audit omits source samples")
    by_id = {r["sample_id"]: r for r in readings}
    native_readings = []
    fault = FaultConfig(**case["fault"])
    for source, row in zip(truth, audit):
        _check(row["sample_id"] == source["sample_id"] and
               row["measurement_time_s"] == source["time_s"], "audit source changed")
        _check(type(row["dropped"]) is bool, "invalid dropout state")
        _check(row["scenario_id"] == source["scenario_id"] and
               0 <= row["u_latency"] < 1 and 0 <= row["u_dropout"] < 1 and
               row["gap_error_m"] == fault.gap_sigma_m * row["z_gap"] and
               row["closing_error_mps"] == fault.closing_sigma_mps * row["z_closing"] and
               row["delay_s"] == fault.latency_s + fault.latency_jitter_s * row["u_latency"] and
               row["arrival_time_s"] == source["time_s"] + row["delay_s"] and
               row["dropped"] == (row["u_dropout"] < fault.dropout_probability),
               "fault audit disagrees with the declared profile")
        if row["dropped"]:
            _check(source["sample_id"] not in by_id, "dropped source was synthesized")
        else:
            observation = by_id.get(source["sample_id"])
            _check(observation is not None, "retained source reading is missing")
            expected_observation = {
                "scenario_id": source["scenario_id"], "sample_id": source["sample_id"],
                "measurement_time_s": source["time_s"], "arrival_time_s": row["arrival_time_s"],
                "gap_m": source["gap_m"] + row["gap_error_m"],
                "closing_speed_mps": source["closing_speed_mps"] + row["closing_error_mps"],
            }
            _check(observation == expected_observation,
                   "observation differs from its source/fault audit")
            native_readings.append(expected_observation)
    _check(len(native_readings) == len(readings), "unaccounted source reading")
    readings = native_readings
    times = _read(folder / "clock.json")
    expected_clock = ([i * 0.5 for i in range(13)] if case["split"] == "diagnostic" else
                      sorted({0.0, case["horizon_s"], *(r["time_s"] for r in truth),
                              *(r["arrival_time_s"] for r in readings
                                if r["arrival_time_s"] <= case["horizon_s"])}))
    _check(times == expected_clock, "paired clock changed")
    _check(_canonical(readings) == case["observation_sha256"] and
           _canonical(times) == case["clock_sha256"], "stream/clock identity changed")
    _check(_canonical({"truth": truth, "observations": readings, "decision_times_s": times,
                       "fault": case["fault"], "policy": case["policy"],
                       "reference_contact_time_s": case["reference_contact_time_s"]})
           == case["input_sha256"], "paired input identity changed")
    selected, latest, ignored, next_index = [], None, 0, 0
    queue = sorted(readings, key=lambda r: (r["arrival_time_s"], r["sample_id"]))
    for now in times:
        while next_index < len(queue) and queue[next_index]["arrival_time_s"] <= now:
            arriving = queue[next_index]
            next_index += 1
            if latest is None or arriving["measurement_time_s"] > latest["measurement_time_s"]:
                latest = arriving
            else:
                ignored += 1
        selected.append(latest)
    counts = {"decision_count": len(times), "ignored_older_arrival_count": ignored,
              "beyond_horizon_arrival_count": sum(
                  r["arrival_time_s"] > case["horizon_s"] for r in readings)}
    for method in METHODS:
        result = case["methods"][method]
        _check(result["status"] == "complete" and result["error"] is None,
               "incomplete method in acceptance evidence")
        decision_path = f"{case['artifact_dir']}/{method}-decisions.csv"
        record_path = f"{case['artifact_dir']}/{method}-records.json"
        _check(result["artifacts"] == {"decisions": decision_path, "records": record_path},
               "method artifact identity changed")
        decisions = _records(_contained(directory, decision_path), Decision)
        records = _read(_contained(directory, record_path))
        _check(len(decisions) == len(records) == len(times), "decision/record row omitted")
        gap_errors, closing_errors, unavailable, stale = [], [], 0, 0
        for now, source, decision, record in zip(times, selected, decisions, records):
            expected, estimate = _expected_decision(source, now, method, case["policy"])
            _check(decision == expected, f"causal state/TTC mismatch: {case['case_id']}/{method}")
            _check(record == {"source": source, "estimate": estimate, "decision": expected},
                   "source/estimate record disagrees with causal decision")
            if expected["reason"] == "unavailable":
                unavailable += 1
            elif expected["reason"] == "stale":
                stale += 1
            else:
                current = evaluator(scenario, now)
                gap_errors.append(abs(expected["gap_m"] - current.gap_m))
                closing_errors.append(abs(expected["closing_speed_mps"] - current.closing_speed_mps))
        score = score_case([Decision(**d) for d in decisions], case["reference_contact_time_s"],
                           case["horizon_s"], case["policy"]["pre_event_window_s"],
                           case["policy"]["minimum_useful_lead_s"])
        count = len(gap_errors)
        errors = {"alignment": "truth at decision_time_s",
                  "weighting": "equal weight per fresh decision row; full horizon",
                  "fresh_count": count, "unavailable_count": unavailable, "stale_count": stale,
                  "gap_mae_m": math.fsum(gap_errors) / count if count else None,
                  "closing_speed_mae_mps": math.fsum(closing_errors) / count if count else None}
        _check(result["counts"] == counts, "causal coverage counts disagree")
        _check(result["score"] == score, "independent warning score disagrees")
        _check(result["errors"] == errors, "decision-aligned errors disagree")
    return len(times) * 2


class _Links(HTMLParser):
    def __init__(self, root):
        super().__init__()
        self.root = root
        self.count = 0

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if name not in {"href", "src"} or not value or value.startswith("#"):
                continue
            url = urlsplit(value)
            _check(not url.scheme and not url.netloc, "report contains an external link")
            path = (self.root / "report" / unquote(url.path)).resolve()
            _check(path.is_relative_to(self.root) and path.is_file(), "broken/escaping report link")
            self.count += 1


def verify(run_dir):
    """Return acceptance checks or raise ValueError for incomplete/tampered evidence."""
    directory = Path(run_dir)
    directory = (directory if directory.is_absolute() else ROOT / directory).resolve()
    _check(directory.is_relative_to(ROOT) and directory.is_dir(), "run must remain inside project")
    manifest = _read(directory / "manifest.json")
    _check(manifest.get("schema") == "drivecheck.c1.v1" and
           manifest.get("status") == "complete" and manifest.get("error") is None,
           "comparison is not complete")
    inventory = _inventory(directory)
    machine = {name: digest for name, digest in inventory.items()
               if name not in {"manifest.json", "report-manifest.json"}
               and not name.startswith("report/")}
    _check(machine == manifest.get("artifact_sha256"), "machine artifact inventory/hash mismatch")
    for name in manifest["artifact_sha256"]:
        _contained(directory, name)
    config = manifest["config"]
    _check(_read(directory / "configuration.json") == config and
           _canonical(config) == manifest["config_sha256"], "frozen configuration changed")
    selection = _read(directory / "frozen-selection.json")
    plan = _read(directory / "case-plan.json")
    _check(selection == manifest["frozen_selection"] and
           selection["method"] == "age_projection" and selection["tunable_parameters"] == {} and
           selection["config_sha256"] == manifest["config_sha256"] and
           selection["plan_sha256"] == _canonical(plan) and
           selection["source_sha256"] == manifest["source_sha256"], "frozen selection changed")
    for name, expected in manifest["source_sha256"].items():
        _check(_digest(_contained(ROOT, name)) == expected, f"checkout source changed: {name}")
    cases = manifest["cases"]
    _check(isinstance(cases, list) and bool(cases), "missing paired cases")
    _check(len({c["case_id"] for c in cases}) == len(cases), "duplicate pair identity")
    _check(len(plan) == len(cases), "planned case omitted")
    for expected, actual in zip(plan, cases):
        _check(all(actual.get(k) == v for k, v in expected.items()
                   if k not in {"status", "score", "errors", "counts", "error"}),
               "saved pair disagrees with the frozen plan")
    baseline = _coverage(config, cases)
    rows = sum(_case(directory, case, config, baseline) for case in cases)
    _check(_read(directory / "summary.json") == manifest["summary"], "saved summaries disagree")
    for split in ("development", "evaluation", "diagnostic"):
        group = [c for c in cases if c["split"] == split]
        summary = manifest["summary"][split]
        _check(summary["planned_pairs"] == summary["complete_pairs"] == len(group) and
               summary["planned_method_records"] == len(group) * 2 and
               summary["partial_pairs"] == summary["failed_pairs"] == 0,
               "summary hides incomplete/planned pairs")
        for method in METHODS:
            item = summary["methods"][method]
            outcomes = Counter(c["methods"][method]["score"]["outcome"] for c in group)
            positive = sum(c["reference_contact_time_s"] is not None for c in group)
            _check(item["planned"] == item["complete"] == len(group) and item["failed"] == 0 and
                   item["positive_count"] == item["planned_positive_count"] == positive and
                   item["negative_count"] == item["planned_negative_count"] == len(group) - positive and
                   item["outcomes"] == dict(outcomes), "summary episode accounting disagrees")
    report_files = {name: digest for name, digest in inventory.items() if name.startswith("report/")}
    links = 0
    if report_files or "report-manifest.json" in inventory:
        package = _read(directory / "report-manifest.json")
        _check(package.get("schema") == "drivecheck.c1.report.v1" and
               package.get("status") == package.get("machine_status") == "complete" and
               package.get("error") is None and
               package.get("machine_manifest_sha256") == inventory["manifest.json"] and
               package.get("artifact_sha256") == report_files, "report package identity/hash mismatch")
        parser = _Links(directory)
        parser.feed((directory / "report" / "report.html").read_text("utf-8"))
        links = parser.count
    return {"status": "complete", "paired_cases": len(cases), "method_records": len(cases) * 2,
            "decision_rows": rows, "machine_hashes": len(machine),
            "report_hashes": len(report_files), "local_links": links,
            "split_counts": dict(Counter(c["split"] for c in cases))}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(verify(args.run_dir), indent=2, sort_keys=True))
        return 0
    except (ValueError, OSError, KeyError, TypeError, OverflowError) as error:
        print(f"C1 evidence audit failed: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
