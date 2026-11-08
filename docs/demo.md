# DriveCheck: a 2–3-minute demonstration

This walkthrough presents the experiment's question, failure mechanism, measured trade-off and limitations using three saved cases.

## Reproduce the demonstration

Use the existing environment and a fresh destination for each run:

```powershell
Set-Location 'E:\DriveCheck'
.\.venv\Scripts\python.exe c1_compare.py --config configs/c1-comparison.json --output-dir outputs/c1-demo-new
if ($LASTEXITCODE -ne 0) { throw 'Comparison failed; inspect the recorded failure.' }
.\.venv\Scripts\python.exe -m tools.verify_c1 outputs/c1-demo-new
if ($LASTEXITCODE -ne 0) { throw 'Independent evidence audit failed.' }
.\.venv\Scripts\python.exe -m tools.portfolio_demo --run outputs/c1-demo-new --output-dir outputs/portfolio-demo-new
if ($LASTEXITCODE -ne 0) { throw 'Portfolio packaging failed.' }
Invoke-Item -LiteralPath .\outputs\portfolio-demo-new\index.html
```

The generated `index.html` is the short presentation. Its `evidence/` directory retains the complete 157-pair comparison, all method rows and the original report. Its `manifest.json` binds the source audit/configuration/manifest and every copied file. Moving the complete generated folder keeps its relative links usable. Do not move only the HTML file.

The packager checks the frozen default C1 configuration and the current checkout's source identities before writing. An older saved run may fail provenance after Git line-ending conversion; preserve it as historical evidence and regenerate from the current checkout. Never edit an old manifest to make it pass.

## Spoken script and screen order

Target duration: approximately 2½ minutes at a clear conversational pace.

**0:00–0:25 — opening and result table**

“DriveCheck is my Python workbench for investigating how sensor faults affect a simple collision-warning rule. I keep the vehicle motion fixed, introduce controlled faults and evaluate the warnings against independently checked contact events. The warnings are passive: they do not change the vehicles' trajectories.”

**0:25–0:50 — the complete-evidence links**

“The comparison uses the same observations, warning policy and scoring for both methods. It retains 76 development pairs, 76 separate evaluation pairs and five diagnostics. The links here expose all cases and settings. The alternative projects a reading's gap forward using its original age and measured closing speed; it does not receive future truth.”

**0:50–1:20 — Mechanism / diagnostic-005**

“At four seconds, this arrived reading is three seconds old. It reports a 25-metre gap and five metres per second closing speed. Raw TTC is five seconds. Projection subtracts fifteen metres, giving a ten-metre gap and TTC of two seconds. It warns two seconds before independently checked contact at six seconds. Raw misses this diagnostic. This constant-speed example explains the mechanism; it is separate from final evaluation.”

**1:20–1:55 — Trade-off / evaluation-027**

“Here projection correctly estimates the current gap as thirty metres, but the extra warning counts as false. The episode ends at ten seconds; contact would occur at twelve and a half. Our negative label means no contact inside that horizon. Better state accuracy therefore does not automatically produce a better score, and the label is not driving advice.”

**1:55–2:15 — Unchanged / evaluation-001, then result table**

“Clean zero-age data leaves both methods unchanged. Across evaluation, both have 31 useful, two late and five missed outcomes out of 38 contact episodes. Negative warning episodes rise from 26 to 35 out of 38. Raw remains the default; this comparison does not support a universal improvement claim.”

**2:15–2:40 — verification and limit**

“The project includes independent event and metric fixtures, causal replay checks, regression cases, complete evidence audits and a reproduced locked environment. It is still a small one-dimensional synthetic model, not real-world safety validation. The source, configurations and reproduction commands are available in the repository.”

## Practical presentation

Open the generated page before starting. Use its section navigation; expand a plot only if the timing calculation needs it. Keep the complete report available through the results link. State explicitly if showing a saved run instead of generating live.

The three examples are entry points into all 157 pairs, not a new selected benchmark. The diagnostics use threshold 2 s / maximum age 3 s, while the main evaluation uses threshold 3 s / maximum age 1.25 s; do not pool them. Keep misses, late warnings, negative episodes and unavailable estimates visible when answering questions.

A full rerun or environment installation need not occupy the spoken presentation. Show the exact reproduction command and its saved manifest; use the short script to explain the evidence rather than wait through setup.

## Evidence and boundaries

The published baseline's verification includes two byte-identical 1,426-file demo packages, with all 1,424 evidence files matching their source. Static checks cover two HTML pages, 1,114 contained links and three valid 1200×1200 plots. See [verification](verification.md) for exact revisions and scope.

An additional boundary check verifies the horizon explanation: the scaled braking case has lead rear stopped at 150 m and ego front at `12*t` m. Its gap is 30 m at H=10 s; extending only `sample_count` from 9 to 11 at dt=1.25 s gives H=12.5 s, final gap zero and contact exactly at the inclusive endpoint. Earlier samples are unchanged. The frozen evaluation configuration/results were not altered.

The [results](results.md), [architecture](architecture.md), [investigation](c1-investigation.md), [reproduction guide](reproduction.md) and [verification record](verification.md) supply the supporting detail.
