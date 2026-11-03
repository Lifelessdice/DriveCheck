"""Package saved paired C1 evidence as a contained offline HTML report."""

import csv
import hashlib
from html import escape
import json
import math
from pathlib import Path

from m1 import ROOT


METHODS = ("raw", "age_projection")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def contained(root, relative):
    path = Path(relative)
    resolved = (root / path).resolve()
    if path.is_absolute() or not resolved.is_relative_to(root.resolve()):
        raise ValueError(f"artifact escapes comparison directory: {relative}")
    return resolved


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def reject(value):
        raise ValueError(f"invalid JSON numeric constant: {value}")

    data = json.loads(Path(path).read_text("utf-8"), object_pairs_hook=unique,
                      parse_constant=reject)

    def check(value):
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("non-finite JSON number")
        if isinstance(value, dict):
            for child in value.values():
                check(child)
        elif isinstance(value, list):
            for child in value:
                check(child)
    check(data)
    return data


def write_json(path, data):
    Path(path).write_text(json.dumps(data, sort_keys=True, indent=2, allow_nan=False)
                          + "\n", encoding="utf-8", newline="\n")


def load_machine(run_dir):
    """Check saved machine identity and refuse inconsistent completion claims."""
    root = Path(run_dir)
    root = (root if root.is_absolute() else ROOT / root).resolve()
    if not root.is_relative_to(ROOT.resolve()):
        raise ValueError("comparison directory must remain inside the project")
    manifest = read_json(root / "manifest.json")
    if manifest.get("schema") != "drivecheck.c1.v1" or manifest.get("status") not in {
            "complete", "partial", "failed", "running"}:
        raise ValueError("unsupported comparison manifest schema/status")
    cases = manifest.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("comparison manifest must contain its complete case inventory")
    identities = [case["case_id"] for case in cases]
    if len(set(identities)) != len(identities):
        raise ValueError("duplicate comparison case identity")
    plan = read_json(root / "case-plan.json")
    if (not isinstance(plan, list) or len(plan) != len(cases)
            or [row["case_id"] for row in plan] != identities):
        raise ValueError("comparison cases disagree with the complete frozen case plan")
    frozen_fields = (
        "case_id", "split", "scenario_id", "family", "condition_id", "seed_base",
        "reference_contact_time_s", "horizon_s", "policy", "configuration", "fault",
    )
    for case, planned in zip(cases, plan):
        if any(case.get(key) != planned.get(key) for key in frozen_fields):
            raise ValueError("comparison case settings disagree with the frozen plan")
    for case in cases:
        if case["split"] not in {"development", "evaluation", "diagnostic"}:
            raise ValueError("unknown comparison split")
        if set(case["methods"]) != set(METHODS):
            raise ValueError("each comparison case must retain both methods")
        contained(root, case["artifact_dir"])
        if read_json(contained(root, case["artifact_dir"]) / "metrics.json") != case:
            raise ValueError("case metrics disagree with the run manifest")
        complete = all(case["methods"][method]["status"] == "complete"
                       for method in METHODS)
        if (case["status"] == "complete") != complete:
            raise ValueError("pair completion disagrees with method execution statuses")
        for method in METHODS:
            result = case["methods"][method]
            if result["status"] == "complete":
                if not isinstance(result.get("score"), dict) or not isinstance(
                        result.get("errors"), dict):
                    raise ValueError("complete method must contain score and error evidence")
                for relative in result.get("artifacts", {}).values():
                    if not contained(root, relative).is_file():
                        raise ValueError("missing completed-method evidence")
    if manifest.get("status") == "complete" and any(
            case["status"] != "complete" for case in cases):
        raise ValueError("incomplete methods cannot produce a complete comparison")
    hashes = manifest.get("artifact_sha256")
    if not isinstance(hashes, dict) or not hashes:
        raise ValueError("comparison artifact hash inventory is missing")
    for relative, expected in hashes.items():
        path = contained(root, relative)
        if not path.is_file() or digest(path) != expected:
            raise ValueError(f"comparison artifact changed: {relative}")
    actual = {path.relative_to(root).as_posix() for path in root.rglob("*")
              if path.is_file() and path != root / "manifest.json"
              and path != root / "report-manifest.json"
              and not path.is_relative_to(root / "report")}
    if actual != set(hashes):
        raise ValueError("comparison hashes do not cover the exact machine inventory")
    return root, manifest


def metric_changes(case):
    """Describe directions separately; never conceal a trade-off in one score."""
    raw, alternative = (case["methods"][name] for name in METHODS)
    if raw["status"] != "complete" or alternative["status"] != "complete":
        return {"comparison": "unevaluated"}
    a, b = raw["score"], alternative["score"]
    positive = case["reference_contact_time_s"] is not None
    result = {}

    def direction(name, left, right, larger_better=False):
        if left is None or right is None:
            result[name] = "not paired"
            return
        difference = right - left
        if math.isclose(right, left, rel_tol=1e-12, abs_tol=1e-12):
            result[name] = "unchanged"
        else:
            better = difference > 0 if larger_better else difference < 0
            result[name] = "win" if better else "loss"

    if positive:
        direction("useful warning", int(a["outcome"] == "useful"),
                  int(b["outcome"] == "useful"), True)
        direction("missed event", int(a["outcome"] == "missed"),
                  int(b["outcome"] == "missed"))
        direction("matched lead (paired matches only)", a.get("matched_lead_s"),
                  b.get("matched_lead_s"), True)
    else:
        direction("false-warning episode", int(a["outcome"] == "false_warning"),
                  int(b["outcome"] == "false_warning"))
    for name in ("gap_mae_m", "closing_speed_mae_mps"):
        direction(name, raw["errors"].get(name), alternative["errors"].get(name))
    return result


def group_summary(cases):
    """Use evaluated positive/negative denominators and expose missing coverage."""
    rows = []
    for split in ("development", "evaluation", "diagnostic"):
        selected = [case for case in cases if case["split"] == split]
        if not selected:
            continue
        for condition in [None] + sorted({case["condition_id"] for case in selected}):
            group = selected if condition is None else [
                case for case in selected if case["condition_id"] == condition]
            for method in METHODS:
                positives = [case for case in group
                             if case["reference_contact_time_s"] is not None]
                negatives = [case for case in group
                             if case["reference_contact_time_s"] is None]
                scored_pos = [case["methods"][method] for case in positives
                              if case["methods"][method]["status"] == "complete"]
                scored_neg = [case["methods"][method] for case in negatives
                              if case["methods"][method]["status"] == "complete"]
                counts = {outcome: sum(row["score"]["outcome"] == outcome
                                      for row in scored_pos)
                          for outcome in ("useful", "late", "missed")}
                false = sum(row["score"]["outcome"] == "false_warning" for row in scored_neg)
                rows.append({
                    "split": split, "condition": condition or "ALL", "method": method,
                    "planned_positive": len(positives), "evaluated_positive": len(scored_pos),
                    "planned_negative": len(negatives), "evaluated_negative": len(scored_neg),
                    **counts, "false_warning": false,
                    "failed_or_partial": sum(case["methods"][method]["status"] != "complete"
                                             for case in group),
                })
    return rows


def number(value):
    return "—" if value is None else format(value, ".6g")


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def numeric(rows, name):
    return [float(row[name]) if row.get(name) not in (None, "", "None", "null")
            else None for row in rows]


def selected_plots(cases):
    """Show the diagnostic, an actual evaluation loss, then an unchanged case."""
    completed = [case for case in cases if case["status"] == "complete"]
    selected = []
    diagnostics = [case for case in completed if case["split"] == "diagnostic"]
    if diagnostics:
        selected.append(("Strongest fixed-delay diagnostic (development)", diagnostics[-1]))
    evaluation = [case for case in completed if case["split"] == "evaluation"]
    losses = [case for case in evaluation
              if metric_changes(case).get("gap_mae_m") == "loss"]
    if losses:
        worst = max(losses, key=lambda case: (
            case["methods"]["age_projection"]["errors"]["gap_mae_m"]
            - case["methods"]["raw"]["errors"]["gap_mae_m"], case["case_id"]))
        selected.append(("Largest evaluation increase in gap MAE", worst))
    else:
        warning_losses = [case for case in evaluation
                          if metric_changes(case).get("false-warning episode") == "loss"]
        other_losses = [case for case in evaluation
                        if "loss" in metric_changes(case).values()]
        if warning_losses:
            selected.append(("First evaluation false-warning regression", warning_losses[0]))
        elif other_losses:
            selected.append(("First evaluation loss on another reported metric", other_losses[0]))
    unchanged = [case for case in evaluation
                 if metric_changes(case) and all(value == "unchanged"
                                                for value in metric_changes(case).values())]
    if unchanged:
        selected.append(("First evaluation case unchanged on reported paired metrics", unchanged[0]))
    if not selected and completed:
        selected.append(("First completed pair", completed[0]))
    return selected


def plot_case(root, case, path):
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    directory = contained(root, case["artifact_dir"])
    truth = read_csv(directory / "truth.csv")
    observations = read_csv(directory / "observations.csv")
    fig, axes = plt.subplots(4, 1, figsize=(10, 10), sharex=True, layout="constrained")
    axes[0].plot(numeric(truth, "time_s"), numeric(truth, "gap_m"), color="black",
                 label="Clean signed gap (virtual paths after contact)")
    axes[1].plot(numeric(truth, "time_s"), numeric(truth, "closing_speed_mps"),
                 color="black", label="Clean closing speed")
    for method, color in zip(METHODS, ("tab:blue", "tab:orange")):
        result = case["methods"][method]
        decisions = read_csv(contained(root, result["artifacts"]["decisions"]))
        times = numeric(decisions, "decision_time_s")
        for axis, field in zip(axes[:3], ("gap_m", "closing_speed_mps", "ttc_s")):
            # Unavailable/stale rows are gaps, not numeric sensor estimates.
            values = numeric(decisions, field)
            values = [None if row.get("reason") in {"unavailable", "stale"} else value
                      for row, value in zip(decisions, values)]
            axis.step(times, values, where="post", color=color, label=method)
        axes[3].step(times, numeric(decisions, "observation_age_s"), where="post",
                     color=color, label=f"{method}: original source age")
    policy = case.get("policy", {})
    threshold = policy.get("warning_threshold_s")
    age_limit = policy.get("max_age_s")
    if threshold is not None:
        axes[2].axhline(threshold, color="red", linestyle="--", label="Fixed TTC threshold")
    if age_limit is not None:
        axes[3].axhline(age_limit, color="red", linestyle="--", label="Fixed source-age limit")
    event = case["reference_contact_time_s"]
    for axis in axes:
        if event is not None:
            axis.axvline(event, color="red", linestyle=":", label="Independent contact")
            window = policy.get("pre_event_window_s")
            lead = policy.get("minimum_useful_lead_s")
            if window is not None and lead is not None and event >= lead:
                axis.axvspan(max(0, event - window), event - lead, color="green",
                             alpha=0.08, label="Useful-warning interval")
        axis.axvline(case["horizon_s"], color="gray", linestyle=":", label="Horizon")
        axis.grid(alpha=0.25)
        axis.legend(fontsize=7, loc="best")
        axis.set_xlim(0, max(case["horizon_s"], 0.1))
    arrivals = [float(row["arrival_time_s"]) for row in observations
                if float(row["arrival_time_s"]) <= case["horizon_s"]]
    ages = [float(row["arrival_time_s"]) - float(row["measurement_time_s"])
            for row in observations if float(row["arrival_time_s"]) <= case["horizon_s"]]
    axes[3].scatter(arrivals, ages, marker="x", color="gray", s=18, label="Source arrivals")
    axes[3].legend(fontsize=7, loc="best")
    for axis, label in zip(axes, ("Gap (m)", "Closing speed (m/s)", "TTC (s)", "Source age (s)")):
        axis.set_ylabel(label)
    axes[-1].set_xlabel("Decision / scenario time (s)")
    fig.suptitle(f"{case['case_id']} | {case['scenario_id']} | {case['condition_id']}")
    fig.savefig(path, dpi=120)
    plt.close(fig)


def render(run_dir):
    """Render every saved case and bind package hashes without changing machine data."""
    root, manifest = load_machine(run_dir)
    destination = root / "report"
    if destination.exists() or (root / "report-manifest.json").exists():
        raise ValueError("report destination already exists; preserve the previous package")
    destination.mkdir()
    package = {"schema": "drivecheck.c1.report.v1", "status": "running",
               "machine_status": manifest["status"], "error": None,
               "machine_manifest_sha256": digest(root / "manifest.json"),
               "plot_selection": [], "artifact_sha256": {},
               "source_sha256": {name: digest(ROOT / name)
                                 for name in ("c1_report.py", "c1_compare.py")}}
    try:
        parts = ["<!doctype html><html lang='en'><meta charset='utf-8'>",
                 "<meta name='viewport' content='width=device-width,initial-scale=1'>",
                 "<title>DriveCheck C1 fair comparison</title>",
                 "<style>body{font:15px system-ui;margin:2rem;line-height:1.5;color:#17212b}",
                 "table{border-collapse:collapse;width:100%;margin:1rem 0}td,th{padding:.45rem;",
                 "border:1px solid #c7ced6;text-align:left}th{background:#edf2f7}",
                 "pre{white-space:pre-wrap;background:#f4f6f8;padding:1rem}img{max-width:100%}",
                 ".scroll{overflow:auto}.status{padding:1rem;background:#fff1cf}</style>",
                 "<h1>DriveCheck: raw versus source-age projection</h1>",
                 f"<p class='status'>Machine status: <b>{escape(manifest['status'])}</b>. ",
                 f"{len(manifest['cases'])} planned paired episodes; both method records retained.</p>",
                 "<p>One changed component: estimated gap = measured gap − measured closing speed × ",
                 "original measurement age. Both methods receive the same causal streams, decision ",
                 "clock, freshness limit, warning threshold and independent scoring. Source timestamps ",
                 "are preserved. No warnings change the trajectory.</p>",
                 "<p>Development, reserved evaluation configurations/seeds, and five fixed-delay ",
                 "development diagnostics are reported separately. The alternative has no tunable ",
                 "parameter. Synthetic scaling is a bounded holdout, not independent real traffic.</p>",
                 "<h2>Complete split and profile accounting</h2>",
                 "<p>Counts below use evaluated denominators; failed/partial executions remain visible. ",
                 "Late and missed are exclusive; both lack a useful warning. Negative labels mean no ",
                 "contact within the declared horizon, not universally safe motion.</p>",
                 "<div class='scroll'><table><tr><th>Split / profile</th><th>Method</th>",
                 "<th>Evaluated / planned +</th><th>Useful</th><th>Late</th><th>Missed</th>",
                 "<th>Evaluated / planned −</th><th>False-warning episodes</th><th>Failed/partial</th></tr>"]
        for row in group_summary(manifest["cases"]):
            positive, negative = row["evaluated_positive"], row["evaluated_negative"]
            cells = [f"{row['split']} / {row['condition']}", row["method"],
                     f"{positive}/{row['planned_positive']}",
                     *(f"{row[name]}/{positive}" if positive else "N/A (0)"
                       for name in ("useful", "late", "missed")),
                     f"{negative}/{row['planned_negative']}",
                     f"{row['false_warning']}/{negative}" if negative else "N/A (0)",
                     row["failed_or_partial"]]
            parts.append("<tr>" + "".join(f"<td>{escape(str(cell))}</td>" for cell in cells) + "</tr>")
        parts.extend(["</table></div><h2>Every paired case</h2>",
                      "<p>MAEs compare the used estimate with truth at the same decision time, equally ",
                      "weighted over eligible rows through the full horizon. Missing/stale estimates ",
                      "are excluded with counts, never filled by zero. Lead times are meaningful with ",
                      "their event outcomes; missing and late outcomes must not disappear.</p>",
                      "<div class='scroll'><table><tr><th>Case / split / scenario / profile / seed</th>",
                      "<th>Method / status</th><th>Outcome</th><th>First warning (s)</th>",
                      "<th>Matched lead (s)</th><th>Gap MAE (m)</th><th>Closing MAE (m/s)</th>",
                      "<th>Fresh / unavailable / stale</th><th>Error</th></tr>"])
        for case in manifest["cases"]:
            for method in METHODS:
                result = case["methods"][method]
                score, errors = result.get("score") or {}, result.get("errors") or {}
                key = (f"{case['case_id']} / {case['split']} / {case['scenario_id']} / "
                       f"{case['condition_id']} / {case.get('seed_base')}")
                cells = [key, f"{method} / {result['status']}", score.get("outcome", "unevaluated"),
                         number(score.get("first_warning_time_s")), number(score.get("matched_lead_s")),
                         number(errors.get("gap_mae_m")), number(errors.get("closing_speed_mae_mps")),
                         " / ".join(str(errors.get(name, "—")) for name in
                                    ("fresh_count", "unavailable_count", "stale_count")),
                         result.get("error") or ""]
                parts.append("<tr>" + "".join(f"<td>{escape(str(cell))}</td>" for cell in cells) + "</tr>")
            changes = metric_changes(case)
            parts.append("<tr><td colspan='9'>Metric-specific changes: "
                         + escape(json.dumps(changes, sort_keys=True)) + "</td></tr>")
            evidence = [f"{case['artifact_dir']}/metrics.json",
                        f"{case['artifact_dir']}/truth.csv",
                        f"{case['artifact_dir']}/observations.csv"]
            for method in METHODS:
                evidence.extend(case["methods"][method].get("artifacts", {}).values())
            links = [f"<a href='../{escape(relative, quote=True)}'>{escape(Path(relative).name)}</a>"
                     for relative in evidence if contained(root, relative).is_file()]
            parts.append("<tr><td colspan='9'>Saved evidence: " + " · ".join(links)
                         + "</td></tr>")
        parts.extend(["</table></div><h2>Evidence plots and selection rule</h2>",
                      "<p>Show the strongest fixed-delay development diagnostic, then the evaluation ",
                      "case with the largest gap-MAE increase. When no gap-MAE loss exists, show the ",
                      "first evaluation false-warning regression, or otherwise the first loss on ",
                      "another reported metric. Also show the first evaluation case unchanged on ",
                      "all reported paired metrics, when present. The complete table above retains ",
                      "every case. This reporting rule does not alter algorithms or evaluation.</p>"])
        for index, (label, case) in enumerate(selected_plots(manifest["cases"]), start=1):
            name = f"pair-{index:02d}.png"
            plot_case(root, case, destination / name)
            package["plot_selection"].append({"case_id": case["case_id"], "reason": label, "path": f"report/{name}"})
            parts.append(f"<h3>{escape(label)}: {escape(case['case_id'])}</h3>"
                         f"<img src='{name}' alt='{escape(label, quote=True)}'>")
        parts.extend(["<h2>Complete directional summary</h2><pre>",
                      escape(json.dumps(manifest.get("summary", {}), sort_keys=True, indent=2)),
                      "</pre><h2>Frozen configuration and selection</h2><pre>",
                      escape(json.dumps({"config": manifest.get("config"),
                                         "config_sha256": manifest.get("config_sha256"),
                                         "frozen_selection": manifest.get("frozen_selection")},
                                        sort_keys=True, indent=2)),
                      "</pre><h2>Source identity</h2><pre>",
                      escape(json.dumps(manifest.get("source_sha256", {}), sort_keys=True, indent=2)),
                      "</pre><h2>Limits and interpretation</h2><p>Constant closing speed can be wrong ",
                      "under braking or acceleration; speed error is multiplied by age. Projection ",
                      "does not restore missing or not-yet-arrived information. An estimated overlap ",
                      "is not a reference contact. A few synthetic configurations/seeds do not establish ",
                      "generalization, statistical significance or real-vehicle safety. The raw baseline ",
                      "remains usable. AI assistance supported implementation and verification; learner ",
                      "understanding is a separate assessment.</p></html>"])
        (destination / "report.html").write_text("".join(parts), encoding="utf-8", newline="\n")
        package["artifact_sha256"] = {
            path.relative_to(root).as_posix(): digest(path)
            for path in sorted(destination.rglob("*")) if path.is_file()
        }
        package["status"] = "complete" if manifest["status"] == "complete" else "partial"
    except Exception as error:
        package["status"] = "failed"
        package["error"] = f"{type(error).__name__}: {error}"
        write_json(root / "report-manifest.json", package)
        raise
    write_json(root / "report-manifest.json", package)
    return package
