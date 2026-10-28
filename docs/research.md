# DriveCheck research and decisions

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
