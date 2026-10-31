# DriveCheck research and decisions

## M3 stop-and-go checkpoint verified — 31 October 2026

The learner saved the supplied continuous stop/hold/restart/cruise model and14 tests. Assistant source/test review and an independent read-only audit found no material blocker; no source/test repair was needed. Actual project-interpreter runs passed14 focused tests and104 full-suite tests (full run41.042s), both exit0. Independently derived references match: gap15 contact5/final2; gap18 no contact/minimum2 at6/final5; gap16 tangent6. Coarse samples `[15,3,2]` retain an analytic5s event, and the event is invariant across the tested1/0.25/4s grids. Boundary continuity, zero-width phases, horizons, signed quadratic cancellation/tiny-time fixtures and existing fault/replay/scoring integration pass.

The model uses constant acceleration within phases, with lead speed capped at zero or the restart target and consistent travel distances. Its signed-acceleration solver is separate from M1's braking-only helper; reference labels remain literals, not TTC/solver outputs. M1's32-ULP endpoint convention is retained. Source evaluation is bounded to the declared horizon, while prescribed virtual paths continue after contact. The implementation rejects unsupported non-finite/lost-resolution calculations rather than promising arbitrary extreme-input support. The reviewed checks do not exercise every numeric guard. The existing report CLI is not yet extended to this family; integration later must select `stop_go_truth_at` for its offline truth callback. No new report/plot/install/Git action, learner mastery or remote CI is claimed.

## M3 checkpoint 2 verified — 31 October 2026

The learner saved the supplied injector and `test_m3_injection.py` and requested review. No source/test repair was needed; independent read-only review found no material blocker. Actual project-interpreter runs passed all 26 tests across the two M3 modules and all 90 project tests (full run 22.456 s), both exit 0. Explicit fixtures verify 20 m/5 m/s changed by −2 m/+1 m/s to 18 m/6 m/s (TTC 3 s), the 2→2.5 s jittered delivery, strict dropout boundary, all-dropout unavailable replay/missed literal contact, M2 clean/fixed-delay compatibility, retained beyond-horizon arrivals, draw-call order, input/overflow guards, unchanged truth and repeatable causal replay.

The implementation uses single-fault conditions: Gaussian additive gap/closing errors, base delay plus nonnegative uniform jitter, and Bernoulli dropout. A dropped row's audit arrival is hypothetical; pending arrivals count retained observations only. Canonically ordered truth is prevalidated before RNG creation, while M2 observation storage can remain unordered. These are experimental design choices, not measured sensor specifications. Four private streams isolate random state; this check does not establish statistical independence or cross-version Gaussian identity. No installation, new integrated report/plot, source/test repair, Git action or remote CI result was performed. Stop-and-go, systematic boundary/failure investigation and the integrated study remain pending.

## M3 checkpoint 1 verified — 31 October 2026

The learner saved the supplied `FaultConfig`, private-generator factory and 11 tests, then supplied an import failure. Inspection found `make_rngs` inside the class body: the name existed in class scope but not as the requested module-level import. The assistant dedented that function only, preserving its body and all test assertions. Actual project-interpreter verification passed 11 focused tests and 75 full-suite tests (22.930 s for the latter), both exit 0; an independent read-only review found no additional material blocker. No new dependency, fault-injection algorithm, Git mutation or remote CI run was introduced. Validated settings and separate seeded state are implemented; transformation arithmetic, dropout audit/draw order, timestamp overflow and scenario/failure work remain later checkpoints.

## M3 settings and reproducibility check — 31 October 2026

The assistant rechecked the primary Python 3.14 documentation while preparing the learner's first M3 block. [random.Random](https://docs.python.org/3.14/library/random.html#random.Random) supports generator instances with separate state; [reproducibility notes](https://docs.python.org/3.14/library/random.html#notes-on-reproducibility) distinguish repeatable compatible seeded sequences from distribution implementation changes across Python versions. The teaching design uses four private generators and records explicit seed/settings/runtime provenance. Separate state is not a claim of statistical independence or guaranteed different outcomes for different seeds.

[Frozen dataclasses](https://docs.python.org/3.14/library/dataclasses.html#frozen-instances) reject ordinary field assignment. Type annotations alone do not validate constructor inputs, so FaultConfig's proposed post-initialization checks reuse the existing finite-number helper and explicit mode/probability/seed policies. Single-fault modes are an experimental isolation choice, not a sensor standard. This block uses only the existing standard library; no installation, product implementation or test run was performed to prepare it. Proposed checkpoint-1 code/tests are supplied for learner implementation in chat; M3 acceptance remains pending.

## M2 final age-limit investigation completed — 2026-10-31

At the learner's explicit request, the assistant ran the final changed-setting experiment instead of requiring learner execution/teach-back. `configs/m2-age-075.json` differs from the default only at warning.max_age_s (1.25 to0.75). Actual CLI run in fresh outputs/m2-age-075 completed6/6/exit0; the full suite passed64 tests again. All40 artifact hashes, source/config hashes and40 local references match. Truth CSV/PNG and observations are byte-identical to the default in every case; clean decision CSVs are identical. Delayed cases contain one unavailable then4/5/8 stale rows, zero fresh rows, no warnings and null MAEs. The contact is missed1/1 and false-warning negatives fall from2/2 to0/2; clean outcomes are unchanged. Stricter freshness suppresses all delayed evidence, including the contact warning. No claim of improved overall warning quality follows.

Technical M2 acceptance is complete within the declared synthetic scope. Assistant supplies a plain-language explanation; learner-independent interpretation is unassessed, without a repeated quiz gate. Final config/docs need a learner-controlled commit before merging. Read-only live Git check confirms the earlier report feature head aea9075 and main48276e3; main is an ancestor, so a fast-forward merge is available. No Git mutation, M3 work or remote CI result is included.

## M2 default report checked — 2026-10-31

The learner saved the final supplied integration block and requested help with its import failure. Assistant renamed `drivehceck.py` to `drivecheck.py` and corrected the metric helper's name/parameter to `aligned_errors(decisions, scenario)`, preserving test expectations. Six report tests and64 full-suite tests pass. A normal CLI run completed all six configured cases in `outputs/m2-first`; saved data,40 artifact hashes, source/configuration provenance,40 local references and all distinct plots were checked. Integration tests cover repeated canonical data, rejected preflight inputs and retained injected case/report failures. These are local synthetic results, not clean-environment or remote CI evidence.

With unchanged threshold3 s, accepted age1.25 s, matching window4 s and minimum useful lead1 s, the braking-contact warning changes from2 s/useful (lead1.316625 s) to3 s/late (lead0.316625 s) under a1 s delivery delay. Both negative episodes warn in each condition under their declared horizons. Fresh-reading errors are compared with truth at decision time, equally weighted by eligible decision row over the full horizon; unavailable/stale rows are counted and excluded. Default delayed gap/closing-speed MAEs are5 m/0 m/s,12.5 m/3 m/s and7.5 m/2.5 m/s. No thresholds were tuned to obtain these outcomes. Learner interpretation and the changed-setting exercise remain pending; noise/dropout and stop-and-go are M3 work.

## M2 replay/warning lesson choices — 2026-10-30

Implementation checkpoint later on 30 October: the learner saved the supplied replay/policy/test block, provided a failing run and explicitly requested repair. A targeted `replay.py` fix restored the clock endpoint/order checks and selected-reading initialization. The unchanged warning policy/test expectations then passed 12 focused and 46 full-suite tests. The choices below now describe an implemented, locally checked replay/TTC baseline; independent scoring and a full comparison report remain pending. No warning-quality result or remote CI is established by these tests.

For the learner's next implementation block, the assistant rechecked the official [SUMO following TTC definition](https://sumo.dlr.de/docs/Simulation/Output/SSM_Device.html#ttc): positive gap divided by positive follower-minus-leader speed. This supports the mathematical baseline, not a universally safe warning threshold. No third-party implementation was copied or run.

The previously declared policies are a 3 s threshold, maximum age 1.25 s inclusive, raw held arrived values without extrapolation, null TTC/no warning for unavailable/stale data, zero TTC/warning for fresh contact/overlap, and null TTC for positive gap with nonpositive closing speed. These are project experiment choices. Replay releases only arrival <= decision time, consumes all simultaneous arrivals, selects the latest measurement time and never receives a contact label. A wrapper retains the decisions and two arrival audit counts. The pending offline scorer remains independently defined with a 4 s pre-event window and 1 s minimum useful lead; these conventions have not yet been evaluated in the full report.

Checked 2026-10-25. These are bounded kickoff checks, not validation of a completed product. No external code was copied or run.

## First slice

Use a CPU-only, one-dimensional relative-motion example before a braking scenario. Start with constant forward speeds so the expected gap can be checked by hand. This teaching fixture now supports M0 foundations completion; it does not implement either required scenario family. No simulator, dashboard, estimator, or large dependency set is needed for it.

Define gap as the clear distance from the ego vehicle's front bumper to the lead vehicle's rear bumper. Both move along the same forward axis. Closing speed is ego speed minus lead speed. Keep seconds, metres and metres/second explicit.

## Primary sources

- Eclipse SUMO, SSM Device, TTC and encounter types: <https://sumo.dlr.de/docs/Simulation/Output/SSM_Device.html#ttc>. The documentation defines TTC under unchanged current speeds and gives the following-vehicle gap and speed-difference conventions. This supports a simple relative-motion baseline; it does not establish a universal warning threshold or real-world safety.
- Official SUMO implementation, `computeTTC`: <https://sumo.dlr.de/daily/doxygen/d8/d6e/_m_s_device___s_s_m_8cpp_source.html>. Bounded read-only review by the research agent found gap divided by follower-minus-leader speed, zero for non-positive gap, and an invalid value for non-positive closing speed. The daily source is mutable; pin a revision before reusing implementation details. No source code was copied.
- Python 3.14, `venv`: <https://docs.python.org/3.14/library/venv.html>. A project-local environment isolates dependencies. Its interpreter can be invoked directly without activation or an execution-policy change. M0 creation was completed after the explanation; observed evidence is recorded below.
- pytest getting started: <https://docs.pytest.org/en/stable/getting-started.html>. Tests can express independently calculated expected answers with assertions. Version 9.1.1 was checked through <https://pypi.org/pypi/pytest/json>: requires Python >=3.10; MIT license. This is a candidate, not an installed or tested project dependency.
- pytest license: <https://docs.pytest.org/en/stable/license.html>. Preserve required notices if redistributing third-party software. Review exact resolved dependency licenses when selecting the lock/install approach.
- NumPy 2.4.0 release notes: <https://numpy.org/doc/2.4/release/2.4.0-notes.html>. Documents support for Python 3.11–3.14. This compatibility check does not select that release; NumPy is deferred until it earns its place.

M0 selected the existing Python 3.14.7, avoiding a new runtime installation. My assistant created `.venv` and verified its interpreter version and `include-system-site-packages = false`. I completed `motion.py` and the independent known-answer test using teaching templates, supplied my own run output and a qualitative explanation, and saved the test correction. My assistant's final run produced `20.0 m` and one passing unittest, both with exit code 0. This verifies the current environment; a fresh-machine/clean-environment reproduction is not yet claimed.

For the first known-answer test, use standard-library `unittest`: <https://docs.python.org/3.14/library/unittest.html>. The official documentation describes test cases that compare a response with an expected answer and a command-line runner. This keeps M0 free of third-party project dependencies; pytest remains a later candidate. There is no third-party project dependency set to lock for this exercise; record Python 3.14.7 and use its standard library. Revisit dependency pins, transitive licenses and a lock mechanism when adding external packages.

M0 rechecked the Python 3.14 `venv` documentation above on 2026-10-25. It confirms default isolation from base packages, bundled pip bootstrapping, and direct use of the environment interpreter without activation. The rolling 3.14 documentation currently labels itself 3.14.9; the locally observed interpreter remains 3.14.7. No interpreter upgrade was performed.

## Open decisions

For the optional VS Code editor path, checked official environment guidance on 2026-10-25: <https://code.visualstudio.com/docs/python/environments>. It documents `Python: Select Interpreter` and use of the selected environment for running/debugging/language features. VS Code/editor extension installation and the learner's selected interpreter are not observed; this is guidance conditional on their editor choice.

- Establish actual learning pace before promising a release date.
- Select and verify dependency locking when third-party project packages are introduced; M0 used only the standard library. The learner's script/test runs and explanation were reviewed; deeper understanding should be assessed through later attempts.
- Define contact, missing data, timestamp policies, warning thresholds, and independent scoring conventions before their respective implementation steps.
- TTC prediction under constant speeds is distinct from contact observed in a trajectory. Acceleration may change a later outcome. No warning threshold is currently chosen.
- CARLA and Kalman-filter research are deferred until the CPU core is usable and the user chooses an extension.

## Portfolio positioning — bounded check, 2026-10-25

The official SUMO SSM documentation already describes traffic safety metrics and configurable output. CARLA's official ScenarioRunner repository already provides scenario definition/execution: <https://github.com/carla-simulator/scenario_runner>. These sources establish existing capabilities, not applicant rankings or hiring outcomes.

Assessment: a simple TTC/noise demonstration is a learning slice. The proposed complete core can provide stronger student-level evidence through independent reference events, causal fault replay, reproducibility, meaningful tests, and one original failure investigation. An estimator comparison or CARLA adapter is valuable only if it answers a clear question and is evaluated; neither is newly required. No scope expansion or implementation is authorized by this assessment alone.

## Archived assistant M1 reference — technical selection and verification, 2026-10-27

This section records the earlier assistant reference that was subsequently archived. Its 35-test/export/plot results are historical and do not describe the active learner implementation. See README.md for the current implemented features and verified test count.

Bounded primary-source checks preceded implementation. This section records actual local outcomes rather than treating old suggested versions as installed. No simulator, sensor/warning implementation or third-party example code was added.

- [OpenStax University Physics, motion with constant acceleration](https://openstax.org/books/university-physics-volume-1/pages/3-4-motion-with-constant-acceleration) supports the position/speed equations and equating two object positions. DriveCheck separately defines bumper coordinates, delayed braking, a zero-speed cap, signed overlap and an inclusive horizon. Reference events come from independently specified trajectories/answers, never a TTC threshold.
- [Matplotlib 3.11.2 release metadata](https://pypi.org/project/matplotlib/3.11.2/) and [versioned JSON metadata](https://pypi.org/pypi/matplotlib/3.11.2/json) show Python >=3.11 and a Windows CPython 3.14 wheel. The actual installer selected the normal cp314 win_amd64 wheel; no source builds or GPU setup were required. The wheel digest is pinned in the project lock.
- [Matplotlib backend documentation](https://matplotlib.org/stable/users/explain/figure/backends.html) documents noninteractive Agg file rendering. [Figure.savefig](https://matplotlib.org/stable/api/_as_gen/matplotlib.figure.Figure.savefig.html) documents PNG output and explicit DPI. M1 uses Agg, 140 DPI, constrained layout and local files; three final 1260x980 images were visually inspected for units, geometry, phases and event/horizon labels.
- [Python 3.14 unittest](https://docs.python.org/3.14/library/unittest.html) remains sufficient for independent expected values, boundaries and artifact integration tests. No pytest dependency is needed. Model mathematics and CSV/JSON/configuration use the standard library; NumPy is installed transitively by Matplotlib, not required by the motion model.
- [pip install](https://pip.pypa.io/en/stable/cli/pip_install/) documents binary-only selection, install reports and dry-run resolution. [pip secure installs](https://pip.pypa.io/en/stable/topics/secure-installs/) explains hash checking. The assistant installed Matplotlib into the existing isolated environment, generated a full version/hash lock from the actual install report, then successfully checked it with `--dry-run --ignore-installed --only-binary=:all: --require-hashes`. This is verified locked resolution on the existing machine, not a fresh-environment release claim.

Observed runtime: CPython 3.14.7, pip 26.2.1, Windows win_amd64. These were retained. Actual install command: `.\.venv\Scripts\python.exe -m pip install --only-binary=:all: --report .\outputs\m1-install-report.json matplotlib==3.11.2`, exit 0. `pip check` reported no broken requirements. Exact direct/transitive versions and licenses:

| Package | Resolved version | Main license / notices |
| --- | --- | --- |
| matplotlib | 3.11.2 | Matplotlib/PSF-style license; bundled DejaVu/STIX font notices |
| contourpy | 1.4.0 | BSD-3-Clause |
| cycler | 0.12.1 | BSD-3-Clause |
| fonttools | 4.67.0 | MIT; external notices |
| kiwisolver | 1.5.1 | BSD-3-Clause / modified BSD |
| numpy | 2.5.4 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0; bundled library notices |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause |
| pillow | 13.0.0 | MIT-CMU; bundled notices |
| pyparsing | 3.3.3 | MIT |
| python-dateutil | 3.0.0 | Apache/BSD dual license |
| six | 1.17.0 | MIT |
| tzdata | 2026.5 | Apache-2.0 package; retain IANA data notices |

Exact-version primary PyPI links, installed license-file paths, metadata excerpts and wheel hashes were recorded in the assistant reference's dependency inventory and twelve-package hash lock. At the user's later request to restore the learner code, those files were archived privately with the assistant reference. Full installed license texts remain in `.venv/Lib/site-packages`; the short table is not a replacement for notices when redistributing dependencies. The historical lock targets Windows CPython 3.14; other platforms/Python versions need separately checked wheel hashes. No dependency bundle/publication occurred.

Method decisions: evaluate closed-form positions rather than Euler integration, so sampling changes do not change the analytic event. Split contact solving at brake/stop boundaries and use cancellation-resistant quadratic roots. Initial touching/overlap is event zero; keep virtual signed trajectories after contact with no impact claim. Contact at the inclusive horizon is allowed, with an explicit 32-ULP endpoint convention scaled to represented endpoint times without a one-second floor. Regression checks cover a 1e-18-second horizon and input/output collision preflight before any writes. Generated reference checks use absolute 1e-9 s/m tolerances; these are numerical test conventions, not sensor accuracy.

Historical assistant-reference acceptance before restoration: 35 tests passed, including the unchanged original test, analytic braking/event/stop cases, horizon/tiny-time/cancellation boundaries, invalid-input rejection, byte-preserving export preflight regressions, failed-run labeling, round-trip artifacts and repeat exports with equal hashes. The final command exports all three fixtures with independent checks passed. The old snapshot/original test/adopted brief SHA-256 hashes are unchanged. There are no warning-quality results yet. Fresh isolated reproduction/CI, sensors/faults and warning/evaluation policy remain subsequent milestones.

## Active learner M1 implementation reviewed — 2026-10-28

I saved the supplied `scenarios.py`, `m1.py` and `test_m1.py` block in the original project and generated the study outputs. My assistant ran `.\.venv\Scripts\python.exe -m unittest -v`: **24 tests, OK, exit 0**. Independent source review found no material M1 correctness blocker. The active test count and results are separate from the historical 35-test reference above.

Read-only checks of my existing `outputs/m1-study/` files verified all three CSV/JSON/PNG sets and the complete manifest: 5/6/9 rows, 4/5/8 s horizons, final gaps 10/-32.5/20 m and contact only at sqrt(11) s in the braking-contact case. Configuration, source/test/requirements hashes and artifact hashes match the saved active files. All three 1400x1050 plots were opened and inspected for units, phase markers, continuous contact between samples, stopped lead motion and visible negative gap. The study files were not rewritten during review.

The three integration tests check export/read-back and repeated artifact hashes on this machine, explicit failed-reference status, and invalid/empty destination preflight. They do not establish every possible filesystem failure or cross-platform pixel identity. The active runner uses `run(output_dir=None, fixtures=None)` and immutable Fixture records; older lesson scaffolds describe alternative proposed interfaces.

The active `requirements.txt` snapshot matches all 12 installed runtime dependency versions, excluding pip; runtime provenance separately records pip. This is resolved version pinning, not a wheel-hash lock, a new installation or a fresh-environment reproduction. No warning/fault/CI result or independent learner mastery is claimed. My final explanation and changed-input review remain pending.
