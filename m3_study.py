"""Run the bounded M3 fault study and export reproducible evidence."""

import argparse
import csv
import hashlib
import html
import json
import platform
import sys
from dataclasses import asdict, fields
from functools import partial
from importlib.metadata import version
from pathlib import Path

from evaluation import aligned_errors, score_case, summarize
from faults import FaultConfig, inject_faults
from m1 import ROOT, matches, sha256
from m3_regression import run_latency_case
from motion import (
    TruthSample,
    first_contact_time,
    sample_truth,
    truth_at,
)
from observations import Observation
from replay import make_decision_times, replay
from scenarios import Fixture, m1_fixtures
from stop_and_go import (
    first_stop_go_contact_time,
    sample_stop_go_truth,
    stop_go_fixtures,
    stop_go_truth_at,
)
from warning_policy import Decision

SCHEMA = "drivecheck.m3.study.v1"

MATRIX_POLICY = {
    "warning_threshold_s": 3.0,
    "max_age_s": 1.25,
    "pre_event_window_s": 4.0,
    "minimum_useful_lead_s": 1.0,
    "decision_clock": "source schedule plus in-horizon arrivals",
}

SOURCE_FILES = (
    "motion.py",
    "scenarios.py",
    "m1.py",
    "observations.py",
    "warning_policy.py",
    "replay.py",
    "evaluation.py",
    "faults.py",
    "stop_and_go.py",
    "m3_regression.py",
    "m3_study.py",
    "requirements.txt",
    "test_m3_faults.py",
    "test_m3_injection.py",
    "test_m3_scenarios.py",
    "test_m3_boundaries.py",
    "test_m3_regression.py",
    "test_m3_study.py",
)

FRESH_REASONS = {
    "not_closing",
    "ttc_clear",
    "ttc_warning",
    "contact_or_overlap",
}


def canonical_hash(value):
    """Hash JSON content independently of its output filename."""
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def truth_hash(truth):
    return canonical_hash([asdict(sample) for sample in truth])


def write_json(path, value):
    path.write_text(
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )


def write_csv(path, rows, fieldnames):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=fieldnames,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def write_records(path, records, record_type):
    write_csv(
        path,
        [asdict(record) for record in records],
        [field.name for field in fields(record_type)],
    )


def profiles(seed_base):
    """Map one main-study seed base to four private RNG streams."""
    if isinstance(seed_base, bool) or not isinstance(seed_base, int) or seed_base < 0:
        raise ValueError("seed_base must be an integer >= 0")

    seeds = {
        "gap_seed": seed_base + 1,
        "closing_seed": seed_base + 2,
        "latency_seed": seed_base + 3,
        "dropout_seed": seed_base + 4,
    }

    settings = {
        "clean": {},
        "noise_low": {
            "mode": "noise",
            "gap_sigma_m": 0.2,
            "closing_sigma_mps": 0.1,
        },
        "noise_strong": {
            "mode": "noise",
            "gap_sigma_m": 1.0,
            "closing_sigma_mps": 0.5,
        },
        "latency_low": {
            "mode": "latency",
            "latency_s": 0.25,
            "latency_jitter_s": 0.1,
        },
        "latency_strong": {
            "mode": "latency",
            "latency_s": 0.5,
            "latency_jitter_s": 1.5,
        },
        "dropout_low": {
            "mode": "dropout",
            "dropout_probability": 0.1,
        },
        "dropout_strong": {
            "mode": "dropout",
            "dropout_probability": 0.4,
        },
    }

    return {name: FaultConfig(**values, **seeds) for name, values in settings.items()}


def make_context(family, fixture, sampler, evaluator, solver):
    """Check independent references before a study writes any output."""
    scenario = fixture.scenario
    truth = sampler(scenario)
    event = solver(scenario)

    if not matches(event, fixture.reference_contact_time_s):
        raise ValueError(f"{scenario.scenario_id}: contact reference mismatch")

    if not matches(
        truth[-1].gap_m,
        fixture.reference_final_gap_m,
    ):
        raise ValueError(f"{scenario.scenario_id}: final-gap reference mismatch")

    return {
        "family": family,
        "fixture": fixture,
        "truth": truth,
        "truth_at_time": partial(evaluator, scenario),
        "truth_sha256": truth_hash(truth),
    }


def make_row(context, case_id, condition_id, section, fault, policy):
    fixture = context["fixture"]
    scenario = fixture.scenario

    return {
        "schema": "drivecheck.m3.case.v1",
        "section": section,
        "case_id": case_id,
        "condition_id": condition_id,
        "scenario_id": scenario.scenario_id,
        "family": context["family"],
        "status": "pending",
        "horizon_s": scenario.horizon_s,
        "reference_contact_time_s": fixture.reference_contact_time_s,
        "reference_basis": fixture.reference_basis,
        "configuration": asdict(scenario),
        "fault": asdict(fault),
        "policy": dict(policy),
        "truth_sha256": context["truth_sha256"],
        "truth_file": f"truth/{scenario.scenario_id}/truth.csv",
        "score": None,
        "errors": None,
        "counts": None,
        "error": None,
    }


def prepare(seed_base=100):
    """Declare all cases and validate all references before execution."""
    fault_profiles = profiles(seed_base)
    contexts = []

    braking_ids = {
        "lead_braking_contact",
        "lead_braking_noncontact",
    }

    braking = [
        fixture
        for fixture in m1_fixtures()
        if fixture.scenario.scenario_id in braking_ids
    ]

    if {item.scenario.scenario_id for item in braking} != braking_ids:
        raise ValueError("both independent braking fixtures are required")

    for fixture in braking:
        contexts.append(
            make_context(
                "lead_braking",
                fixture,
                sample_truth,
                truth_at,
                first_contact_time,
            )
        )

    for fixture in stop_go_fixtures():
        contexts.append(
            make_context(
                "stop_and_go",
                fixture,
                sample_stop_go_truth,
                stop_go_truth_at,
                first_stop_go_contact_time,
            )
        )

    if len(contexts) != 4:
        raise ValueError("the main study requires four fixtures")

    plan = []

    for context in contexts:
        for condition_id, fault in fault_profiles.items():
            case_id = f"case-{len(plan) + 1:03d}"
            row = make_row(
                context,
                case_id,
                condition_id,
                "matrix",
                fault,
                MATRIX_POLICY,
            )
            plan.append((context, fault, dict(MATRIX_POLICY), row))

    baseline = run_latency_case(0.0)
    regression_fixture = Fixture(
        scenario=baseline["scenario"],
        reference_contact_time_s=6.0,
        reference_final_gap_m=0.0,
        reference_basis=("gap=30-5t; contact at 6 s; final gap at 6 s is 0 m"),
    )

    regression_context = make_context(
        "constant_speed_diagnostic",
        regression_fixture,
        sample_truth,
        truth_at,
        first_contact_time,
    )
    contexts.append(regression_context)

    delays = (
        ("delay_0s", 0.0),
        ("delay_1s", 1.0),
        ("delay_1p5s", 1.5),
        ("delay_2s", 2.0),
        ("delay_2p5s", 2.5),
    )

    for index, (condition_id, delay) in enumerate(delays, start=1):
        # Fixed-delay arms do not use stochastic fault magnitudes.
        fault = FaultConfig(
            mode="clean" if delay == 0 else "latency",
            latency_s=delay,
        )
        policy = dict(baseline["policy"])
        row = make_row(
            regression_context,
            f"regression-{index:03d}",
            condition_id,
            "regression",
            fault,
            policy,
        )
        plan.append((regression_context, fault, policy, row))

    return contexts, plan


def compute_case(context, fault, policy):
    """Run causal replay, then perform separate offline evaluation."""
    fixture = context["fixture"]
    scenario = fixture.scenario

    if context["family"] == "constant_speed_diagnostic":
        data = run_latency_case(fault.latency_s)

        if data["scenario"] != scenario or data["policy"] != policy:
            raise ValueError("diagnostic scenario or policy changed")

        if data["fault_config"] != fault:
            raise ValueError("diagnostic fault configuration changed")

        if not matches(
            data["reference_contact_time_s"],
            fixture.reference_contact_time_s,
        ):
            raise ValueError("diagnostic reference changed")
    else:
        truth = context["truth"]
        observations, audit = inject_faults(truth, fault)

        times = make_decision_times(
            [sample.time_s for sample in truth],
            observations,
            scenario.horizon_s,
            scenario_id=scenario.scenario_id,
        )

        replay_result = replay(
            observations,
            times,
            warning_threshold_s=policy["warning_threshold_s"],
            max_age_s=policy["max_age_s"],
            scenario_id=scenario.scenario_id,
            horizon_s=scenario.horizon_s,
        )

        score = score_case(
            replay_result.decisions,
            reference_contact_time_s=fixture.reference_contact_time_s,
            horizon_s=scenario.horizon_s,
            pre_event_window_s=policy["pre_event_window_s"],
            minimum_useful_lead_s=policy["minimum_useful_lead_s"],
        )

        data = {
            "truth": truth,
            "observations": observations,
            "audit": audit,
            "decision_times_s": times,
            "replay": replay_result,
            "score": score,
        }

    if truth_hash(context["truth"]) != context["truth_sha256"]:
        raise ValueError("cached truth changed during execution")

    if truth_hash(data["truth"]) != context["truth_sha256"]:
        raise ValueError("case truth differs from the frozen snapshot")

    data["errors"] = aligned_errors(
        data["replay"].decisions,
        scenario,
        truth_at_time=context["truth_at_time"],
    )

    return data


def selected_plot(row, all_plots):
    """Select figures by declared condition, never by observed outcome."""
    if all_plots:
        return True

    if row["section"] == "regression":
        return row["condition_id"] in {"delay_0s", "delay_2p5s"}

    if row["condition_id"] == "clean":
        return True

    return row["reference_contact_time_s"] is not None and row["condition_id"] in {
        "noise_strong",
        "latency_strong",
        "dropout_strong",
    }


def save_timeline(path, context, data, policy, label):
    """Plot truth and causal held readings on explicitly labelled clocks."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    scenario = context["fixture"].scenario
    horizon = scenario.horizon_s
    event = context["fixture"].reference_contact_time_s
    evaluator = context["truth_at_time"]
    decisions = data["replay"].decisions

    dense_times = {horizon * index / 400 for index in range(401)}
    dense_times.update(sample.time_s for sample in context["truth"])

    for name in (
        "brake_start_s",
        "stop_time_s",
        "restart_time_s",
        "cruise_time_s",
    ):
        value = getattr(scenario, name, None)
        if value is not None and 0 <= value <= horizon:
            dense_times.add(value)

    if event is not None:
        # Independent reference events are added only to offline plots.
        dense_times.add(event)

    dense_times = sorted(dense_times)
    truth_gaps = [evaluator(time).gap_m for time in dense_times]
    times = [decision.decision_time_s for decision in decisions]
    nan = float("nan")

    held_gaps = [
        decision.gap_m if decision.reason in FRESH_REASONS else nan
        for decision in decisions
    ]
    ttcs = [
        decision.ttc_s if decision.ttc_s is not None else nan for decision in decisions
    ]
    ages = [
        decision.observation_age_s if decision.observation_age_s is not None else nan
        for decision in decisions
    ]

    figure, axes = plt.subplots(
        3,
        1,
        figsize=(11, 9),
        sharex=True,
    )

    try:
        axes[0].plot(
            dense_times,
            truth_gaps,
            color="black",
            label="continuous truth",
        )
        axes[0].step(
            times,
            held_gaps,
            where="post",
            label="fresh held gap at decision time",
        )
        axes[0].scatter(
            [item.measurement_time_s for item in data["observations"]],
            [item.gap_m for item in data["observations"]],
            s=18,
            alpha=0.6,
            label="observation at acquisition; offline view",
        )
        axes[0].axhline(0, color="grey", linewidth=1)
        axes[0].set_ylabel("Gap (m)")

        axes[1].step(times, ttcs, where="post", label="selected TTC")
        axes[1].axhline(
            policy["warning_threshold_s"],
            color="purple",
            linestyle="--",
            label="warning threshold",
        )

        warnings = [item for item in decisions if item.is_warning]
        axes[1].scatter(
            [item.decision_time_s for item in warnings],
            [item.ttc_s for item in warnings],
            color="red",
            marker="x",
            s=45,
            label="warning",
        )

        for reason, marker, height in (
            ("unavailable", "x", 0.08),
            ("stale", "s", 0.16),
            ("not_closing", "^", 0.24),
        ):
            positions = [
                item.decision_time_s for item in decisions if item.reason == reason
            ]
            if positions:
                axes[1].scatter(
                    positions,
                    [height] * len(positions),
                    transform=axes[1].get_xaxis_transform(),
                    marker=marker,
                    s=25,
                    label=f"{reason}: status marker",
                )

        axes[1].set_ylabel("TTC (s)")
        axes[1].set_ylim(bottom=0)

        axes[2].step(times, ages, where="post", label="selected reading age")
        axes[2].axhline(
            policy["max_age_s"],
            color="purple",
            linestyle="--",
            label="maximum accepted age",
        )
        axes[2].set_ylabel("Age (s)")
        axes[2].set_ylim(bottom=0)
        axes[2].set_xlabel("Time (s)")

        for axis in axes:
            axis.axvline(
                horizon,
                color="grey",
                linestyle=":",
                label="horizon",
            )

            if event is not None:
                start = max(
                    0.0,
                    event - policy["pre_event_window_s"],
                )
                useful_end = event - policy["minimum_useful_lead_s"]

                if useful_end >= start:
                    axis.axvspan(
                        start,
                        useful_end,
                        color="green",
                        alpha=0.07,
                        label="useful matching window",
                    )

                axis.axvspan(
                    max(start, useful_end),
                    event,
                    color="orange",
                    alpha=0.10,
                    label="late matching window",
                )
                axis.axvline(
                    event,
                    color="red",
                    linestyle="--",
                    label="independent contact",
                )

                if event < horizon:
                    axis.axvspan(
                        event,
                        horizon,
                        color="grey",
                        alpha=0.08,
                        label="virtual post-contact motion",
                    )

            axis.grid(alpha=0.2)
            axis.legend(fontsize=7, loc="best")

        margin = max(horizon * 0.02, 0.05)
        axes[2].set_xlim(-margin, horizon + margin)
        figure.suptitle(label)
        figure.tight_layout()
        figure.savefig(path, dpi=130)
    finally:
        plt.close(figure)


def provenance():
    missing = [name for name in SOURCE_FILES if not (ROOT / name).is_file()]
    if missing:
        raise ValueError(f"missing provenance files: {missing}")

    return {
        "python": platform.python_version(),
        "platform": platform.system(),
        "packages": {name: version(name) for name in ("matplotlib", "numpy", "Pillow")},
        "source_sha256": {name: sha256(ROOT / name) for name in SOURCE_FILES},
        "draw_order": (
            "v1: per source row reserve gap.gauss, closing.gauss, "
            "latency.random, dropout.random, including dropped rows"
        ),
    }


def checked_destination(output_dir):
    allowed = ROOT / "outputs"

    if allowed.resolve() != allowed:
        raise ValueError("the project outputs directory is redirected")

    destination = Path(output_dir).expanduser().resolve()

    if destination == allowed or not destination.is_relative_to(allowed):
        raise ValueError("use a fresh child directory under project outputs")

    if destination.exists():
        raise ValueError("output directory already exists; choose a fresh name")

    return destination


def scientific_summary(manifest):
    return {
        key: manifest[key]
        for key in (
            "schema",
            "status",
            "configuration",
            "cases",
            "regression_cases",
            "summaries",
            "regression_summaries",
            "error",
        )
    }


def write_case_table(destination, rows):
    records = []

    for row in rows:
        score = row["score"] or {}
        errors = row["errors"] or {}
        counts = row["counts"] or {}

        records.append(
            {
                "section": row["section"],
                "case_id": row["case_id"],
                "scenario_id": row["scenario_id"],
                "condition_id": row["condition_id"],
                "status": row["status"],
                "outcome": score.get("outcome"),
                "first_warning_time_s": score.get("first_warning_time_s"),
                "matched_lead_s": score.get("matched_lead_s"),
                "gap_mae_m": errors.get("gap_mae_m"),
                "closing_speed_mae_mps": errors.get("closing_speed_mae_mps"),
                "fresh_count": errors.get("fresh_count"),
                "unavailable_count": errors.get("unavailable_count"),
                "stale_count": errors.get("stale_count"),
                "dropped_count": counts.get("dropped"),
                "pending_arrival_count": counts.get("pending_arrivals"),
                "truth_sha256": row["truth_sha256"],
                "error": row["error"],
            }
        )

    write_csv(
        destination / "cases.csv",
        records,
        list(records[0]),
    )


def html_table(headers, rows):
    def cell(value):
        return html.escape("" if value is None else str(value))

    heading = "".join(f"<th>{cell(item)}</th>" for item in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{cell(item)}</td>" for item in row) + "</tr>"
        for row in rows
    )
    return f"<table><thead><tr>{heading}</tr></thead><tbody>{body}</tbody></table>"


def write_report(destination, manifest):
    def links(paths):
        result = []
        for path in paths:
            if path.is_file():
                relative = path.relative_to(destination).as_posix()
                result.append(
                    f'<a href="{html.escape(relative, quote=True)}">'
                    f"{html.escape(relative)}</a>"
                )
        return " | ".join(result)

    parts = [
        "<!doctype html><html><head><meta charset='utf-8'>",
        "<title>DriveCheck M3 study</title>",
        "<style>"
        "body{font:15px system-ui;margin:2rem;max-width:1600px}"
        "table{border-collapse:collapse;margin:1rem 0}"
        "th,td{border:1px solid #bbb;padding:.4rem;vertical-align:top}"
        "pre{white-space:pre-wrap;overflow-wrap:anywhere}"
        "a{overflow-wrap:anywhere}"
        "</style></head><body>",
        "<h1>DriveCheck M3 study</h1>",
        f"<p>Execution status: {html.escape(manifest['status'])}</p>",
        "<p>Counts are episodes, not independent-world replications. "
        "Main and diagnostic policies are summarized separately. "
        "Warnings do not change vehicle motion.</p>",
        "<p>MAEs use equal weight per fresh decision row over the full "
        "horizon. Unavailable/stale rows are excluded, not replaced by "
        "zero. Arrival jitter changes the number and timing of rows. "
        "Post-contact trajectories are virtual diagnostics.</p>",
        "<p>"
        + links(
            [
                destination / "manifest.json",
                destination / "configuration.json",
                destination / "study-summary.json",
                destination / "cases.csv",
            ]
        )
        + "</p>",
    ]

    for title, key in (
        ("Main matrix", "summaries"),
        ("Fixed-delay diagnostic", "regression_summaries"),
    ):
        summary_rows = []

        for group in manifest[key]:
            rates = group["rates"]
            useful = rates["useful"]
            false_warning = rates["false_warning_episode"]

            summary_rows.append(
                [
                    group["condition_id"],
                    group["planned"],
                    group["scored"],
                    group["unscored"],
                    group["outcomes"],
                    f"{useful['numerator']}/{useful['denominator']}",
                    (
                        f"{false_warning['numerator']}/"
                        f"{false_warning['denominator']}"
                    ),
                    group["unscored_case_ids"],
                ]
            )

        parts.append(f"<h2>{title}</h2>")
        parts.append(
            html_table(
                [
                    "Condition",
                    "Planned P/N",
                    "Scored P/N",
                    "Unscored P/N",
                    "Outcomes",
                    "Useful / scored positives",
                    "False warning / scored negatives",
                    "Unscored IDs",
                ],
                summary_rows,
            )
        )

    parts.append("<h2>Every declared case</h2>")

    for row in manifest["cases"] + manifest["regression_cases"]:
        case_dir = destination / "cases" / row["case_id"]
        score = row["score"] or {}

        parts.append(
            "<h3>"
            + html.escape(
                f"{row['case_id']} — {row['scenario_id']} — " f"{row['condition_id']}"
            )
            + "</h3>"
        )
        parts.append(
            html_table(
                ["Status", "Outcome", "First warning (s)", "Lead (s)", "Error"],
                [
                    [
                        row["status"],
                        score.get("outcome"),
                        score.get("first_warning_time_s"),
                        score.get("matched_lead_s"),
                        row["error"],
                    ]
                ],
            )
        )
        parts.append(
            "<p>"
            + links(
                [
                    destination / row["truth_file"],
                    case_dir / "result.json",
                    case_dir / "observations.csv",
                    case_dir / "fault-audit.csv",
                    case_dir / "decisions.csv",
                    case_dir / "timeline.png",
                ]
            )
            + "</p>"
        )

    parts.append("<h2>Configuration and provenance</h2>")
    parts.append(
        "<pre>"
        + html.escape(
            json.dumps(
                {
                    "configuration": manifest["configuration"],
                    "provenance": manifest["provenance"],
                    "global_error": manifest["error"],
                },
                indent=2,
                sort_keys=True,
                allow_nan=False,
            )
        )
        + "</pre>"
    )
    parts.append("</body></html>")

    (destination / "report.html").write_text(
        "\n".join(parts) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def run(output_dir, *, seed_base=100, all_plots=False, plotter=None):
    if not isinstance(all_plots, bool):
        raise ValueError("all_plots must be bool")

    if plotter is not None and not callable(plotter):
        raise ValueError("plotter must be callable or None")

    destination = checked_destination(output_dir)
    contexts, plan = prepare(seed_base)
    runtime = provenance()
    renderer = save_timeline if plotter is None else plotter

    configuration = {
        "schema": SCHEMA,
        "units": "SI: seconds, metres, metres/second",
        "main_seed_base": seed_base,
        "main_seed_mapping": "gap/closing/latency/dropout = base + 1/2/3/4",
        "regression_seeds": "fixed defaults 101/102/103/104; no random magnitude",
        "main_profiles": {
            name: asdict(config) for name, config in profiles(seed_base).items()
        },
        "main_policy": dict(MATRIX_POLICY),
        "regression_policy": dict(plan[-1][2]),
        "all_plots": all_plots,
        "scenarios": [
            {
                "family": context["family"],
                "configuration": asdict(context["fixture"].scenario),
                "reference_contact_time_s": (
                    context["fixture"].reference_contact_time_s
                ),
                "reference_final_gap_m": (context["fixture"].reference_final_gap_m),
                "reference_basis": context["fixture"].reference_basis,
                "truth_sha256": context["truth_sha256"],
            }
            for context in contexts
        ],
    }

    manifest = {
        "schema": SCHEMA,
        "status": "running",
        "expected_case_count": 28,
        "expected_regression_count": 5,
        "configuration": configuration,
        "configuration_sha256": canonical_hash(configuration),
        "provenance": runtime,
        "cases": [entry[3] for entry in plan if entry[3]["section"] == "matrix"],
        "regression_cases": [
            entry[3] for entry in plan if entry[3]["section"] == "regression"
        ],
        "summaries": [],
        "regression_summaries": [],
        "error": None,
        "artifact_sha256": {},
    }

    destination.mkdir(parents=True, exist_ok=False)
    write_json(destination / "configuration.json", configuration)
    write_json(destination / "manifest.json", manifest)

    try:
        for context in contexts:
            fixture = context["fixture"]
            truth_dir = destination / "truth" / fixture.scenario.scenario_id
            truth_dir.mkdir(parents=True)

            write_records(
                truth_dir / "truth.csv",
                context["truth"],
                TruthSample,
            )
            write_json(
                truth_dir / "configuration.json",
                asdict(fixture.scenario),
            )
            write_json(
                truth_dir / "reference.json",
                {
                    "contact_time_s": fixture.reference_contact_time_s,
                    "final_gap_m": fixture.reference_final_gap_m,
                    "basis": fixture.reference_basis,
                    "truth_content_sha256": context["truth_sha256"],
                },
            )

        for context, fault, policy, row in plan:
            case_dir = destination / "cases" / row["case_id"]

            try:
                case_dir.mkdir(parents=True)
                data = compute_case(context, fault, policy)

                write_records(
                    case_dir / "observations.csv",
                    data["observations"],
                    Observation,
                )
                write_csv(
                    case_dir / "fault-audit.csv",
                    data["audit"],
                    list(data["audit"][0]),
                )
                write_records(
                    case_dir / "decisions.csv",
                    data["replay"].decisions,
                    Decision,
                )

                if selected_plot(row, all_plots):
                    renderer(
                        case_dir / "timeline.png",
                        context,
                        data,
                        policy,
                        (f"{row['scenario_id']} / " f"{row['condition_id']}"),
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
                        "ignored_older_arrivals": (
                            data["replay"].ignored_older_arrival_count
                        ),
                        "pending_arrivals": (
                            data["replay"].beyond_horizon_arrival_count
                        ),
                    },
                )
                write_json(case_dir / "result.json", row)

            except Exception as error:
                row.update(
                    status="failed",
                    score=None,
                    errors=None,
                    counts=None,
                    error=f"{type(error).__name__}: {error}",
                )

                try:
                    write_json(case_dir / "result.json", row)
                except Exception as save_error:
                    row["error"] += (
                        f"; result export failed: "
                        f"{type(save_error).__name__}: {save_error}"
                    )

            write_json(destination / "manifest.json", manifest)

    except Exception as error:
        manifest["error"] = f"{type(error).__name__}: {error}"

    manifest["summaries"] = summarize(manifest["cases"])
    manifest["regression_summaries"] = summarize(manifest["regression_cases"])

    all_rows = manifest["cases"] + manifest["regression_cases"]
    complete_count = sum(row["status"] == "complete" for row in all_rows)

    manifest["status"] = (
        "complete"
        if complete_count == len(all_rows) and manifest["error"] is None
        else "partial" if complete_count else "failed"
    )

    try:
        write_json(
            destination / "study-summary.json",
            scientific_summary(manifest),
        )
        write_case_table(destination, all_rows)
        write_report(destination, manifest)
    except Exception as error:
        previous = manifest["error"]
        message = f"{type(error).__name__}: {error}"
        manifest["error"] = f"{previous}; {message}" if previous else message
        manifest["status"] = "partial" if complete_count else "failed"

    # Machine-readable evidence survives a report-rendering exception.
    write_json(
        destination / "study-summary.json",
        scientific_summary(manifest),
    )

    try:
        manifest["artifact_sha256"] = {
            path.relative_to(destination).as_posix(): sha256(path)
            for path in sorted(destination.rglob("*"))
            if path.is_file() and path != destination / "manifest.json"
        }
    except Exception as error:
        manifest["artifact_sha256"] = {}
        manifest["error"] = (
            f"{manifest['error'] or ''}; artifact hashing failed: "
            f"{type(error).__name__}: {error}"
        ).lstrip("; ")
        manifest["status"] = "partial" if complete_count else "failed"
        write_json(
            destination / "study-summary.json",
            scientific_summary(manifest),
        )

    # The manifest is excluded from its own artifact hash map.
    write_json(destination / "manifest.json", manifest)
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--seed-base", type=int, default=100)
    parser.add_argument("--all-plots", action="store_true")
    args = parser.parse_args(argv)

    try:
        manifest = run(
            args.output_dir,
            seed_base=args.seed_base,
            all_plots=args.all_plots,
        )
    except Exception as error:
        print(
            f"{type(error).__name__}: {error}",
            file=sys.stderr,
        )
        return 1

    rows = manifest["cases"] + manifest["regression_cases"]
    complete_count = sum(row["status"] == "complete" for row in rows)

    print(f"{manifest['status']}: " f"{complete_count}/{len(rows)} cases complete")
    print(Path(args.output_dir).resolve())

    return 0 if manifest["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
