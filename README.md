# DriveCheck

**Better gap estimates can still produce more warning episodes.**

DriveCheck is a Python workbench for investigating how controlled sensor faults affect a passive collision-warning rule. It separates synthetic vehicle trajectories, causal observations, warning decisions and independent offline scoring, then compares a raw-measurement baseline with constant-closing-speed age projection on the same observations and policies.

The result is a measured trade-off: projection fixes a held-old-reading failure and often improves gap error, but does not improve positive outcome counts on the separate evaluation suite and increases finite-horizon false-warning episodes. Raw remains the default.

## Results

The frozen comparison retains **76 development pairs, 76 evaluation pairs and five development diagnostics: 157 pairs / 314 method records**. Every pair and both methods remain visible, with configuration, source identity, traces, faults, status and metrics.

| Separate evaluation set | Raw | Age projection |
| --- | ---: | ---: |
| Useful positive episodes | 31/38 | 31/38 |
| Late positive episodes | 2/38 | 2/38 |
| Missed positive episodes | 5/38 | 5/38 |
| False-warning negative episodes | 26/38 | 35/38 |

Gap MAE improves in 37 evaluation pairs, stays equal in 38 and is unavailable in one. Among paired useful detections, earliest lead improves in three and stays equal in 28; seven positive pairs lack a paired useful match. An unavailable estimate is not zero error.

“False warning” means a warning in an episode with no reference contact **inside its declared horizon**. In `evaluation-027`, projection correctly estimates the current gap at 30 m, yet its extra warning counts as false because contact would occur beyond the 10 s horizon. This is an experimental scoring convention, not a judgment about what a real driver should do.

See [complete results and denominators](docs/results.md), the [failure investigation](docs/c1-investigation.md), and the earlier [baseline failure study](docs/failure-study.md).

## Run locally

The checked target is **CPython 3.14.7 / Windows x64**. From an existing prepared checkout in PowerShell:

```powershell
Set-Location 'E:\DriveCheck'
.\.venv\Scripts\python.exe c1_compare.py --config configs/c1-comparison.json --output-dir outputs/c1-example
if ($LASTEXITCODE -ne 0) { throw 'Comparison failed; inspect its saved evidence.' }
.\.venv\Scripts\python.exe -m tools.verify_c1 outputs/c1-example
if ($LASTEXITCODE -ne 0) { throw 'Comparison audit failed.' }
Invoke-Item -LiteralPath .\outputs\c1-example\report\report.html
```

Use a **fresh** output directory; the runner refuses existing destinations. The report opens from disk with local plots and no credentials, CARLA, GPU or hosted service. `cases.csv`, `summary.json`, the frozen plan/configuration and per-case truth/observation/source/used-decision traces remain beside it. Failed and partial methods retain explicit statuses.

For a new checkout, use the exact-runtime and hash-locked setup in [reproduction.md](docs/reproduction.md). Preserve an existing environment. The lock records all 12 runtime packages plus pip and Ruff; other platforms are not covered by the recorded evidence.

## Short offline portfolio demo

Package that audited run as a portable three-case walkthrough, retaining the complete evidence underneath:

```powershell
.\.venv\Scripts\python.exe -m tools.portfolio_demo --run outputs/c1-example --output-dir outputs/portfolio-example
if ($LASTEXITCODE -ne 0) { throw 'Portfolio packaging failed.' }
Invoke-Item -LiteralPath .\outputs\portfolio-example\index.html
```

The packager checks source provenance and the frozen configuration, copies all report evidence byte for byte, preserves the original run and refuses an existing destination. The page has no scripts, CDN, external fonts or analytics. Its manifest records the source audit and every copied file hash.

The [2–3-minute script](docs/demo.md) follows three actual cases:

1. `diagnostic-005`: an arrived but old reading hides a warning; age projection recovers a useful warning under the constant-speed diagnostic.
2. `evaluation-027`: current-gap accuracy improves while a finite-horizon negative episode gains a warning.
3. `evaluation-001`: zero-age clean data leaves both methods unchanged.

Generated demonstrations stay under ignored `outputs/`; the commands reproduce them. [Verification](docs/verification.md) records the tested runtime, report audits and reproducibility limits.

## Architecture and verification

`scenario truth → observations/faults → arrival replay → raw or projected state → shared warning rule → independent evaluator → complete offline report`

Truth supplies reference events and error checks only to offline evaluation. The warning path sees arrived observations, original source age and the current decision time. Contact labels come from continuously checked trajectories, not from the TTC threshold being tested. See [architecture and data contracts](docs/architecture.md).

The tests cover independent analytic contact/non-contact fixtures, timing and availability boundaries, known-answer metrics, causal prefixes, baseline compatibility and failure regressions. The published baseline's [main CI run](https://github.com/Lifelessdice/DriveCheck/actions/runs/42056296813) at `b2168f189377c9b7919f289f81f1b6e986b973ef` passed **227 tests**, dependency/lint checks, both complete experiment audits and the real portfolio build with all 1,424 evidence files preserved. See [verification](docs/verification.md) for revision-specific results and [main-branch runs](https://github.com/Lifelessdice/DriveCheck/actions?query=branch%3Amain) for later checks.

The recorded C1 reproduction copied 55 source inputs, hash-installed 14 wheel/package pins, and reproduced two 1,424-file reports with zero file differences on the same machine in a new environment. It is separate from cross-machine or cross-platform validation. [Commands and exact evidence](docs/reproduction.md).

## Limits

This is a one-dimensional kinematic experiment with prescribed motion, two synthetic scenario families, controlled noise/latency/dropout and a limited set of related configurations. Negative gaps after contact are virtual overlap; impact dynamics are not simulated. Warnings do not control a vehicle. Thresholds/windows are experimental choices. There is no claim of safety certification, statistical significance, real-road generalisation, Kalman filtering or CARLA integration.

## Attribution and licence

Developed with AI assistance for implementation, testing and documentation.

Original project source uses the [MIT licence](LICENSE). Dependency-specific licences and technical references are documented in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
