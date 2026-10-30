"""Local tables, plots and HTML presentation for the M2 experiment."""

import csv
import json
import math
from dataclasses import asdict, fields
from html import escape

from m1 import save_plot
from motion import TruthSample, truth_at
from observations import Observation
from warning_policy import Decision

CASE_FILES = (
    "truth.csv",
    "observations.csv",
    "decisions.csv",
    "result.json",
    "truth.png",
    "timeline.png",
)


def _write_records(path, records, record_type):
    """Retain complete dataclass fields, including empty-stream headers."""

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[field.name for field in fields(record_type)],
        )
        writer.writeheader()
        writer.writerows(asdict(record) for record in records)


def _timeline(path, fixture, condition, data, warning):
    """Plot truth and the actual decision timeline without changing replay."""

    import matplotlib

    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    scenario = fixture.scenario
    decisions = data["replay"].decisions
    event = fixture.reference_contact_time_s

    dense_times = {scenario.horizon_s * index / 300 for index in range(301)}

    if event is not None:
        dense_times.add(event)

    dense = [truth_at(scenario, time_s) for time_s in sorted(dense_times)]

    times = [decision.decision_time_s for decision in decisions]

    # Plot-only NaNs break lines; saved unavailable values remain JSON null.
    gaps = [
        decision.gap_m if decision.reason not in ("unavailable", "stale") else math.nan
        for decision in decisions
    ]
    ttcs = [
        decision.ttc_s if decision.ttc_s is not None else math.nan
        for decision in decisions
    ]

    fig, axes = plt.subplots(
        3,
        1,
        figsize=(10, 9),
        sharex=True,
        layout="constrained",
    )
    gap_ax, ttc_ax, age_ax = axes

    fig.suptitle(f"{scenario.scenario_id} | {condition['condition_id']}")

    gap_ax.plot(
        [state.time_s for state in dense],
        [state.gap_m for state in dense],
        label="Analytic truth",
        color="black",
    )
    gap_ax.step(
        times,
        gaps,
        where="post",
        label="Fresh held reading at decision time",
    )
    gap_ax.axhline(0, color="gray", linewidth=1)
    gap_ax.set_ylabel("Signed bumper gap (m)")
    gap_ax.set_title("Post-contact negative gap is virtual overlap", fontsize=9)

    ttc_ax.step(times, ttcs, where="post", label="TTC from selected reading")
    ttc_ax.axhline(
        warning["threshold_s"],
        linestyle="--",
        color="tab:orange",
        label="Warning threshold",
    )
    warnings = [decision for decision in decisions if decision.is_warning]
    ttc_ax.scatter(
        [decision.decision_time_s for decision in warnings],
        [decision.ttc_s for decision in warnings],
        color="tab:red",
        marker="x",
        label="Warning decision",
        zorder=4,
    )
    ttc_ax.set_ylabel("TTC (s)")

    for reason, marker in (
        ("unavailable", "x"),
        ("stale", "s"),
        ("not_closing", "+"),
    ):
        state_times = [
            decision.decision_time_s
            for decision in decisions
            if decision.reason == reason
        ]
        if state_times:
            # Axes-relative height avoids assigning a fake numeric TTC.
            ttc_ax.scatter(
                state_times,
                [0.05] * len(state_times),
                transform=ttc_ax.get_xaxis_transform(),
                marker=marker,
                label=f"{reason}: no finite TTC",
            )

    available = [
        decision for decision in decisions if decision.observation_age_s is not None
    ]
    age_ax.scatter(
        [decision.decision_time_s for decision in available],
        [decision.observation_age_s for decision in available],
        label="Age at decision times",
    )
    age_ax.axhline(
        warning["max_age_s"],
        linestyle="--",
        color="tab:orange",
        label="Maximum accepted age",
    )
    age_ax.set_ylabel("Observation age (s)")
    age_ax.set_xlabel("Elapsed simulation / decision time (s)")

    for axis in axes:
        axis.grid(alpha=0.25)
        axis.axvline(
            scenario.horizon_s,
            color="gray",
            linestyle=":",
            label="Horizon",
        )
        if event is not None:
            axis.axvline(
                event,
                color="tab:red",
                linestyle="-.",
                label="Independent contact",
            )
        axis.set_xlim(0, max(scenario.horizon_s, 0.1))
        axis.legend(fontsize=8)

    fig.savefig(path, dpi=140)
    plt.close(fig)


def save_case(directory, fixture, condition, data, warning):
    """Write the required case data and both offline plots."""

    _write_records(directory / "truth.csv", data["truth"], TruthSample)
    _write_records(
        directory / "observations.csv",
        data["observations"],
        Observation,
    )
    _write_records(
        directory / "decisions.csv",
        data["replay"].decisions,
        Decision,
    )

    save_plot(
        directory / "truth.png",
        fixture.scenario,
        data["truth"],
        fixture.reference_contact_time_s,
    )
    _timeline(directory / "timeline.png", fixture, condition, data, warning)


def _display(value):
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def _table(headers, rows):
    head = "".join(f"<th>{escape(str(value))}</th>" for value in headers)
    body = "".join(
        "<tr>"
        + "".join(f"<td>{escape(_display(value))}</td>" for value in row)
        + "</tr>"
        for row in rows
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _fraction(rate):
    if rate["value"] is None:
        return f"{rate['numerator']}/{rate['denominator']} (n/a)"
    return f"{rate['numerator']}/{rate['denominator']} " f"({rate['value']:.1%})"


def write_report(output, manifest):
    """Save every case row and an HTML report using local relative links."""

    flat_rows = []

    for case in manifest["cases"]:
        score = case.get("score") or {}
        errors = case.get("errors") or {}

        flat_rows.append(
            {
                "case_id": case["case_id"],
                "scenario_id": case["scenario_id"],
                "condition_id": case["condition_id"],
                "status": case["status"],
                "horizon_s": case["horizon_s"],
                "reference_contact_time_s": case["reference_contact_time_s"],
                "latency_s": case["condition"]["latency_s"],
                "seed": case["condition"]["seed"],
                "outcome": score.get("outcome", "unscored"),
                "first_warning_time_s": score.get("first_warning_time_s"),
                "matched_lead_s": score.get("matched_lead_s"),
                "fresh_count": errors.get("fresh_count"),
                "unavailable_count": errors.get("unavailable_count"),
                "stale_count": errors.get("stale_count"),
                "gap_mae_m": errors.get("gap_mae_m"),
                "closing_speed_mae_mps": errors.get("closing_speed_mae_mps"),
                "error": case.get("error"),
            }
        )

    with (output / "cases.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(flat_rows[0]))
        writer.writeheader()
        writer.writerows(flat_rows)

    summary_rows = []

    for group in manifest["summaries"]:
        counts = group["outcomes"]
        summary_rows.append(
            [
                group["condition_id"],
                f"{group['planned']['positive']}/{group['planned']['negative']}",
                f"{group['scored']['positive']}/{group['scored']['negative']}",
                f"{group['unscored']['positive']}/{group['unscored']['negative']}",
                counts["useful"],
                counts["late"],
                _fraction(group["rates"]["missed"]),
                _fraction(group["rates"]["false_warning_episode"]),
                _fraction(group["rates"]["without_useful_warning"]),
            ]
        )

    parts = [
        "<!doctype html><html><head><meta charset='utf-8'>",
        "<title>DriveCheck M2 report</title>",
        "<style>"
        "body{font:16px system-ui;max-width:1250px;margin:2rem auto;padding:0 1rem}"
        "table{border-collapse:collapse;width:100%;margin:1rem 0}"
        "td,th{border:1px solid #ccc;padding:.45rem;text-align:left}"
        "th{background:#eee}img{max-width:100%;height:auto}"
        "pre{white-space:pre-wrap;overflow-wrap:anywhere}"
        "</style></head><body>",
        "<h1>DriveCheck M2 experiment</h1>",
        f"<p>Run status: <strong>{escape(manifest['status'])}</strong>. "
        f"Configured cases: {manifest['expected_case_count']}.</p>",
        "<p>P/N means reference-contact/non-contact episodes within each "
        "declared horizon. Rates use scored denominators; unscored cases "
        "remain visible.</p>",
        _table(
            [
                "Condition",
                "Planned P/N",
                "Scored P/N",
                "Unscored P/N",
                "Useful",
                "Late",
                "Missed",
                "False-warning negatives",
                "Without useful warning",
            ],
            summary_rows,
        ),
        "<h2>All configured cases</h2>",
        _table(
            [
                "Case",
                "Scenario",
                "Condition",
                "Status",
                "Outcome",
                "First warning (s)",
                "Matched lead (s)",
                "Gap MAE (m)",
                "Closing MAE (m/s)",
                "Fresh / unavailable / stale",
            ],
            [
                [
                    row["case_id"],
                    row["scenario_id"],
                    row["condition_id"],
                    row["status"],
                    row["outcome"],
                    row["first_warning_time_s"],
                    row["matched_lead_s"],
                    row["gap_mae_m"],
                    row["closing_speed_mae_mps"],
                    f"{row['fresh_count']} / {row['unavailable_count']} / "
                    f"{row['stale_count']}",
                ]
                for row in flat_rows
            ],
        ),
        "<p>Errors compare held readings with truth at decision time, with "
        "equal weight per fresh decision row over the full horizon. Stale "
        "and unavailable rows are excluded, never assigned zero error.</p>",
        "<p>A finite-horizon negative may still predict eventual contact. "
        "Post-contact paths are virtual overlap, with no impact response. "
        "Warnings do not control either vehicle. These few deterministic "
        "synthetic cases do not establish real-world safety or generalisation.</p>",
        "<p>Machine-readable files: "
        "<a href='results.json'>results.json</a>, "
        "<a href='cases.csv'>cases.csv</a>, "
        "<a href='configuration.json'>configuration.json</a>, "
        "<a href='manifest.json'>manifest.json</a>.</p>",
    ]

    for case in manifest["cases"]:
        case_id = case["case_id"]
        parts.append(
            f"<h2>{escape(case_id)} — {escape(case['scenario_id'])} / "
            f"{escape(case['condition_id'])}</h2>"
        )
        parts.append(f"<p>Status: {escape(case['status'])}</p>")

        if case.get("error"):
            parts.append(f"<pre>{escape(case['error'])}</pre>")

        for name in ("result.json", "truth.csv", "observations.csv", "decisions.csv"):
            if (output / case_id / name).is_file():
                parts.append(f"<a href='{case_id}/{name}'>{escape(name)}</a> ")

        if case["status"] == "complete":
            for name in ("truth.png", "timeline.png"):
                parts.append(
                    f"<p><img src='{case_id}/{name}' "
                    f"alt='{escape(case_id)} {escape(name)}'></p>"
                )

    for title, value in (
        ("Effective configuration", manifest["configuration"]),
        ("Runtime and source provenance", manifest["provenance"]),
    ):
        parts.append(
            f"<details><summary>{escape(title)}</summary><pre>"
            f"{escape(json.dumps(value, indent=2, allow_nan=False))}"
            "</pre></details>"
        )

    parts.append("</body></html>")
    (output / "report.html").write_text(
        "\n".join(parts),
        encoding="utf-8",
    )
