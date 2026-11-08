"""Package the audited frozen comparison as a portable, offline portfolio demo."""

import argparse
import hashlib
from html import escape
import json
from pathlib import Path
import shutil

from tools.verify_c1 import verify


ROOT = Path(__file__).resolve().parents[1]
CONFIG_SHA256 = "8bf3c4aaaa9395ee66c2a75a4e52a554c94d47fe111f404af5a9dcddd12bef27"
PLOT_CASES = ("diagnostic-005", "evaluation-027", "evaluation-001")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(directory):
    result = {}
    for path in sorted(directory.rglob("*")):
        if path.is_symlink() or not path.resolve().is_relative_to(directory):
            raise ValueError("demo evidence must not contain redirected paths")
        if path.is_file():
            result[path.relative_to(directory).as_posix()] = digest(path)
    return result


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
                    encoding="utf-8", newline="\n")


def page(manifest):
    """Describe only the fixed, independently audited comparison configuration."""
    group = manifest["summary"]["evaluation"]
    rows = []
    for label, key, denominator in (
        ("Useful positives", "useful", "positive_count"),
        ("Late positives", "late", "positive_count"),
        ("Missed positives", "missed", "positive_count"),
        ("False-warning negative episodes", "false_warning", "negative_count"),
    ):
        values = [group["methods"][method] for method in ("raw", "age_projection")]
        cells = "".join(f"<td>{value['outcomes'].get(key, 0)}/{value[denominator]}</td>"
                        for value in values)
        rows.append(f"<tr><th scope='row'>{escape(label)}</th>{cells}</tr>")
    return """<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src 'self' file:; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>DriveCheck — better estimates, more warnings</title>
<style>
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#eef2f6;color:#182b40;font:17px/1.6 system-ui,sans-serif}
main{max-width:1080px;margin:auto;padding:32px 24px 70px}nav{display:flex;flex-wrap:wrap;gap:10px;padding:16px 0}
a{color:#174a8b;text-underline-offset:3px}nav a{background:#fff;border:1px solid #bdcad8;border-radius:7px;padding:7px 13px}
header,section{background:#fff;padding:28px 32px;border:1px solid #d4dde6;border-radius:12px;margin-bottom:24px}
h1{font-size:clamp(28px,4.3vw,48px);line-height:1.15;max-width:820px;margin:10px 0 20px}h2{font-size:27px;line-height:1.25}
.eyebrow{font-size:13px;font-weight:700;letter-spacing:.09em;text-transform:uppercase;color:#41627e}.lead{font-size:21px}
.fact{border-left:4px solid #167079;padding:12px 18px;background:#eef7f7}.limit{border-left:4px solid #a75123;padding:12px 18px;background:#fff5ed}
table{border-collapse:collapse;width:100%;margin:20px 0}th,td{padding:10px 12px;text-align:left;border-bottom:1px solid #d4dde6}
thead{background:#edf2f7}img{display:block;width:100%;height:auto;margin-top:20px}figure{margin:0}figcaption{font-size:14px;color:#425973;margin:10px 0}
code{background:#edf2f7;padding:2px 5px;border-radius:3px}footer{font-size:14px;color:#425973}.links{display:flex;gap:18px;flex-wrap:wrap}
@media(max-width:600px){main{padding:16px 10px}header,section{padding:20px 16px}table{font-size:14px}th,td{padding:7px}.lead{font-size:18px}}
@media print{body{background:white}nav{display:none}section{break-inside:avoid}a{color:inherit}}
</style><main>
<header><div class="eyebrow">DriveCheck / synthetic validation workbench</div>
<h1>Better gap estimates can still produce more warning episodes.</h1>
<p class="lead">I investigated how measurement age changes a passive collision-warning rule, then compared one small change on the same causal observations.</p>
<p>The CPU workflow separates clean trajectories, controlled sensor faults, arrival-time replay, warning decisions and independent offline scoring.</p>
<nav aria-label="Demo sections"><a href="#mechanism">1 · Mechanism</a><a href="#tradeoff">2 · Trade-off</a><a href="#unchanged">3 · Unchanged</a><a href="#results">Complete results</a></nav>
<div class="fact">157 paired episodes · 314 method records · 76 evaluation pairs · separate development and diagnostics</div>
</header>
<section id="results"><div class="eyebrow">The supported conclusion</div><h2>State accuracy and warning utility are different outcomes.</h2>
<p>Raw stays the default. Age projection improves gap MAE in 37 evaluation pairs, leaves 38 unchanged and has no eligible estimate in one. Positive outcome counts stay unchanged; false-warning episodes increase.</p>
<table><thead><tr><th>Evaluation metric</th><th>Raw</th><th>Age projection</th></tr></thead><tbody>""" + "".join(rows) + """</tbody></table>
<p>The 38 contact and 38 non-contact episodes belong to a fixed, related synthetic suite. A non-contact label means no contact within the declared horizon. Diagnostics are not pooled into these denominators.</p>
<p class="links"><a href="evidence/report/report.html">All cases, traces and comparison plots</a><a href="evidence/cases.csv">Complete method rows (CSV)</a><a href="evidence/summary.json">Machine summary</a><a href="evidence/configuration.json">Frozen configuration</a><a href="manifest.json">Demo identity and source audit</a></p></section>
<section id="mechanism"><div class="eyebrow">01 / diagnostic-005 / development</div><h2>Account for the age of an arrived reading.</h2>
<p>At decision time 4 s, the selected reading was measured at 1 s and arrived at 3.5 s: gap 25 m, closing speed 5 m/s, age 3 s. Raw TTC is 5 s. Projection uses <code>25 − 5 × 3 = 10 m</code>, so TTC is 2 s.</p>
<div class="fact">With the diagnostic threshold of 2 s, projection warns at 4 s, two seconds before independently checked contact at 6 s. Raw misses. No reading is used before arrival.</div>
<p>The same eight eligible rows give gap MAE 13.75 m raw versus 0 m projected. This constant-speed diagnostic matches the assumption; its policy differs from the main evaluation.</p>
<figure><img src="evidence/report/pair-01.png" width="1200" height="1200" alt="Diagnostic 005: raw and projected gaps, closing speeds, TTC and original source age"><figcaption>Original, unaltered C1 plot. The evaluator can show truth; the warning method receives only causal observations.</figcaption></figure></section>
<section id="tradeoff"><div class="eyebrow">02 / evaluation-027 / low latency</div><h2>The estimate is correct; the extra warning is still counted.</h2>
<p>At the 10 s horizon, the reading is 1.25 s old and reports gap 45 m / closing speed 12 m/s. Raw TTC is 3.75 s. Projection gives <code>45 − 12 × 1.25 = 30 m</code>, the correct current gap, and TTC 2.5 s.</p>
<div class="limit">The main threshold is 3 s, so projection warns. Contact would occur at 12.5 s, outside the 10 s horizon. Under this finite-horizon convention the negative episode changes from clear to false warning. This is not driving advice.</div>
<p>Full-episode gap MAE improves from 6.91937 m to 0.99145 m. The result exposes both a method trade-off and the importance of the scoring question.</p>
<figure><img src="evidence/report/pair-02.png" width="1200" height="1200" alt="Evaluation 027: projected endpoint gap is closer to truth while its TTC crosses the warning threshold"><figcaption>Endpoint markers preserve the decision at exactly 10 s. Truth lines join saved samples; they are not a claim of exact linear motion between every row.</figcaption></figure></section>
<section id="unchanged"><div class="eyebrow">03 / evaluation-001 / clean</div><h2>Zero measurement age leaves the result unchanged.</h2>
<p>With zero source age the correction is zero. Both methods warn at 2.5 s; independent contact is approximately 4.145781 s, giving useful lead approximately 1.645781 s. Both gap and closing-speed MAE are zero.</p>
<figure><img src="evidence/report/pair-03.png" width="1200" height="1200" alt="Evaluation 001: coincident clean raw and projected decisions"><figcaption>An unchanged case belongs beside the mechanism and loss. The complete table retains every other result.</figcaption></figure></section>
<section><h2>What this project establishes</h2>
<p>I kept observations, warning policy and scoring fixed within each pair; separated development and evaluation configurations/streams; preserved failures and missing estimates; checked independent event/metric fixtures; and reproduced the report in a new locked environment.</p>
<p class="limit">This is a one-dimensional kinematic experiment with prescribed motion, synthetic faults, closely related scenarios and experimental thresholds. Warnings do not alter vehicle motion. There is no claim of real-world safety, statistical significance, Kalman filtering or CARLA integration.</p>
</section><footer>Offline artifact: no scripts, external fonts, CDN, analytics or network-dependent assets. Project and dependency licensing are documented separately; bundled evidence is generated synthetic project output. Source audit and byte identities are recorded in manifest.json.</footer></main></html>
"""


def build(run_dir, output_dir):
    source = Path(run_dir).resolve()
    destination = Path(output_dir).resolve()
    output_root = (ROOT / "outputs").resolve()
    if output_root != ROOT / "outputs":
        raise ValueError("project outputs must not redirect to another directory")
    if not source.is_relative_to(output_root) or not source.is_dir():
        raise ValueError("source must be a saved comparison under project outputs")
    if (not destination.is_relative_to(output_root) or destination == output_root
            or destination.exists() or destination.is_relative_to(source)
            or source.is_relative_to(destination)):
        raise ValueError("destination must be a fresh, separate project output directory")
    before = inventory(source)
    audit = verify(source)
    manifest = json.loads((source / "manifest.json").read_text("utf-8"))
    if manifest["config_sha256"] != CONFIG_SHA256:
        raise ValueError("this narrative requires the frozen default C1 configuration")
    package = json.loads((source / "report-manifest.json").read_text("utf-8"))
    expected_selection = [(case, f"report/pair-{number:02d}.png")
                          for number, case in enumerate(PLOT_CASES, 1)]
    if [(row["case_id"], row["path"]) for row in package["plot_selection"]] != expected_selection:
        raise ValueError("selected plots do not match the three-case portfolio narrative")
    evaluation = manifest["summary"]["evaluation"]
    if (evaluation["complete_pairs"] != 76
            or evaluation["methods"]["raw"]["outcomes"] != {
                "clear_negative": 12, "false_warning": 26, "late": 2, "missed": 5, "useful": 31}
            or evaluation["methods"]["age_projection"]["outcomes"] != {
                "clear_negative": 3, "false_warning": 35, "late": 2, "missed": 5, "useful": 31}
            or evaluation["directional_changes"]["gap_mae_m"] != {
                "loss": 0, "not_comparable": 1, "unchanged": 38, "win": 37}):
        raise ValueError("evaluation differs from the fixed portfolio narrative")
    for name in ("pair-01.png", "pair-02.png", "pair-03.png"):
        if not (source / "report" / name).is_file():
            raise ValueError("comparison report is missing its three selected plots")
    document = page(manifest)
    destination.mkdir(parents=True)
    record = {"schema": "drivecheck.portfolio.v1", "status": "running",
              "source_audit": audit, "config_sha256": CONFIG_SHA256,
              "source_manifest_sha256": before["manifest.json"],
              "builder_sha256": digest(Path(__file__)), "error": None}
    write_json(destination / "manifest.json", record)
    try:
        shutil.copytree(source, destination / "evidence")
        if inventory(destination / "evidence") != before or inventory(source) != before:
            raise ValueError("copied evidence differs or source changed during packaging")
        (destination / "index.html").write_text(document, encoding="utf-8", newline="\n")
        record["artifact_sha256"] = {
            name: value for name, value in inventory(destination).items()
            if name != "manifest.json"}
        record["source_preserved"] = True
        record["status"] = "complete"
    except Exception as error:
        record["status"] = "failed"
        record["error"] = f"{type(error).__name__}: {error}"
        raise
    finally:
        write_json(destination / "manifest.json", record)
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        record = build(args.run, args.output_dir)
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(1, f"Portfolio packaging failed: {error}\n")
    print(f"Portfolio {record['status']}; evidence unchanged; {len(record['artifact_sha256'])} files")
    print(f"Open: {(args.output_dir / 'index.html').resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
