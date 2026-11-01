"""Render verified saved M4 machine evidence as a local report package."""

import argparse
import csv
from dataclasses import asdict
import hashlib
from html import escape
from html.parser import HTMLParser
import json
import math
from pathlib import Path
import platform
import re
import sys
from urllib.parse import unquote, urlsplit

from evaluation import summarize
from faults import FaultConfig
from m3_study import canonical_hash, write_json
from motion import Scenario
from release_config import (
    ROOT,
    _reject_constant,
    _unique_keys,
    build_plan,
)
from release_runner import DIAGNOSTIC_POLICY


def read_json(path):
    value = json.loads(
        path.read_text("utf-8"),
        object_pairs_hook=_unique_keys,
        parse_constant=_reject_constant,
    )

    def check(item):
        if isinstance(item, float) and not math.isfinite(item):
            raise ValueError("JSON contains a non-finite numeric value")

        if isinstance(item, dict):
            for child in item.values():
                check(child)
        elif isinstance(item, list):
            for child in item:
                check(child)

    check(value)
    return value


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def contained(root, relative):
    path = Path(relative)
    resolved = (root / path).resolve()

    if path.is_absolute() or not resolved.is_relative_to(root.resolve()):
        raise ValueError(f"artifact escapes run directory: {relative}")

    return resolved


def read_csv(path):
    with path.open(
        encoding="utf-8",
        newline="",
    ) as stream:
        return list(csv.DictReader(stream))


def check_case_csv(directory, rows):
    records = read_csv(directory / "cases.csv")
    by_id = {row["case_id"]: row for row in records}

    if len(by_id) != len(records) or set(by_id) != {row["case_id"] for row in rows}:
        raise ValueError("CSV case inventory disagrees with JSON")

    for row in rows:
        score = row["score"] or {}
        errors = row["errors"] or {}

        expected = {
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

        formatted = {
            key: "" if value is None else str(value) for key, value in expected.items()
        }

        if by_id[row["case_id"]] != formatted:
            raise ValueError("CSV case values disagree with JSON: " f"{row['case_id']}")


def load_machine(run_dir):
    directory = Path(run_dir)
    directory = (directory if directory.is_absolute() else ROOT / directory).resolve()

    allowed = ROOT / "outputs"

    if (
        allowed.resolve() != allowed
        or directory == allowed
        or not directory.is_relative_to(allowed)
    ):
        raise ValueError("run directory must remain under project outputs")

    manifest = read_json(directory / "manifest.json")

    if (
        manifest.get("schema") != "drivecheck.m4.machine.v1"
        or manifest.get("stage") != "machine-results"
        or manifest.get("status") not in {"complete", "partial", "failed"}
    ):
        raise ValueError("unsupported or unfinished machine manifest")

    hashes = manifest.get("artifact_sha256")

    if not isinstance(hashes, dict) or not hashes:
        raise ValueError("machine artifact verification is unavailable")

    for relative, expected in hashes.items():
        path = contained(directory, relative)

        if not path.is_file() or digest(path) != expected:
            raise ValueError(f"machine artifact hash mismatch: {relative}")

    for required in (
        "configuration.json",
        "plan.json",
        "results.json",
        "cases.csv",
    ):
        if required not in hashes:
            raise ValueError(
                "required machine artifact is not verified: " f"{required}"
            )

    saved = read_json(directory / "results.json")

    expected = {
        key: value for key, value in manifest.items() if key != "artifact_sha256"
    }

    if saved != expected:
        raise ValueError("manifest and saved results disagree")

    config = read_json(directory / "configuration.json")

    if (
        config != manifest["configuration"]
        or canonical_hash(config) != manifest["configuration_sha256"]
    ):
        raise ValueError("configuration snapshot disagrees with manifest")

    rows = manifest["cases"] + manifest["regression_cases"]

    if (
        len(manifest["cases"]) != manifest["expected_case_count"]
        or len(manifest["regression_cases"]) != manifest["expected_regression_count"]
    ):
        raise ValueError("declared case count mismatch")

    expected_main = build_plan(config)

    actual_main = {row["case_id"]: row for row in manifest["cases"]}

    if len(actual_main) != len(expected_main) or set(actual_main) != {
        row["case_id"] for row in expected_main
    }:
        raise ValueError("configured matrix coverage is incomplete")

    changing = {
        "status",
        "score",
        "errors",
        "counts",
        "error",
    }

    for expected_row in expected_main:
        actual_row = actual_main[expected_row["case_id"]]

        if any(
            actual_row.get(key) != value
            for key, value in expected_row.items()
            if key not in changing
        ):
            raise ValueError("configured case metadata mismatch")

    diagnostics = manifest["regression_cases"]

    if {row["case_id"] for row in diagnostics} != {
        f"regression-{index:03d}" for index in range(1, 6)
    }:
        raise ValueError("the five diagnostic arms are required")

    delays = {
        f"regression-{index:03d}": delay
        for index, delay in enumerate(
            (0, 1, 1.5, 2, 2.5),
            start=1,
        )
    }

    diagnostic_scenario = asdict(
        Scenario(
            scenario_id="latency_regression",
            initial_gap_m=30.0,
            ego_speed_mps=10.0,
            lead_speed_mps=5.0,
            timestep_s=1.0,
            sample_count=7,
        )
    )

    for row in diagnostics:
        delay = delays[row["case_id"]]

        expected_fault = asdict(
            FaultConfig(
                mode="clean" if delay == 0 else "latency",
                latency_s=delay,
            )
        )

        if (
            row["section"] != "regression"
            or row["policy"] != DIAGNOSTIC_POLICY
            or row["fault"] != expected_fault
            or row["configuration"] != diagnostic_scenario
            or row["scenario_id"] != "latency_regression"
            or row["reference_contact_time_s"] != 6
            or row["horizon_s"] != 6
        ):
            raise ValueError("diagnostic contract mismatch")

    identifiers = [row["case_id"] for row in rows]

    if len(set(identifiers)) != len(identifiers):
        raise ValueError("duplicate case ID")

    if any(
        not re.fullmatch(
            r"(?:case|regression)-\d{3,}",
            name,
        )
        for name in identifiers
    ):
        raise ValueError("unsafe case ID")

    plan = read_json(directory / "plan.json")

    if canonical_hash(plan) != manifest["plan_sha256"]:
        raise ValueError("resolved plan hash mismatch")

    planned = {row["case_id"]: row for row in plan}

    if len(planned) != len(plan) or set(planned) != set(identifiers):
        raise ValueError("saved plan and case IDs disagree")

    for row in rows:
        result_path = f"cases/{row['case_id']}/result.json"

        if (
            result_path in hashes
            and read_json(contained(directory, result_path)) != row
        ):
            raise ValueError(
                "case result disagrees with manifest: " f"{row['case_id']}"
            )

        for key, value in planned[row["case_id"]].items():
            if key not in changing and row.get(key) != value:
                raise ValueError(
                    "case metadata differs from plan: " f"{row['case_id']}/{key}"
                )

        if row["status"] == "complete":
            required = [row["truth_file"]] + [
                f"cases/{row['case_id']}/{name}"
                for name in (
                    "observations.csv",
                    "fault-audit.csv",
                    "decisions.csv",
                    "result.json",
                )
            ]

            if any(name not in hashes for name in required):
                raise ValueError("complete case lacks verified evidence")

        elif any(row.get(name) is not None for name in ("score", "errors", "counts")):
            raise ValueError("unscored case contains numeric results")

    if summarize(manifest["cases"]) != manifest["summaries"]:
        raise ValueError("main summary disagrees with saved rows")

    if summarize(manifest["regression_cases"]) != manifest["regression_summaries"]:
        raise ValueError("diagnostic summary disagrees with saved rows")

    complete = sum(row["status"] == "complete" for row in rows)

    status = (
        "complete"
        if complete == len(rows) and manifest["error"] is None
        else "partial" if complete else "failed"
    )

    if manifest["status"] != status:
        raise ValueError("overall machine status contradicts execution evidence")

    check_case_csv(directory, rows)

    return directory, manifest


def number(value):
    if value in (None, ""):
        return float("nan")

    result = float(value)

    if not math.isfinite(result):
        raise ValueError("CSV contains a non-finite numeric value")

    return result


def plot_case(path, row, directory):
    import matplotlib

    matplotlib.use("Agg")

    import matplotlib.pyplot as plt

    truth = read_csv(contained(directory, row["truth_file"]))

    decisions = read_csv(directory / "cases" / row["case_id"] / "decisions.csv")

    times = [number(item["decision_time_s"]) for item in decisions]

    fresh = {
        "not_closing",
        "ttc_clear",
        "ttc_warning",
        "contact_or_overlap",
    }

    gap = [
        number(item["gap_m"]) if item["reason"] in fresh else float("nan")
        for item in decisions
    ]

    ttc = [number(item["ttc_s"]) for item in decisions]

    age = [number(item["observation_age_s"]) for item in decisions]

    figure, axes = plt.subplots(
        3,
        1,
        figsize=(10, 8),
        sharex=True,
    )

    try:
        axes[0].plot(
            [number(item["time_s"]) for item in truth],
            [number(item["gap_m"]) for item in truth],
            "o",
            label="Clean truth samples",
        )

        axes[0].step(
            times,
            gap,
            where="post",
            label="Fresh held gap at decision time",
        )

        axes[0].axhline(
            0,
            color="black",
            linewidth=0.7,
        )
        axes[0].set_ylabel("Bumper gap (m)")

        axes[1].step(
            times,
            ttc,
            where="post",
            label="Saved TTC",
        )

        axes[1].axhline(
            row["policy"]["warning_threshold_s"],
            linestyle="--",
            label="TTC threshold",
        )

        warning = [
            index
            for index, item in enumerate(decisions)
            if item["is_warning"] == "True"
        ]

        axes[1].scatter(
            [times[index] for index in warning],
            [ttc[index] for index in warning],
            marker="x",
            label="Warning decisions",
            zorder=4,
        )

        axes[1].set_ylabel("TTC (s)")
        axes[1].set_ylim(bottom=-0.15)

        axes[2].plot(
            times,
            age,
            "o-",
            markersize=3,
            label="Measurement age",
        )

        axes[2].axhline(
            row["policy"]["max_age_s"],
            linestyle="--",
            label="Age limit",
        )

        stale = [
            index for index, item in enumerate(decisions) if item["reason"] == "stale"
        ]

        axes[2].scatter(
            [times[index] for index in stale],
            [age[index] for index in stale],
            marker="x",
            label="Stale decision",
        )

        missing = [
            times[index]
            for index, item in enumerate(decisions)
            if item["reason"] == "unavailable"
        ]

        axes[2].scatter(
            missing,
            [0] * len(missing),
            marker="|",
            s=90,
            label="Unavailable marker (age undefined)",
        )

        axes[2].set_ylabel("Observation age (s)")
        axes[2].set_xlabel("Decision / source time (s)")

        event = row["reference_contact_time_s"]

        for axis in axes:
            if event is not None:
                axis.axvline(
                    event,
                    color="red",
                    linestyle=":",
                    label="Independent contact",
                )

                axis.axvspan(
                    event,
                    row["horizon_s"],
                    color="grey",
                    alpha=0.08,
                )

            axis.set_xlim(0, row["horizon_s"])
            axis.grid(alpha=0.2)
            axis.legend(fontsize=7, loc="best")

        figure.suptitle(
            f"{row['case_id']}: "
            f"{row['scenario_id']} / "
            f"{row['condition_id']} / "
            f"base {row.get('seed_base')}"
        )

        figure.text(
            0.01,
            0.005,
            "Truth shown as saved samples. Shading after contact "
            "is virtual geometry, not impact dynamics.",
            fontsize=8,
        )

        figure.tight_layout(rect=(0, 0.025, 1, 0.96))

        figure.savefig(path, dpi=130)

    finally:
        plt.close(figure)


def display(value):
    return "N/A" if value is None else escape(str(value))


def table(headers, rows):
    headings = "".join(f"<th>{escape(name)}</th>" for name in headers)

    body = "".join(
        "<tr>" + "".join(f"<td>{display(value)}</td>" for value in row) + "</tr>"
        for row in rows
    )

    return (
        "<table><thead><tr>"
        + headings
        + "</tr></thead><tbody>"
        + body
        + "</tbody></table>"
    )


def fraction(value):
    counts = f"{value['numerator']}/" f"{value['denominator']}"

    if value["value"] is None:
        return counts + " (N/A)"

    return counts + f" ({100 * value['value']:.1f}%)"


def summary_table(rows):
    groups = summarize(rows)

    records = []

    for group in groups:
        records.append(
            [
                group["condition_id"],
                (f"{group['planned']['positive']}/" f"{group['planned']['negative']}"),
                (f"{group['scored']['positive']}/" f"{group['scored']['negative']}"),
                *[
                    fraction(group["rates"][name])
                    for name in (
                        "useful",
                        "late",
                        "missed",
                        "without_useful_warning",
                        "false_warning_episode",
                    )
                ],
            ]
        )

    return table(
        [
            "Condition",
            "Planned P/N",
            "Scored P/N",
            "Useful",
            "Late",
            "Missed",
            "Without useful",
            "False-warning episodes",
        ],
        records,
    )


def selected(row, all_plots):
    return row["status"] == "complete" and (
        all_plots
        or row["section"] == "regression"
        or row["condition_id"] == "clean"
        or (
            row["condition_id"] == "latency_strong"
            and row["seed_base"] == 100
            and row["reference_contact_time_s"] is not None
        )
    )


def diagnostic_observed(directory, manifest):
    rows = manifest["regression_cases"]

    text = "<h3>Observed diagnostic outcomes</h3>" + table(
        [
            "Delay (s)",
            "Execution",
            "Outcome",
            "First warning (s)",
            "Matched lead (s)",
        ],
        [
            [
                row["fault"]["latency_s"],
                row["status"],
                (row["score"] or {}).get("outcome"),
                (row["score"] or {}).get("first_warning_time_s"),
                (row["score"] or {}).get("matched_lead_s"),
            ]
            for row in rows
        ],
    )

    strong = next(row for row in rows if row["fault"]["latency_s"] == 2.5)

    if strong["status"] != "complete":
        return text + (
            "<p>Observed strongest-arm trace unavailable: "
            "execution is incomplete.</p>"
        )

    case_dir = directory / "cases" / strong["case_id"]

    decisions = read_csv(case_dir / "decisions.csv")
    observations = read_csv(case_dir / "observations.csv")

    last = next(
        (item for item in decisions if number(item["decision_time_s"]) == 6),
        None,
    )

    alarming = next(
        (item for item in observations if item["sample_id"] == "4"),
        None,
    )

    if last is None or alarming is None:
        return text + (
            "<p>Required saved diagnostic evidence is unavailable; "
            "inspect the raw trace.</p>"
        )

    text += "<h3>Observed strongest-arm decision at 6 s</h3>" + table(
        ["Saved field", "Saved value"],
        [
            [
                name,
                value if value != "" else None,
            ]
            for name, value in last.items()
        ],
    )

    text += "<h3>Observed source ID 4</h3>" + table(
        ["Saved field", "Saved value"],
        [[name, value] for name, value in alarming.items()],
    )

    return text


def write_html(directory, manifest, plots):
    rows = manifest["cases"] + manifest["regression_cases"]

    chunks = [
        (
            "<!doctype html><html lang='en'>"
            "<meta charset='utf-8'>"
            "<title>DriveCheck evidence</title>"
        ),
        (
            "<style>"
            "body{font:15px system-ui;max-width:1200px;"
            "margin:2rem auto;padding:0 1rem}"
            "table{border-collapse:collapse;width:100%;"
            "margin:1rem 0}"
            "th,td{border:1px solid #bbb;padding:.4rem;"
            "text-align:left}"
            "img{max-width:100%;height:auto}"
            "pre{white-space:pre-wrap}"
            "a{color:#1457a6}"
            "</style>"
        ),
        "<h1>DriveCheck: saved CPU evidence</h1>",
        (
            "<p>Machine execution status: <strong>"
            f"{display(manifest['status'])}</strong>. "
            "Final report-package status and hashes: "
            "<a href='../release-manifest.json'>"
            "release manifest</a>.</p>"
        ),
        (
            f"<p>Declared main cases: {len(manifest['cases'])}; "
            "separate diagnostics: "
            f"{len(manifest['regression_cases'])}. "
            "A completed case can contain a missed warning. "
            "Failed/pending cases remain unscored.</p>"
        ),
        (
            "<p>Synthetic one-dimensional passive warnings; "
            "no vehicle is controlled. A negative episode means "
            "no contact within its declared horizon. "
            "Repeated seeds share scenarios; these are not "
            "independent traffic samples or safety validation.</p>"
        ),
        "<h2>Main matrix</h2>",
        summary_table(manifest["cases"]),
    ]

    families = sorted({row["family"] for row in manifest["cases"]})

    for family in families:
        chunks += [
            f"<h3>Family: {display(family)}</h3>",
            summary_table(
                [row for row in manifest["cases"] if row["family"] == family]
            ),
        ]

    bases = sorted(
        {row["seed_base"] for row in manifest["cases"] if row["seed_base"] is not None}
    )

    for base in bases:
        chunks += [
            f"<h3>Seed base {base} " "(clean shown once above)</h3>",
            summary_table(
                [row for row in manifest["cases"] if row["seed_base"] == base]
            ),
        ]

    chunks += [
        "<h2>Separate fixed-delay diagnostics</h2>",
        summary_table(manifest["regression_cases"]),
        diagnostic_observed(directory, manifest),
        (
            "<p>Independent diagnostic expectation "
            "(compare the saved completed traces): "
            "contact is at 6 s, threshold 2 s, age limit 3 s, "
            "matching window 3 s and useful lead 1 s. "
            "Under delay 2.5 s, the decision at 6 s uses source ID 3: "
            "measurement 3, arrival 5.5, age 3, gap 15 m, "
            "closing 5 m/s, TTC 3 s. It is fresh and clear. "
            "Alarming ID 4 has TTC 2 s but arrives at 6.5 s, "
            "after the horizon. This miss is unavailable alarming "
            "data, not stale rejection. Confirm these trace rows "
            "below; a failed/pending diagnostic is not evidence "
            "this prediction occurred. No improvement is claimed.</p>"
        ),
        "<h2>Every case</h2>",
    ]

    records = []

    for row in rows:
        score = row["score"] or {}
        errors = row["errors"] or {}

        records.append(
            [
                row["case_id"],
                row["section"],
                row["scenario_id"],
                row["condition_id"],
                row.get("seed_base"),
                row["status"],
                score.get("outcome"),
                score.get("first_warning_time_s"),
                score.get("matched_lead_s"),
                errors.get("gap_mae_m"),
                errors.get("closing_speed_mae_mps"),
                "/".join(
                    str(errors.get(name, "N/A"))
                    for name in (
                        "fresh_count",
                        "unavailable_count",
                        "stale_count",
                    )
                ),
                row["error"],
            ]
        )

    chunks += [
        table(
            [
                "ID",
                "Section",
                "Scenario",
                "Profile",
                "Base",
                "Status",
                "Outcome",
                "First warning (s)",
                "Matched lead (s)",
                "Gap MAE (m)",
                "Closing MAE (m/s)",
                "Fresh/unavailable/stale",
                "Error",
            ],
            records,
        ),
        (
            "<p>MAE alignment is truth at decision time, "
            "equally weighted over fresh rows across the full "
            "horizon, including virtual post-contact geometry. "
            "Missing/stale values are excluded, never zero-filled. "
            "Matched lead is unavailable on a miss; misses/late "
            "counts remain beside lead values.</p>"
        ),
    ]

    for row in rows:
        case_id = row["case_id"]

        chunks.append(
            f"<section id='{case_id}'><h3>{case_id}: "
            f"{display(row['scenario_id'])} / "
            f"{display(row['condition_id'])}</h3>"
        )

        links = []

        for name in (
            "result.json",
            "observations.csv",
            "fault-audit.csv",
            "decisions.csv",
        ):
            relative = f"cases/{case_id}/{name}"

            if relative in manifest["artifact_sha256"]:
                links.append(f"<a href='../{relative}'>{name}</a>")

        truth = row["truth_file"]

        if truth in manifest["artifact_sha256"]:
            links.append(
                "<a href='../" f"{escape(truth, quote=True)}'>" "truth.csv</a>"
            )

        chunks.append("<p>" + " | ".join(links) + "</p>")

        if case_id in plots:
            chunks.append(
                f"<img src='{case_id}.png' "
                "alt='Saved gap, TTC, warnings and "
                f"measurement age for {case_id}'>"
            )

        chunks.append("</section>")

    chunks += [
        "<h2>Settings, references and versions</h2>",
        (
            "<p><a href='../configuration.json'>"
            "Effective configuration</a> | "
            "<a href='../plan.json'>"
            "Resolved plan/references/seeds</a> | "
            "<a href='../results.json'>"
            "Full machine results</a> | "
            "<a href='../manifest.json'>"
            "Machine hashes/provenance</a></p>"
        ),
        (
            "<pre>"
            + escape(
                json.dumps(
                    manifest["provenance"],
                    indent=2,
                )
            )
            + "</pre>"
        ),
        (
            "<p>Fixed/seeded synthetic models, one event per "
            "episode, finite horizons, uncalibrated experimental "
            "policies and decision-row weighting limit interpretation. "
            "No real-road generalization, safety certification, "
            "clean-machine reproduction or remote CI success "
            "is established by this report.</p></html>"
        ),
    ]

    (directory / "report" / "report.html").write_text(
        "\n".join(chunks),
        encoding="utf-8",
    )


def check_links(directory):
    report = directory / "report" / "report.html"

    links = []

    class Links(HTMLParser):
        def handle_starttag(self, tag, attrs):
            for name, value in attrs:
                if name in {"src", "href"}:
                    links.append(value)

    parser = Links()
    parser.feed(report.read_text("utf-8"))

    for link in links:
        parts = urlsplit(link)

        if parts.scheme or parts.netloc:
            raise ValueError("report must use contained local links/assets")

        if not parts.path:
            continue

        target = (report.parent / unquote(parts.path)).resolve()

        if not target.is_relative_to(directory) or not target.is_file():
            raise ValueError(f"broken or escaping report link: {link}")

    return len(links)


def package_hashes(directory):
    return {
        path.relative_to(directory).as_posix(): digest(path)
        for path in sorted(directory.rglob("*"))
        if path.is_file() and path != directory / "release-manifest.json"
    }


def generate(run_dir, *, all_plots=False, plotter=None):
    if not isinstance(all_plots, bool) or (
        plotter is not None and not callable(plotter)
    ):
        raise ValueError("invalid report option")

    directory, machine = load_machine(run_dir)
    report_dir = directory / "report"

    if report_dir.exists() or (directory / "release-manifest.json").exists():
        raise ValueError("report/package already exists; " "use a fresh machine run")

    package = {
        "schema": "drivecheck.m4.report.v1",
        "stage": "offline-report",
        "status": "running",
        "machine_status": machine["status"],
        "machine_manifest_sha256": digest(directory / "manifest.json"),
        "renderer": {
            "python": platform.python_version(),
            "source_sha256": {
                name: digest(ROOT / name)
                for name in (
                    "release_report.py",
                    "drivecheck.py",
                    "test_m4_report.py",
                )
            },
        },
        "plot_selection": (
            "all complete cases"
            if all_plots
            else ("clean + five diagnostics + " "base100 strong-latency positives")
        ),
        "plot_case_ids": [],
        "local_link_count": 0,
        "error": None,
        "artifact_sha256": {},
    }

    write_json(
        directory / "release-manifest.json",
        package,
    )
    report_dir.mkdir()

    try:
        renderer = plot_case if plotter is None else plotter

        plots = {}

        for row in machine["cases"] + machine["regression_cases"]:
            if selected(row, all_plots):
                renderer(
                    report_dir / f"{row['case_id']}.png",
                    row,
                    directory,
                )
                plots[row["case_id"]] = True

        package["plot_case_ids"] = list(plots)

        write_html(directory, machine, plots)

        package["local_link_count"] = check_links(directory)

        any_complete = any(
            row["status"] == "complete"
            for row in (machine["cases"] + machine["regression_cases"])
        )

        package["status"] = (
            "complete"
            if machine["status"] == "complete"
            else "partial" if any_complete else "failed"
        )

        package["artifact_sha256"] = package_hashes(directory)

    except Exception as error:
        package["status"] = (
            "partial"
            if any(
                row["status"] == "complete"
                for row in (machine["cases"] + machine["regression_cases"])
            )
            else "failed"
        )

        package["error"] = f"{type(error).__name__}: {error}"
        package["artifact_sha256"] = {}

    write_json(
        directory / "release-manifest.json",
        package,
    )

    return package


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument(
        "--run-dir",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--all-plots",
        action="store_true",
    )

    args = parser.parse_args(argv)

    try:
        result = generate(
            args.run_dir,
            all_plots=args.all_plots,
        )
    except (ValueError, OSError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2

    print(
        f"offline-report {result['status']}; " f"{len(result['plot_case_ids'])} plots"
    )

    if result["error"]:
        print(result["error"], file=sys.stderr)

    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
