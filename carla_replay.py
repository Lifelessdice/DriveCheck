"""Replay a declared CARLA-shaped export on CPU with the shared warning policy."""

import argparse
import csv
from dataclasses import asdict, fields
import hashlib
from html import escape
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import sys

from carla_import import ImportPolicy, parse_export
from c1_replay import replay_with_estimator
from evaluation import aligned_errors, score_case
from faults import FaultConfig, inject_faults
from motion import TruthSample
from observations import Observation
from replay import make_decision_times
from warning_policy import Decision, validate_warning_settings


ROOT = Path(__file__).resolve().parent
CONFIG_SCHEMA = "drivecheck.carla-replay.v1"
RUN_SCHEMA = "drivecheck.carla-run.v1"
SOURCE_FILES = (
    "carla_import.py", "carla_replay.py", "c1_estimators.py", "c1_replay.py",
    "faults.py", "replay.py", "observations.py", "warning_policy.py",
    "evaluation.py", "motion.py", "requirements-lock.txt",
)
FRESH_REASONS = {"not_closing", "ttc_clear", "ttc_warning", "contact_or_overlap"}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
                    encoding="utf-8", newline="\n")


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError(f"non-finite JSON constant: {value}")


def _keys(value, expected, label):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise ValueError(f"{label} requires exactly: {', '.join(sorted(expected))}")


def load_configuration(content):
    """Validate the complete settings before any output directory is created."""
    data = json.loads(content.decode("utf-8-sig"), object_pairs_hook=_unique,
                      parse_constant=_reject_constant)
    _keys(data, {"schema_version", "mapping", "fault", "warning", "scoring", "methods"},
          "replay configuration")
    if data["schema_version"] != CONFIG_SCHEMA:
        raise ValueError("unsupported replay schema_version")
    for key, record_type in (("mapping", ImportPolicy), ("fault", FaultConfig)):
        value = data[key]
        allowed = {field.name for field in fields(record_type)}
        if not isinstance(value, dict) or not set(value).issubset(allowed):
            raise ValueError(f"{key} must contain only {sorted(allowed)}")
    mapping = ImportPolicy(**data["mapping"])
    fault = FaultConfig(**data["fault"])
    _keys(data["warning"], {"warning_threshold_s", "max_age_s"}, "warning")
    validate_warning_settings(**data["warning"])
    _keys(data["scoring"], {"pre_event_window_s", "minimum_useful_lead_s"}, "scoring")
    score_case([], None, 0.0, **data["scoring"])
    methods = data["methods"]
    if (not isinstance(methods, list) or not methods
            or not all(isinstance(method, str) and method in {"raw", "age_projection"}
                       for method in methods) or len(set(methods)) != len(methods)):
        raise ValueError("methods must be a unique nonempty list of raw/age_projection")
    effective = {"schema_version": CONFIG_SCHEMA, "mapping": asdict(mapping),
                 "fault": asdict(fault), "warning": dict(data["warning"]),
                 "scoring": dict(data["scoring"]), "methods": list(methods)}
    json.dumps(effective, allow_nan=False)
    return effective, mapping, fault


def _project_path(value, *, existing_file=False):
    path = Path(value)
    path = path if path.is_absolute() else ROOT / path
    lexical = Path(os.path.abspath(path))
    resolved = lexical.resolve()
    if (not lexical.is_relative_to(ROOT) or resolved != lexical
            or not resolved.is_relative_to(ROOT)):
        raise ValueError("paths must stay in the project without redirects")
    if existing_file and not resolved.is_file():
        raise ValueError(f"input file does not exist: {resolved.name}")
    return resolved


def _preflight(input_path, config_path, output_dir):
    source = _project_path(input_path, existing_file=True)
    configuration = _project_path(config_path, existing_file=True)
    destination = _project_path(output_dir)
    allowed = ROOT / "outputs"
    if allowed.resolve() != allowed:
        raise ValueError("project outputs must not redirect")
    if (destination == allowed or not destination.is_relative_to(allowed)
            or destination.exists() or destination.is_symlink()
            or source.is_relative_to(destination) or configuration.is_relative_to(destination)):
        raise ValueError("use a fresh separate subdirectory inside project outputs")
    for parent in destination.parents:
        if parent.exists() and not parent.is_dir():
            raise ValueError("output parent is not a directory")
        if parent == ROOT:
            break
    input_bytes, config_bytes = source.read_bytes(), configuration.read_bytes()
    effective, mapping, fault = load_configuration(config_bytes)
    trajectory = parse_export(input_bytes, policy=mapping)
    if source.read_bytes() != input_bytes or configuration.read_bytes() != config_bytes:
        raise ValueError("inputs changed during preflight")
    names = ["manifest.json", "results.json", "source-export.json", "replay-config.json",
             "effective-settings.json", "truth.csv", "frame-map.csv", "observations.csv",
             "fault-audit.json", "clock.json", "report.html", "timeline.png"]
    names += [f"{method}-{suffix}" for method in effective["methods"]
              for suffix in ("decisions.csv", "records.json")]
    for name in names:
        planned = destination / name
        if planned.resolve() != planned or planned in {source, configuration}:
            raise ValueError("output plan redirects or overlaps an input")
    source_hashes = {name: digest(_project_path(name, existing_file=True))
                     for name in SOURCE_FILES}
    return (source, configuration, destination, input_bytes, config_bytes,
            effective, fault, trajectory, source_hashes)


def write_records(path, rows, record_type):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=[field.name for field in fields(record_type)])
        writer.writeheader()
        writer.writerows(asdict(row) for row in rows)


def _identity(trajectory, readings, times, effective):
    value = {"truth": [asdict(row) for row in trajectory.samples],
             "observations": [asdict(row) for row in readings], "clock": list(times),
             "settings": effective, "reference": trajectory.reference_contact_time_s}
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False,
                                    separators=(",", ":")).encode("utf-8")).hexdigest()


def save_plot(path, trajectory, outputs, settings):
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    fig = Figure(figsize=(10, 9), layout="constrained")
    FigureCanvasAgg(fig)
    axes = fig.subplots(3, 1, sharex=True)
    fig.suptitle(f"{trajectory.scenario_id} | {trajectory.provenance['kind']}")
    axes[0].plot([row.time_s for row in trajectory.samples],
                 [row.gap_m for row in trajectory.samples], color="black", marker=".",
                 label="Imported clean gap (joined export samples)")
    axes[0].axhline(0, color="gray", linewidth=1)
    for method, output in outputs.items():
        decisions = output.replay.decisions
        times = [row.decision_time_s for row in decisions]
        fresh = [row.reason in FRESH_REASONS for row in decisions]
        axes[0].step(times, [row.gap_m if ok else float("nan")
                            for row, ok in zip(decisions, fresh)],
                     where="post", marker=".", label=method)
        ttc = [row.ttc_s if ok and row.ttc_s is not None else float("nan")
               for row, ok in zip(decisions, fresh)]
        ttc_line, = axes[1].step(times, ttc, where="post", marker=".", label=method)
        warnings = [row for row in decisions if row.is_warning]
        if warnings:
            axes[1].scatter([row.decision_time_s for row in warnings],
                            [row.ttc_s for row in warnings], s=75, marker="D",
                            facecolors="none", edgecolors=ttc_line.get_color(),
                            zorder=4, label=f"{method} warning decisions")
        axes[2].step(times, [row.observation_age_s if row.observation_age_s is not None
                            else float("nan") for row in decisions], where="post", label=method)
    axes[1].axhline(settings["warning_threshold_s"], color="red", linestyle="--",
                   label="Experimental TTC threshold")
    axes[2].axhline(settings["max_age_s"], color="red", linestyle="--", label="Source-age limit")
    plot_horizon = max(trajectory.horizon_s, 0.1)
    for ax, label in zip(axes, ("Bumper gap (m)", "TTC (s)", "Original source age (s)")):
        ax.set_ylabel(label)
        ax.grid(alpha=0.25)
        ax.axvline(trajectory.horizon_s, color="gray", linestyle=":", label="Captured horizon")
        if trajectory.reference_contact_time_s is not None:
            ax.axvline(trajectory.reference_contact_time_s, color="purple", linestyle="-.",
                       label="Recorded ego-to-lead collision")
        ax.legend(fontsize=8, loc="best")
        ax.set_xlim(-0.025 * plot_horizon, 1.025 * plot_horizon)
        ax.margins(y=0.12)
    axes[-1].set_xlabel("Scenario / decision time since first exported frame (s)")
    try:
        fig.savefig(path, format="png", dpi=120)
    finally:
        fig.clear()


def _display(value):
    return "unavailable" if value is None else str(value)


def save_report(path, manifest, plot_exists):
    rows = []
    for method, result in manifest["methods"].items():
        score, errors = result["score"] or {}, result["errors"] or {}
        cells = (method, result["status"], score.get("outcome", "unscored"),
                 score.get("first_warning_time_s"), score.get("matched_lead_s"),
                 errors.get("gap_mae_m"), errors.get("closing_speed_mae_mps"),
                 errors.get("fresh_count"), errors.get("unavailable_count"),
                 errors.get("stale_count"), result.get("error") or "")
        rows.append("<tr>" + "".join(f"<td>{escape(_display(value))}</td>"
                                     for value in cells) + "</tr>")
    links = ["manifest.json", "source-export.json", "replay-config.json", "effective-settings.json", "truth.csv",
             "frame-map.csv", "observations.csv", "fault-audit.json", "clock.json", "results.json"]
    links += [f"{method}-{suffix}" for method in manifest["methods"]
              for suffix in ("decisions.csv", "records.json")]
    evidence = " · ".join(f"<a href='{name}'>{name}</a>" for name in links
                          if (path.parent / name).is_file())
    figure = ("<figure><img src='timeline.png' alt='Imported gap, used TTC and source age' "
              "style='width:100%;height:auto'><figcaption>Truth lines join exported samples; "
              "offline error truth is piecewise-linear interpolation. Collision markers come "
              "from recorded events, not geometric gap crossing.</figcaption></figure>"
              if plot_exists else "<p>Plot unavailable; inspect the recorded error.</p>")
    text = ("<!doctype html><html lang='en'><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>Imported longitudinal replay</title><style>body{font:16px/1.5 system-ui;"
            "max-width:1150px;margin:30px auto;padding:0 18px}table{border-collapse:collapse;"
            "width:100%}td,th{border:1px solid #bbb;padding:7px} .table{overflow:auto}"
            "pre{white-space:pre-wrap;overflow-wrap:anywhere}</style>"
            f"<h1>{escape(manifest['scenario_id'])}: imported CPU replay</h1>"
            f"<p>Run status: <strong>{escape(manifest['status'])}</strong>. Declared source kind: "
            f"<strong>{escape(manifest['source_provenance']['kind'])}</strong>.</p>"
            "<p>These observations are controlled sensor proxies derived from actor ground truth, "
            "not radar/perception measurements. A source declaration does not authenticate a "
            "simulator capture. The supplied examples are hand-authored contract fixtures.</p>"
            f"<p>Recorded pair contact: {escape(_display(manifest['reference_contact_time_s']))} s; "
            f"horizon: {manifest['horizon_s']} s. Each method scores this same single episode; "
            "methods are not independent replications.</p><div class='table'><table><tr>"
            "<th>Method</th><th>Status</th><th>Outcome</th><th>First warning (s)</th>"
            "<th>Matched lead (s)</th><th>Gap MAE (m)</th><th>Closing MAE (m/s)</th>"
            "<th>Fresh rows</th><th>Unavailable</th><th>Stale</th><th>Error</th></tr>"
            + "".join(rows) + "</table></div>" + figure + "<h2>Saved evidence</h2><p>"
            + evidence + "</p><h2>Settings, capture declarations and limits</h2><pre>"
            + escape(json.dumps({key: manifest[key] for key in (
                "source_provenance", "settings", "mapping", "warnings", "error")}
                | {"plot_error": manifest.get("plot_error")},
                indent=2, allow_nan=False))
            + "</pre><p>Bounding-box projection approximates bumper separation on a fixed axis. "
            "Interpolation is not exact continuous simulator truth; event timing is limited by "
            "captured frame resolution. Warnings are passive and do not alter the export. "
            "No real-world safety validation or actual simulator execution is established by "
            "these synthetic fixtures.</p></html>")
    path.write_text(text, encoding="utf-8", newline="\n")


def run(input_path, config_path, output_dir):
    """Validate before writes; retain every requested method and runtime failure."""
    (source, configuration, destination, input_bytes, config_bytes, effective,
     fault, trajectory, source_hashes) = _preflight(input_path, config_path, output_dir)
    manifest = {"schema_version": RUN_SCHEMA, "status": "running", "error": None,
                "scenario_id": trajectory.scenario_id, "horizon_s": trajectory.horizon_s,
                "reference_contact_time_s": trajectory.reference_contact_time_s,
                "source_provenance": trajectory.provenance, "settings": effective,
                "mapping": {"policy": asdict(trajectory.mapping_policy),
                            "time_origin_s": trajectory.time_origin_s,
                            "reference_basis": "first recorded ego-to-lead collision in captured frames",
                            "ignored_other_collision_count": trajectory.ignored_collision_count,
                            "truth_between_frames": "piecewise-linear position/speed; no extrapolation",
                            "observations": "ground-truth-derived sensor proxies; not radar"},
                "warnings": list(trajectory.warnings),
                "provenance": {"python": platform.python_version(), "platform": platform.system(),
                               "input_sha256": hashlib.sha256(input_bytes).hexdigest(),
                               "config_sha256": hashlib.sha256(config_bytes).hexdigest(),
                               "source_sha256": source_hashes,
                               "packages": dict(sorted((dist.metadata["Name"], dist.version)
                                                       for dist in metadata.distributions()
                                                       if dist.metadata.get("Name")))},
                "methods": {method: {"status": "pending", "score": None, "errors": None,
                                     "counts": None, "error": None}
                            for method in effective["methods"]}}
    destination.mkdir(parents=True)
    write_json(destination / "manifest.json", manifest)
    outputs = {}
    try:
        (destination / "source-export.json").write_bytes(input_bytes)
        (destination / "replay-config.json").write_bytes(config_bytes)
        write_json(destination / "effective-settings.json", effective)
        write_records(destination / "truth.csv", trajectory.samples, TruthSample)
        with (destination / "frame-map.csv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(("sample_id", "source_frame_id", "source_elapsed_seconds", "time_s"))
            writer.writerows((row.sample_id, frame, elapsed, row.time_s)
                             for row, frame, elapsed in zip(trajectory.samples,
                                 trajectory.source_frame_ids, trajectory.source_elapsed_seconds))
        readings, audit = inject_faults(trajectory.samples, fault)
        readings = tuple(readings)
        times = tuple(make_decision_times([row.time_s for row in trajectory.samples], readings,
                      trajectory.horizon_s, scenario_id=trajectory.scenario_id))
        identity = _identity(trajectory, readings, times, effective)
        manifest["shared_input_sha256"] = identity
        write_records(destination / "observations.csv", readings, Observation)
        write_json(destination / "fault-audit.json", audit)
        write_json(destination / "clock.json", times)
        for method, result in manifest["methods"].items():
            try:
                if _identity(trajectory, readings, times, effective) != identity:
                    raise ValueError("shared replay inputs changed")
                output = replay_with_estimator(readings, times, **effective["warning"],
                           scenario_id=trajectory.scenario_id, horizon_s=trajectory.horizon_s,
                           method=method)
                if (_identity(trajectory, readings, times, effective) != identity
                        or [row.decision_time_s for row in output.replay.decisions] != list(times)
                        or len(output.records) != len(times)):
                    raise ValueError("method changed shared inputs or omitted decision records")
                result["score"] = score_case(output.replay.decisions,
                    trajectory.reference_contact_time_s, trajectory.horizon_s, **effective["scoring"])
                result["errors"] = aligned_errors(output.replay.decisions, trajectory,
                                                   truth_at_time=trajectory.truth_at)
                result["counts"] = {"decision_count": len(times),
                    "ignored_older_arrival_count": output.replay.ignored_older_arrival_count,
                    "beyond_horizon_arrival_count": output.replay.beyond_horizon_arrival_count}
                write_records(destination / f"{method}-decisions.csv", output.replay.decisions, Decision)
                write_json(destination / f"{method}-records.json", [asdict(row) for row in output.records])
                result["status"] = "complete"
                outputs[method] = output
            except Exception as error:
                result.update(status="failed", score=None, errors=None, counts=None,
                              error=f"{type(error).__name__}: {error}")
    except Exception as error:
        manifest["error"] = f"{type(error).__name__}: {error}"
        for result in manifest["methods"].values():
            if result["status"] == "pending":
                result.update(status="failed", error="Shared-input/export failure: " + manifest["error"])
    complete = sum(result["status"] == "complete" for result in manifest["methods"].values())
    manifest["status"] = ("complete" if complete == len(manifest["methods"])
                          else "partial" if complete else "failed")
    try:
        save_plot(destination / "timeline.png", trajectory, outputs, effective["warning"])
    except Exception as error:
        manifest["plot_error"] = f"{type(error).__name__}: {error}"
        manifest["status"] = "partial" if complete else "failed"
    try:
        if source.read_bytes() != input_bytes or configuration.read_bytes() != config_bytes:
            raise ValueError("source/configuration changed during replay")
        write_json(destination / "results.json", manifest)
        save_report(destination / "report.html", manifest, (destination / "timeline.png").is_file())
    except Exception as error:
        manifest["error"] = f"{type(error).__name__}: {error}"
        manifest["status"] = "partial" if complete else "failed"
    # Presentation failures must not leave an earlier complete result behind.
    write_json(destination / "results.json", manifest)
    manifest["artifact_sha256"] = {path.name: digest(path) for path in sorted(destination.iterdir())
                                  if path.is_file() and path.name != "manifest.json"}
    write_json(destination / "manifest.json", manifest)
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = run(args.input, args.config, args.output_dir)
    except (ValueError, OSError, TypeError) as error:
        print(f"Import/replay preflight failed: {error}", file=sys.stderr)
        return 2
    print(f"Imported replay {result['status']}; {len(result['methods'])} methods retained")
    print(f"Report: {(args.output_dir / 'report.html').resolve()}")
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
