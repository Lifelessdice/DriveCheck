# M3 study lesson: controlled faults and trustworthy regression tests

### Current acceptance — 1 November 2026

**All five M3 technical blocks are accepted locally.** The learner saved the supplied final driver/test module and produced `outputs/m3-study/run-a` and `run-b`. Assistant review required no product edits. Actual project-interpreter checks passed all seven new tests in7.115s and the full131-test suite in47.831s, both exit0. Independent read-only source/artifact review found no material acceptance blocker. Learning explanations/transfer remain separate and unassessed.

Each saved run is complete at28 main cases plus5 separately summarized diagnostic arms. All164 files match byte-for-byte between runs; each run's163 artifact hashes, configuration/source hashes and181 contained local references match. Saved observations/audits/decisions/counts and causal latest-available sample selection were checked. All12 default figures were visually reviewed. Main seed100 counts are recorded in README/research: latency_low has1 useful/1 late, latency_strong0 useful/1 late/1 missed, and both clean negatives warn. The separate diagnostic matches useful/useful/late/late/missed, with first4/5/5.5/6/None. No seed200, clean-environment reproduction, browser-rendered HTML layout or remote CI result is claimed.

Branch remains `feature/m3-fault-suite` at419c2e2 with the final checkpoint uncommitted. Next is selective learner staging/commit/push of `m3_study.py`, `test_m3_study.py`, README and the four reviewed public M3/roadmap/research documents, then learner-run fast-forward merge/push of main. Assistant performed no Git mutation, product changes, dependency installation or persistent study rerun in this acceptance review. M4 remains future release/configuration/CI work.

### Historical final delivery — 1 November 2026 (before implementation)

Read-only Git inspection observes learner checkpoint `419c2e2` on `feature/m3-fault-suite`, matching the configured remote-tracking ref, with clean tracked files before this documentation update. This is not a new live-remote or CI check. Four of five M3 blocks remain verified at the prior 124 passing tests.

The final chat block supplies complete proposed `m3_study.py` and `test_m3_study.py` for learner implementation. Neither file nor integrated study outputs exist at this delivery. The study enumerates 28 main rows (four fixtures, seven single-fault profiles) and five separately summarized fixed-delay diagnostic rows. The main policy remains threshold 3 s, maximum age 1.25 s, matching window 4 s and minimum useful lead 1 s; diagnostic settings remain those in `m3_regression.py`. A seed base of 100 maps to streams 101/102/103/104. Reused streams do not establish independent replications.

The concrete final layout supersedes the earlier suggested layout below: root `manifest.json`, `configuration.json`, `study-summary.json`, `cases.csv` and `report.html`; shared truth/configuration/reference under `truth/<scenario_id>/`; 28 `cases/case-001` through `case-028` folders and five `cases/regression-001` through `regression-005` folders containing observations, audit, decisions and result JSON. Default plots are selected before outcomes: all four clean main cases, three strong-fault conditions for both contact fixtures, and clean/2.5 s diagnostic arms (12 figures). `--all-plots` requests all 33. Every declared result remains in the manifest, including failed executions; incomplete studies exit nonzero. Artifact hashes exclude the manifest itself to avoid a self-reference cycle.

The driver must preserve M2, validate independent references and fresh contained output paths before writing, bind the correct stop-and-go truth evaluator, hash immutable truth snapshots, export full precision/null metrics, record source/configuration/runtime/draw-order provenance, and keep full-horizon equally weighted fresh-decision-row MAEs explicit. Jitter changes arrival-grid row weighting. Plotted virtual post-contact motion is diagnostic, not impact physics or warning-driven control.

Seven proposed tests cover the declared matrix/policies, repeated exports/read-back/hashes/local links, real plots for both motion families, retained case failures/nonzero CLI, retained machine data after report failure, preflight guards, and render selection without changing scientific rows. Expected full count is 131 if saved as supplied; this is not an observed run. Next: learner saves both distinct files, runs the supplied commands in fresh folders, and reviews actual artifacts and plots. Only then review/checkpoint/push and guide the final merge. No source/test/configuration write, implementation command, dependency install or Git mutation was performed for this delivery.

Prepared 27 October 2026; current acceptance is recorded above. At the31 October checkpoint, blocks1–4 were verified at124 tests and the integrated study was still proposed. Block4 required an explicitly requested assistant file-layout repair/restoration. The dated delivery notes below preserve that earlier progression; the1 November acceptance supersedes their pending status.

### Current learner delivery — 31 October 2026

M1/M2 technical acceptance and the learner's M2 main integration are recorded. Read-only inspection now verifies `feature/m3-fault-suite` at the completed M2 commit `f67522a`, with no tracked changes before this lesson update. The earlier authoring snapshot below is historical; active M1 files are the later guided learner implementation, and M2 modules now exist. The recorded 64-test/two-report M2 acceptance is not a new M3 test run.

The learner confirmed substantial blocks, theory explained alongside code, concrete progress after each block, a reviewed learner-run commit/push per block on this branch, and a final merge at the end. The seven teaching blocks below are bundled into five implementation checkpoints:

| Checkpoint | Scope | Current evidence |
| --- | --- | --- |
| 1 | Validated immutable FaultConfig, private random streams and focused tests | Verified; learner checkpoint commit 3fc7f17 observed |
| 2 | Explicit-draw arithmetic, individual seeded faults, audit and truth protection | Verified without source fixes; learner checkpoint commit 4a95e81 observed |
| 3 | Stop-and-go continuous motion and independent contact/non-contact fixtures | Verified without source fixes; learner checkpoint commit 7530c4e observed |
| 4 | Causal/data/metric boundaries and a reproduced fault-induced regression | Verified after requested file-layout repair; 20 focused/124 full tests OK; learner checkpoint 419c2e2 observed |
| 5 | Integrated saved study, plots, result interpretation and M4 handoff | Verified1 November;7 new/131 full tests OK; two complete33-case runs and12 plots reviewed; final Git checkpoint pending |

For checkpoint 1, use the actual `motion.require_finite` helper for nonnegative numeric settings; it validates and returns None, so do not assign its return to a field. Check probability <=1 separately. Validate mode type before membership, and validate nonnegative integer seeds excluding bool. Enforce the single-fault inactive-field rule after numeric checks. `make_rngs` returns fresh gap/closing/latency/dropout generators. No observation transform is implemented in checkpoint 1; timestamp/value overflow is checked later when those values are computed.

The checkpoint-1 tests cover valid/invalid/frozen settings, fresh reproducible generators, stream isolation, changed-seed isolation and global-state preservation. The learner's first command failed before test discovery because `make_rngs` was indented inside `FaultConfig`; importing it directly from `faults` requires module scope. The assistant dedented only that function, preserving its body and all test assertions. Actual assistant verification: `python -m unittest -v test_m3_faults` ran 11 tests, OK/exit 0; `python -m unittest -v` ran 75 tests, OK/exit 0 in 22.930 s. Independent read-only review found no additional material blocker for this bounded block. This is guided implementation with a targeted repair, not independent debugging/mastery evidence. Existing replay returns `ReplayResult`, so later integration reads `.decisions`; scoring reuses `evaluation.score_case`. No new dependencies or M2 rewrites were needed. Next is learner-controlled checkpoint commit/push, then fault injection.

The next read-only checkpoint confirms local commit `3fc7f17` (`Add validated M3 fault settings and random streams`) on `feature/m3-fault-suite`; its configured remote-tracking ref matches and tracked files are clean. This is local Git evidence, not a new live-remote/CI check. The learner requested continuation, so checkpoint 2 now supplies `apply_draws` and `inject_faults` for learner implementation, with a new `test_m3_injection.py` module preserving the first 11 tests.

Checkpoint-2 contract: source `TruthSample` IDs/times increase strictly (gaps and nonzero starting IDs allowed); numeric fields are finite, forward speeds nonnegative and scenario identity consistent. This is a generation-order rule; M2 observation storage may still be unordered. Prevalidate the complete source before creating RNGs. Validate direct explicit-draw calls too, including inactive Gaussian/uniform draws. Compute and validate finite errors/delay/arrival/values before dropout suppression. Reserve gap Gaussian, closing Gaussian, latency uniform and dropout uniform calls in that order for every source row. Return `(observations, audit_rows)`, with a raw-draw/error/delay audit for every source, and reuse M2 Observation unchanged. A dropped row's audit arrival is hypothetical; pending arrivals are counted only among retained observations.

Proposed checkpoint-2 code/tests are supplied in chat, not written or run by the assistant. There are 15 new test methods, with an expected 90 total only if the accepted 75 remain unchanged. Fixtures include 20 m/5 m/s with errors −2 m/+1 m/s producing 18 m/6 m/s and TTC 3 s, a 2 s reading with 0.25 s base plus 0.5 s jitter times 0.5 arriving at 2.5 s, strict dropout comparison, all-dropout unavailable replay/missed contact, repeatability and immutable truth/reference, before-RNG input rejection, finite overflow guards and the mock call-order regression. Fault mechanisms will be implemented by this block; systematic boundary/regression investigation and report evidence still belong to later checkpoints.

Checkpoint-2 acceptance, 31 October: the learner reported saving the supplied injector/test file. Assistant inspection confirmed all 15 intended new test methods and found no required source fix; independent read-only review found no material blocker. Actual project-interpreter `-m unittest -v test_m3_faults test_m3_injection` ran 26 tests, OK/exit 0; full `-m unittest -v` ran 90 tests, OK/exit 0 in 22.456 s. Tests verify the independent arithmetic above, complete dropout preserving seven clock ticks and scoring the literal 6 s contact missed, clean/fixed-delay M2 compatibility, five retained arrivals beyond the horizon distinct from dropout, four reserved API calls per source, invalid/overflow rejection and unchanged repeatable truth/config/reference/replay. No dependency, source/test repair, new report run, Git mutation or new plot result occurred in this review. Learner explanation/independent transfer remains unassessed. Commit/push on the existing branch is next, followed by stop-and-go.

Checkpoint-3 delivery, 31 October: learner reported pushing Block2. Local read-only inspection observes commit `4a95e81` (`Add seeded sensor fault injection and audit tests`) on `feature/m3-fault-suite`, matching the configured remote-tracking ref with clean tracked files. This is not a new live-remote/CI check. The supplied next block creates `stop_and_go.py` and `test_m3_scenarios.py` in the original project when the learner follows it; the assistant has not written/run that product code.

The proposed `StopGoScenario` reuses a temporary M1 `Scenario` only for common input guards, then checks positive braking/restart acceleration, nonnegative hold/target speed and finite derived phase times/distances. Zero-width phases are supported; a positive phase duration lost to floating-point resolution fails explicitly. Its truth evaluator is bounded to `[0,H]`, emits the existing TruthSample fields and keeps prescribed virtual paths after contact. A new signed-acceleration phase solver is required because M1's `contact_delay` accepts braking magnitude only. Search continuous phases, inspect both stable quadratic roots, include tangent contact, reject non-finite/zero-rounded polynomial results, and preserve M1's 32-ULP endpoint convention without a 1-second floor. Stored numeric references remain literal/independently derived, never filled by that solver.

The complete supplied Block3 contains 14 proposed tests: derived phase values; literal truth table/references; non-contact minimum; tangency; grid invariance with positive coarse gaps despite contact; boundary continuity; stop/restart contacts; horizon/initial cases; zero-width phases; stationary ego/no reverse; invalid/overflow settings and queries; early-root/tiny-horizon numerical fixtures; and existing fault/replay/scoring integration. Expected focused count is14 and full count104 only if the accepted90 remain unchanged. These are proposed checks, not observed results. Independent default references are gap15/contact5/final2; gap18/no contact/minimum2 at6/final5; gap16/tangency6. Later integrated reporting chooses this family's own continuous evaluator; it must not call M1's braking evaluator on the new settings.

Block3 acceptance, 31 October: learner saved `stop_and_go.py` and `test_m3_scenarios.py`; assistant reviewed them without any source/test edit. Independent read-only review found no material correctness issue. Actual project-interpreter focused run passed all14 tests (exit0), and the full suite passed104 tests (exit0,41.042s). Verified references include first contact5 despite coarse gaps `[15,3,2]`, no contact/minimum2 at6/final5 for gap18, and tangent contact6 for gap16. Boundary continuity, zero-duration phases, stationary ego/no reverse, horizon and numerical fixtures and clean/all-dropout replay/scoring integration pass. This does not test every numerical-rejection branch or claim arbitrary extreme-input support. No new report/plot/dependency/Git action or later-block implementation occurred; learner explanation/independent transfer remains separate. Next is the learner checkpoint commit/push, then systematic boundaries and failure regression.

Block4 delivery, 31 October: read-only local inspection observes learner commit `7530c4e` on `feature/m3-fault-suite`, matching the configured remote-tracking ref and clean tracked files before this documentation update. No new live-remote/CI check or repeated product run. The complete next block supplies (for learner implementation) `m3_regression.py`, `test_m3_boundaries.py`, `test_m3_regression.py` and a backward-compatible optional `truth_at_time` keyword on `evaluation.aligned_errors`. The callback is validated as callable when provided and invoked only for fresh rows. Default M1 evaluation, result keys and equal-fresh-row full-horizon MAE policy stay unchanged; bind the stop-and-go scenario in the callback. This avoids passing new settings into M1's braking evaluator or creating a second error calculator. No RMSE metric is added in this block.

The reusable regression helper keeps literal contact6, source times0–6 in1s steps, a fixed0.5s decision grid, threshold2, maxage3, window3 and useful minimum1. Delays0/1/1.5/2/2.5 have independently predicted first warnings4/5/5.5/6/None and useful/useful/late/late/missed outcomes. This explicitly separate diagnostic policy is not substituted for M2 defaults. The strongest miss is caused by the alarming ID4 arriving at6.5 beyond horizon6, while ID3 remains fresh/clear at age3; it is not stale rejection. Warnings do not alter truth. One optional age-sensitivity check keeps those future arrivals unavailable even under a larger age limit.

Proposed checks add11 boundary/alignment tests plus9 regression tests (20 total), so expected full count124 assumes the accepted104 are unchanged. They cover adjacent-float arrival/age/window boundaries, ignored alarming old arrivals, nonuniform age, future-value noninterference, five-episode denominators, null empty-subset rates, noise-induced TTC branches, measurement-versus-decision alignment, stop-and-go callback MAE/coverage and the fixed-latency causal trace/repeatability. The signed residual fixture[-2,0,2] yields absolute errors[2,0,2] and MAE4/3 over3 fresh rows with1 unavailable and1 stale row. These are supplied predictions/code, not new implementation or test evidence. Actual checks remain pending learner save/run/review; integrated artifacts/plots remain Block5.

Block4 acceptance, 31 October: learner requested file inspection/repair. The saved `m3_regression.py` contained the11 boundary tests; the two intended test filenames were absent. Assistant reproduced two missing-module errors, moved that content intact to `test_m3_boundaries.py` (before/after SHA-256 identical), and restored the previously supplied regression helper and missing9-test module. The learner's optional evaluator callback change was already correct and was not edited. Actual focused run passed20 tests, OK/exit0; full run passed124 tests, OK/exit0 in27.529s. The five fixed-latency outcomes match their independent predictions, including ID4 arriving at6.5 beyond horizon6 with ID3 fresh/clear at age3. Existing scoring/warning semantics and old M2 tests remain intact. No new integrated report/plot/dependency/Git action or Block5 implementation occurred. This repair is assistant-attributed; learner interpretation/independent transfer remains unassessed. Next is learner checkpoint commit/push, then the integrated study.

Work through this lesson after implementing and checking M2. You can read the complete section now and follow its blocks at your own pace without replying between commands. Keep your own code, outputs and short explanations for review. A passing test is technical evidence; explaining why its answer is correct is separate learning evidence.

## Starting point and destination

M2 asks whether an arrived reading causes a warning. M3 asks whether that answer remains understandable when the reading is wrong, late or absent. You will build three separate fault modes, add stop-and-go motion, check timing and scoring boundaries, and preserve a small failure that another person can reproduce.

The delivery pattern is:

`fixed clean truth → faulted observations → causal replay → unchanged warning policy → independent evaluation`.

Only the observations change between fault conditions. Warnings remain passive: they do not brake either vehicle or change the reference contact event. This is a one-dimensional synthetic model, not evidence of real-world warning safety.

The authoring snapshot contains an AI-created M1 reference in `motion.py`, `scenarios.py`, `m1.py` and `configs/m1-fixtures.json`. Preserving those files does not establish that you implemented or understand M1. The shared [study guide](../study-guide.md) defines later module conventions. At authoring time, M2/M3 product interfaces are proposed; inspect your actual M2 work before importing them.

By the end of your implementation, you should be able to:

- Reproduce a sensor stream from its full configuration and seeds while proving that its truth did not change.
- Trace an observation's measurement time, arrival time, age and use in a decision.
- Check stop-and-go positions and contact independently of sampled rows or a TTC threshold.
- Explain why a delayed observation can cause a late or missed useful warning without a replay bug.
- Run meaningful tests for invalid data, arrival order, missing/stale readings and metric denominators.

### Files you will work on

These are proposed responsibilities, not instructions to replace existing work blindly.

| File | Your responsibility in M3 |
| --- | --- |
| `faults.py` | Validated fault configuration, independent random streams, one observation per retained source sample and an offline fault audit |
| `stop_and_go.py` | A small continuous stop-and-go trajectory returning M1 `TruthSample` fields; independent event fixtures |
| `observations.py` | Reuse M2's `Observation`; add validation only where missing |
| `replay.py` | Extend M2 timing/ordering tests and fix a demonstrated defect if needed |
| `warning_policy.py` | Preserve M2's warning semantics; use explicit experimental parameter overrides for worked fixtures |
| `evaluation.py` | Preserve independent scoring; add known-answer tests and explicit empty-denominator handling |
| `test_m3_faults.py` | Deterministic transforms, seed separation, unchanged truth, fault configuration guards |
| `test_m3_scenarios.py` | Stop, hold, restart, continuity, analytic event and non-contact fixtures |
| `test_m3_boundaries.py` | Arrival, age, ordering, input and metric boundaries |
| `test_m3_regression.py` | Clean versus delayed warnings on the same analytically specified episode |
| `m3_study.py` | A small study driver connecting your modules and saving inspectable evidence; M4 later supplies the release CLI |

Use `warning_policy.py`, because a local `warnings.py` can shadow Python's standard-library module. Keep generated outputs beneath a new `outputs/m3-study/` directory. Preserve the original two-column CSV and M1 fixtures. Do not rename M1's truth schema merely because the trajectory family changes; version a new configuration shape separately.

### Before you implement

From PowerShell:

```powershell
Set-Location 'E:\DriveCheck'
Get-Content -LiteralPath .\docs\study-guide.md
Get-Content -LiteralPath .\observations.py
Get-Content -LiteralPath .\replay.py
Get-Content -LiteralPath .\warning_policy.py
Get-Content -LiteralPath .\evaluation.py
.\.venv\Scripts\python.exe -m unittest -v
```

These are **learner commands to run later**, not commands the lesson author ran. If the M2 files are absent, complete M2 first. If they use different function names, keep their meaning and write the small adapter described below; do not create a second competing observation or scoring implementation. Establish the M2 test baseline before extending it. No new dependency is needed for the M3 model or tests; reuse M1's plotting setup when you reach the evidence block.

## Block 1 — freeze the experiment contract

### Truth and observations have different jobs

M1's `TruthSample` has these fields:

```text
scenario_id, sample_id, time_s,
ego_front_x_m, lead_rear_x_m,
ego_speed_mps, lead_speed_mps, gap_m, closing_speed_mps
```

The positive axis points forward. Gap is `lead_rear_x_m - ego_front_x_m`; closing speed is `ego_speed_mps - lead_speed_mps`. SI units are seconds, metres and metres per second. Negative closing speed means separation is increasing. A signed nonpositive gap means touching/virtual overlap, not missing data.

The shared proposed `Observation` contains only:

```python
# Conceptual shape in observations.py; reuse your M2 definition.
@dataclass(frozen=True)
class Observation:
    scenario_id: str
    sample_id: int
    measurement_time_s: float
    arrival_time_s: float
    gap_m: float
    closing_speed_mps: float
```

Do not put the future contact time, clean positions, clean speeds or fault audit into the warning program's input. A CSV can carry metadata in a separate sidecar; the record has no implicit km/h conversion. Validate the declared schema/units when loading data.

For source row 12 measured at 1.2 s with 0.3 s latency, the observation keeps ID 12 and measurement time 1.2 s, arrives at 1.5 s, and has age 0.4 s when used at decision time 1.6 s. Its time is not relabelled 1.6 s. A dropped row 13 does not cause row 14 to become row 13.

### Make policy choices visible

Use your documented M2 policies. The following explicit lesson convention supports the worked examples; if your M2 differs, record the difference and recalculate the expectations before running them:

| Question | Convention used in this lesson |
| --- | --- |
| Availability | A reading is usable only at `arrival_time_s <= decision_time_s` |
| Arrival order | Release in `(arrival_time_s, sample_id)` order within one scenario |
| Newest state | Retain the arrived reading with the greatest measurement time; a later-arriving older measurement does not roll state backward |
| Missing | Keep the last arrived reading with its original time, or no reading if none has arrived |
| Stale | If `decision_time_s - measurement_time_s > max_age_s`, emit no warning and reason `stale`; equality remains usable |
| No available reading | TTC is `None`, warning is false and reason is `unavailable` |
| Valid nonpositive gap | With a usable reading, TTC is 0 and warning is true; this is an observed condition, not a reference-event label |
| Positive gap, closing speed <= 0 | No finite TTC: use `None`, warning false |
| Positive gap, positive closing speed | TTC is `gap_m / closing_speed_mps`; warn at or below the configured threshold |
| Repetition | Keep decision-level flags for tracing; each contact episode has one exclusive M2 outcome: `useful`, `late` or `missed` |

Validate availability and age **before** using gap/TTC. A stale negative gap does not bypass the stale policy. No-reading, no-finite-TTC and invalid-data outcomes need distinct reasons even if their TTC fields are all null.

The gap/speed TTC expression is supported by the [official SUMO following-vehicle definition](https://sumo.dlr.de/docs/Simulation/Output/SSM_Device.html#ttc). Its constant-speed assumption and the warning thresholds here are different matters: thresholds, maximum age and evaluation windows are our experimental choices. They are not calibrated vehicle-safety requirements.

**Your task:** write a small contract note alongside your M3 code naming the M2 functions used for observation construction, replay, warning and scoring. Describe what happens to an older sample arriving after a newer one. Trace ID 12 above in your own words, including the age calculation. This is the first learning check; continue after writing your attempt.

## Block 2 — independent seeded faults, one fault at a time

### Noise changes a reading's value

Use additive independent zero-mean Gaussian errors for gap and closing speed:

`measured_gap = clean_gap + sigma_gap * z_gap`

`measured_closing = clean_closing + sigma_closing * z_closing`.

Each z is a standard-normal draw. Sigma has the same unit as the value it perturbs: metres for gap and m/s for closing speed. Sigma is not a bound on every draw. Our chosen distribution is a deliberately simple synthetic error model; it is not a measured radar specification.

Consider a clean gap of 12 m and closing speed of 4 m/s. TTC is 3 s. Under a lesson threshold of 2.5 s, this reading does not warn. For a hand-specified test draw `z_gap=-1`, sigma 2 m and zero speed noise, measured gap is 10 m; TTC becomes exactly 2.5 s and the inclusive threshold warns. Alternatively keep gap 12 m and add +1 m/s closing error: TTC becomes 2.4 s. These are independent arithmetic fixtures, not predictions of what a particular seed will draw.

Keep finite negative noisy gaps and negative noisy closing speeds visible under the documented policy. Silently clamping gap to a small positive number changes the error distribution and hides a warning cause. Non-finite values are invalid and must fail validation; missing values are handled through omitted observations.

### Latency changes availability

For source time t, define:

`arrival_time_s = t + latency_s + latency_jitter_s * u_latency`,

where `0 <= u_latency < 1`. This uses nonnegative additional uniform delay. Fixed latency is the special case `latency_jitter_s=0`. It is deterministic and needs no random draw to define its value, although the stream can still reserve a draw for consistent accounting.

Latency does not change measurement time, ID or clean value. It can change which reading is available at a decision. If variable delays reverse arrival order, replay must apply the documented newest-measurement policy. Arrivals beyond the episode horizon remain pending; do not flush them early to improve a score.

### Dropout removes an observation

For Bernoulli dropout, omit a reading when `u_dropout < dropout_probability`. Do not add a zero gap, renumber surviving samples, remove decision ticks or compress elapsed time. Under probability 0 nothing drops; under probability 1 everything drops.

A deterministic diagnostic mask is also useful. If source IDs 2 and 3 are suppressed from times `[0, 1, 2, 3, 4]`, retained measurement times are `[0, 1, 4]`. Decisions still occur at the full chosen decision grid. Label a mask as a diagnostic pattern, not a random sample from the probability model.

### Separate random state from experiment state

Use separate `random.Random` instances for gap error, closing-speed error, latency jitter and dropout. Python documents private generator instances and the Gaussian API; it also cautions that distribution algorithms can change between Python versions. Record runtime, complete settings and draw-order version alongside seeds. [Python random documentation](https://docs.python.org/3.14/library/random.html#random.Random), [reproducibility notes](https://docs.python.org/3.14/library/random.html#notes-on-reproducibility).

This is the proposed construction in `faults.py`:

```python
from dataclasses import dataclass
import math
import random

@dataclass(frozen=True)
class FaultConfig:
    mode: str = "clean"       # clean, noise, latency, dropout
    gap_sigma_m: float = 0.0
    closing_sigma_mps: float = 0.0
    latency_s: float = 0.0
    latency_jitter_s: float = 0.0
    dropout_probability: float = 0.0
    gap_seed: int = 101
    closing_seed: int = 102
    latency_seed: int = 103
    dropout_seed: int = 104

    def __post_init__(self):
        # TASK: implement the validation rules below before using this record.
        raise NotImplementedError("validate the complete fault contract")

def make_rngs(config):
    return {
        "gap": random.Random(config.gap_seed),
        "closing": random.Random(config.closing_seed),
        "latency": random.Random(config.latency_seed),
        "dropout": random.Random(config.dropout_seed),
    }
```

Implement configuration checks as one coherent task:

1. Reject unknown mode; bools and non-numeric/non-finite magnitudes; negative sigmas or delays; probability outside `[0,1]`; boolean, noninteger or negative seeds. Permit zero magnitudes.
2. Reject nonzero fields for inactive fault groups. For example, `mode="noise"` requires delays/jitter/probability zero. `clean` requires all magnitudes zero. Do not silently ignore an accidentally enabled second fault.
3. Check computed arrival and perturbed values remain finite. Overflow should fail with a useful message, not yield a partially valid observation stream.

Create RNGs once at the start of each episode-condition run, not once per sample. Reinitializing at each sample repeats the same error rather than producing a sequence. Do not call global `random.seed()` or derive seeds with Python's process-randomized `hash()`.

Keep provenance honest: clean mode and fixed latency with zero jitter have no stochastic effect. Their result-level stochastic seed can remain null as in M2, with a note that the injector reserves private draws internally. Save the full `FaultConfig` for exact procedural reproduction, but do not present unused seed fields as independent random experimental replications. Jitter, noise and probability dropout identify their active stream seeds explicitly.

Draw from all four private streams for **every source row, before checking dropout**, in a fixed order. Build the entire noise/delay audit, then omit the dropped observation. Changing dropout settings must not move the gap-noise stream forward by a different number of samples. Keeping separate state is an engineering isolation choice; it does not prove mathematical independence of every finite generated sequence.

```python
# Proposed loop interior: implement around your existing Observation type.
z_gap = rngs["gap"].gauss(0.0, 1.0)
z_closing = rngs["closing"].gauss(0.0, 1.0)
u_latency = rngs["latency"].random()
u_dropout = rngs["dropout"].random()

gap_error_m = config.gap_sigma_m * z_gap
closing_error_mps = config.closing_sigma_mps * z_closing
delay_s = config.latency_s + config.latency_jitter_s * u_latency
dropped = u_dropout < config.dropout_probability

# TASK: validate results; append an audit row for every source ID.
# If retained, construct Observation with measurement_time_s=truth.time_s,
# arrival_time_s=truth.time_s+delay_s and the perturbed gap/closing speed.
# Never modify truth or append its future event time to Observation.
```

The offline audit can contain source ID/time, errors, delay and dropped flag. Store it separately from observations and decisions. It helps distinguish a dropped sample from a retained one whose arrival is beyond the horizon. The warning algorithm must not receive this audit.

### Tests that distinguish correctness from randomness

Separate the numeric transform from the RNG loop. Give the transform explicit draws so its arithmetic can be checked without depending on a particular generated sequence. A useful proposed helper is:

```python
def apply_draws(sample, config, *, z_gap, z_closing, u_latency, u_dropout):
    """Return (observation_or_none, audit_row); do not mutate sample."""
    # TASK: implement the equations and construction described above.
    raise NotImplementedError
```

For this helper validate finite z draws and uniform draws in `[0,1)` as well as configuration/source validity. The outer `inject_faults(truth_samples, config)` owns generators and calls it. Let the outer function accept an optional RNG bundle for a deterministic fake in tests, or mock `make_rngs` with `unittest.mock.patch`.

Use a clear outer return contract: `(observations, audit_rows)`, with one audit row per source sample and one observation per retained sample. An audit row records the source ID even when the observation is omitted.

Write these tests in `test_m3_faults.py`:

| Fixture | Independently expected check |
| --- | --- |
| Gap 12, closing 4; sigma gap 2, z gap −1 | Observed gap 10, closing 4; source unchanged |
| Latency 0.25, jitter 0.5, supplied u 0.5, source t=2 | Arrival 2.5, measurement 2; gap/closing unchanged |
| Probability 0.2, supplied u 0.19 | Omitted observation; audit identifies source ID |
| Probability 0.2, supplied u 0.2 | Retained observation; strict dropout boundary |
| Probability 0 and 1 | All retained versus none retained; decision grid unchanged |
| Same truth/config/seeds injected twice | Equal observations and audit; original truth still equal to its saved snapshot |
| Different gap seed only | Timing, dropout mask and closing-error audit unchanged; use supplied fake sequences to prove isolation exactly |
| Different dropout seed only | Per-source noise and delay audit unchanged |
| Clean mode | Every observation equals source gap/closing with equal measurement/arrival times |

For truth protection, use `before = tuple(asdict(row) for row in truth_samples)` and compare it afterward. Also compare reference event/configuration before and after faults; unchanged rows alone would not detect accidental event relabelling. Build clean truth once and reuse it across conditions.

Do not assert that a second seed *must* change a warning, or that a short sequence has exactly its configured mean/dropout proportion. Those are flaky tests of an outcome that probability does not guarantee. Draw-value fixtures test arithmetic; repeatability/isolation tests test engineering properties.

There is a subtle test trap here: our single-fault rule prevents enabling noise and dropout together. In dropout mode the noise magnitudes are zero, so shifted Gaussian draws can still produce identical zero error arrays. Test the **API call count and order** directly to detect skipped work on dropped rows. Do not rely only on output errors for this property.

This proposed test uses five source rows with exactly two deliberate drops. It checks one intended call per row per stream, including dropped rows. It does not inspect how many internal uniform draws Python's Gaussian implementation uses:

```python
from types import SimpleNamespace
from unittest.mock import patch
from motion import Scenario, sample_truth
from faults import FaultConfig, inject_faults

def test_draws_are_reserved_even_for_dropped_rows(self):
    calls = []

    def fixed_draw(label, value):
        def draw(*args):
            calls.append(label)
            return value
        return draw

    dropout_draws = iter([0.1, 0.9, 0.2, 0.8, 0.7])

    def next_dropout():
        calls.append("dropout")
        return next(dropout_draws)

    fake_rngs = {
        "gap": SimpleNamespace(gauss=fixed_draw("gap", 1.0)),
        "closing": SimpleNamespace(gauss=fixed_draw("closing", -1.0)),
        "latency": SimpleNamespace(random=fixed_draw("latency", 0.5)),
        "dropout": SimpleNamespace(random=next_dropout),
    }
    rows = sample_truth(Scenario("draw_order", 30.0, 10.0, 5.0, 1.0, 5))
    config = FaultConfig(mode="dropout", dropout_probability=0.3)
    with patch("faults.make_rngs", return_value=fake_rngs):
        observations, audit = inject_faults(rows, config)

    self.assertEqual(calls, ["gap", "closing", "latency", "dropout"] * 5)
    self.assertEqual([row.sample_id for row in observations], [1, 3, 4])
    self.assertEqual(len(audit), 5)
```

Place this method inside your `unittest.TestCase` class, with the imports at module top. The helper's fixed values are test inputs, not Gaussian samples or seed outputs. Temporarily moving draws after the dropout check should fail the ordered-call assertion even though all multiplied noise errors are zero. Restore the documented order afterward.

Run after creating the test file and implementing its targets:

```powershell
.\.venv\Scripts\python.exe -m unittest -v test_m3_faults
```

**Expected later:** the named tests finish with `OK`, and there are no `NotImplementedError` paths left in implemented functions. No test count or successful result is promised here.

**Your meaningful attempt:** change only the gap-noise magnitude in a fixture and predict the TTC effect before running it. Then introduce a deliberate bug that draws noise only after dropout; show which isolation test detects the bug, and restore your correct code. Record what the test establishes.

## Block 3 — causal replay boundaries and invalid data

The fault generator can know a complete future stream offline. The warning component cannot. Give replay a schedule and expose only readings that have arrived at each decision time.

For a small precomputed stream, sorting once by `(arrival_time_s, sample_id)` and advancing a cursor is sufficient. A priority queue is an alternative for online insertion; Python's [heapq documentation](https://docs.python.org/3.14/library/heapq.html) describes a min-heap whose next popped item is the smallest. You do not need to introduce a queue framework to handle these short fixtures.

### Trace out-of-order arrivals by hand

Use the following valid synthetic observations. Their gap values are arbitrary diagnostic inputs, independent of the truth generator.

| ID | Measurement (s) | Arrival (s) | Gap (m) | Closing (m/s) |
| ---: | ---: | ---: | ---: | ---: |
| 0 | 0.0 | 0.8 | 10 | 2 |
| 1 | 0.5 | 0.6 | 9 | 2 |
| 2 | 1.4 | 1.4 | 7 | 2 |

At decision 0.59 s, nothing is available. At 0.6 s, ID 1 is available and has age 0.1 s. At 0.8 s, ID 0 has also arrived, but it is older than ID 1; keep ID 1 as state with age 0.3 s. Log ID 0 as released but ignored for state. At 1.4 s, use ID 2, age zero. Availability ordering and state freshness answer different questions.

Proposed replay logic to finish/adapt in `replay.py`:

```text
validate each observation and reject duplicate source IDs
validate one scenario per replay and strictly increasing finite decision times
sort pending observations by (arrival_time_s, sample_id)
state = None
for each decision time now:
    release every pending item whose arrival <= now
    for each released item:
        replace state only if its measurement time is newer
        retain a diagnostic reason for a released older measurement
    call warning_policy with state, now and policy only
    save the decision and the selected source ID
```

No future truth lookup appears in this loop. An evaluator later joins decisions to truth. If your M2 trace lacks selected sample ID, add it as diagnostic output rather than inferring it from rounded timestamps.

### Boundary fixtures to implement

Use `unittest.subTest` to make cases readable. Check exact representable neighbours with `math.nextafter` where appropriate; the [Python math documentation](https://docs.python.org/3.14/library/math.html#math.nextafter) defines adjacent representable values, `isfinite` and closeness tools. Assertions may use small absolute numeric tolerances; replay must not introduce a broad epsilon that releases future data early.

| Boundary | Expected behaviour |
| --- | --- |
| Arrival exactly 1.0; decision `nextafter(1.0, -inf)` | Unavailable |
| Arrival exactly 1.0; decision 1.0 | Available |
| Measurement 0, max age 1, decision 1 | Usable at age limit |
| Same reading; decision `nextafter(1.0, +inf)` | Stale |
| First reading dropped | Initial decisions unavailable; no invented zero gap |
| Every reading dropped | All decisions unavailable; still score the episode |
| Arrival beyond horizon | Pending count increases; no early release or horizon extension |
| Older reading arrives after newer | Newer measurement remains selected |
| Same arrival for two different measurement times | Deterministic release order; retain newer measurement |
| Times 0, 0.5, 1.4 | Age uses actual times, never sample count × assumed dt |
| Duplicate ID within one scenario | Reject even if duplicate fields agree |
| Distinct IDs with identical measurement times | Reject in this one-reading-per-source-time contract; do not invent multi-sensor merging |
| Input list not sorted by arrival | Schedule correctly after validation; this is allowed |

Dropout creates gaps in IDs, so do not demand contiguous observation IDs. Validate the original truth's strict ID/time ordering before injection. Measurement times should increase with source IDs in that original sequence; sort-by-arrival input is allowed to have decreasing measurement times. Check source ordering by ID separately from arrival scheduling.

### Reject invalid data deliberately

Test NaN, positive/negative infinity, strings, bools and negative times. Require finite numeric gap/closing values; finite negative values remain meaningful. Reject arrival before measurement, mixed-scenario streams, negative/noninteger IDs, non-finite decision times, repeated/backward decision times and unit/schema mismatches at import. Seeds and counts also reject bools, since Python otherwise treats them as integers.

An empty valid observation list is different from invalid input: replay should return unavailable decisions for the requested grid. A rejected input should fail the case visibly. Do not catch every exception and return an empty result that looks like sensor dropout.

When a comparison uses decimal times, remember that floating-point subtraction can round. Use exact binary-friendly times such as 0, 0.5 and 1 for the closest-neighbour boundary tests. For a 0.6-second arrival trace, compare ages using a small absolute tolerance rather than asserting an exact decimal representation.

Run after implementing the tests:

```powershell
.\.venv\Scripts\python.exe -m unittest -v test_m3_boundaries
```

**Your meaningful attempt:** add a test where an older, alarming observation arrives after a newer, non-alarming one. Write the expected selected ID and warning before running it. If the warning changes merely because the old item arrived last, inspect state replacement rather than adjusting the TTC threshold.

## Block 4 — add stop-and-go without changing the truth contract

The lead-braking family stops once. A second family should exercise a different motion pattern: the lead brakes to zero, remains stopped, then accelerates and cruises again. Keep the ego at a prescribed constant speed for this section. Adding a driver controller or feedback braking would change the experiment's scope.

Use piecewise constant acceleration. Within a phase of local duration u:

`v(u) = v_start + a*u`

`x(u) = x_start + v_start*u + 0.5*a*u²`.

The constant-acceleration equations and splitting changing motion into phases are explained in [OpenStax University Physics §3.4](https://openstax.org/books/university-physics-volume-1/pages/3-4-motion-with-constant-acceleration). The stop/hold/restart schedule below is our independently chosen synthetic fixture.

### A complete hand-checkable schedule

Use ego speed 4 m/s, lead initial speed 4 m/s, braking magnitude 2 m/s², a 2 s stationary hold, restart acceleration 2 m/s² and final lead speed 6 m/s. The horizon is 8 s. Only initial gap differs between the contact and non-contact cases.

| Phase | Interval | Lead motion | Distance accumulated at phase end |
| --- | --- | --- | ---: |
| Brake | 0–2 s | Speed falls 4→0 m/s under −2 m/s² | 4 m |
| Hold | 2–4 s | Speed zero, position fixed | 4 m |
| Restart | 4–7 s | Speed rises 0→6 m/s under +2 m/s² | 13 m |
| Cruise | 7–8 s | Speed 6 m/s | 19 m |

Check those distances without using your implementation: braking takes `4/2=2 s` and covers average speed `(4+0)/2 * 2 = 4 m`. Restart takes `6/2=3 s` and covers `(0+6)/2 * 3 = 9 m`. Cruise adds 6 m. Ego travels `4*8=32 m`.

For arbitrary initial gap d, the lead's travel distance is:

```text
0 <= t <= 2:   4*t - t*t
2 <  t <= 4:   4
4 <  t <= 7:   4 + (t-4)**2
7 <  t <= 8:   13 + 6*(t-7)
```

Add d to obtain its rear-bumper position. Ego front position is `4*t`. This gives the following independent answers:

| t (s) | Lead travel (m) | Ego front (m) | Lead speed (m/s) | Gap for d=15 (m) | Gap for d=18 (m) |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 0 | 0 | 4 | 15 | 18 |
| 1 | 3 | 4 | 2 | 14 | 17 |
| 2 | 4 | 8 | 0 | 11 | 14 |
| 3 | 4 | 12 | 0 | 7 | 10 |
| 4 | 4 | 16 | 0 | 3 | 6 |
| 5 | 5 | 20 | 2 | 0 | 3 |
| 6 | 8 | 24 | 4 | −1 | 2 |
| 7 | 13 | 28 | 6 | 0 | 3 |
| 8 | 19 | 32 | 6 | 2 | 5 |

For d=15, gap stays positive through braking/hold. During restart let `u=t-4`. Gap is `3 - 4*u + u² = (u-1)*(u-3)`. First contact is therefore **5 s**, inside the restart phase. The later equality at 7 s is not another independent collision episode: the prescribed virtual paths have already overlapped. This model does not simulate impact dynamics.

For d=18, restart gap is `6 - 4*u + u² = (u-2)² + 2`. Its minimum is **2 m at 6 s**. Earlier phases have larger gaps and cruise increases gap, so there is no contact anywhere on `[0,8]`; final gap is 5 m. This is stronger evidence than just observing positive saved rows.

### Implement a small new model, not a second sensor format

Use a new `StopGoScenario` in `stop_and_go.py` with proposed fields:

```text
scenario_id, initial_gap_m, ego_speed_mps, lead_speed_mps,
lead_deceleration_mps2, hold_s, lead_acceleration_mps2,
restart_speed_mps, timestep_s, sample_count
```

Give it `family="stop_and_go"` and the same horizon formula `(sample_count-1)*timestep_s`. Braking starts at zero in this bounded family. Use positive deceleration/acceleration magnitudes, nonnegative speeds/hold, finite values and positive timestep/integer sample count. Reject overflow in derived phase times/positions and times outside the evaluation domain you document. Permit signed initial gap as in M1.

Do not pass these new keys into M1's `Scenario` or its strict fixture loader: those support the original constant/braking configuration shape. Your study driver can construct two `StopGoScenario` instances explicitly and export their complete configurations. M4 later makes the release configuration loader dispatch by family.

Implement these functions:

```python
from motion import TruthSample

def stop_go_truth_at(scenario, elapsed_s, sample_id=0):
    """Return M1-compatible TruthSample from continuous piecewise motion."""
    # TASK: validate time/ID; derive stop, restart and cruise times.
    # Evaluate lead distance/speed in the relevant phase.
    # Set ego_x=ego_speed*elapsed_s and lead_x=initial_gap+lead_distance.
    # Return TruthSample with gap=lead_x-ego_x and closing=ego_speed-lead_speed.
    raise NotImplementedError

def sample_stop_go_truth(scenario):
    # TASK: evaluate sample_id*timestep_s, including zero and horizon.
    # Check strict time increase; retain the existing truth column names.
    raise NotImplementedError

def first_stop_go_contact_time(scenario):
    # TASK: find the first continuous gap<=0 inside the inclusive horizon.
    # Use the piecewise root procedure below; never call the TTC policy.
    raise NotImplementedError
```

Compute each phase from its absolute start state. If braking would continue beyond zero speed, stop at zero and freeze position. If restart reaches its target speed, switch to cruise. Do not clip only the reported speed while continuing the wrong position equation. Positions and speeds must be continuous at phase boundaries even though acceleration can jump.

For general validated inputs define stop time `v_lead_initial/deceleration`, restart time `stop_time+hold_s`, and cruise time `restart_time+restart_speed/acceleration`. Lead distance at stop is `v_lead_initial²/(2*deceleration)`; distance at cruise adds `restart_speed²/(2*acceleration)`. Zero initial/target speed creates zero-width phases; skip them without dividing by a speed or producing repeated breakpoints.

### Continuous contact matters more in this family

With sample spacing 4 s and horizon 8 s, the d=15 case saves only gaps `[15,3,2]` at `[0,4,8]`. All are positive, yet contact occurs at 5 s. A test that checks only sign changes between saved rows misses the event entirely.

Divide the continuous horizon at every phase boundary. In each phase, compute local gap:

`g(u) = C + B*u + A*u²`,

where `C=gap(left)`, `B=lead_speed(left)-ego_speed`, and `A=0.5*lead_acceleration` because ego acceleration is zero. The signs are: negative A during braking, zero during hold/cruise and positive during restart.

Implement the root procedure in this order:

1. Initial gap <= 0 returns zero; a zero-length horizon with positive gap returns no event.
2. Form a sorted unique list of zero, in-horizon phase boundaries and horizon.
3. Visit each nonzero-width phase chronologically. If its starting gap is nonpositive, return the phase start.
4. For A=0 solve the linear root when B is nonzero; a constant positive gap has no root.
5. Otherwise solve the quadratic, inspect **both** real roots and accept only roots in that phase's local interval. Reuse/understand M1's stable quadratic method and documented endpoint-rounding convention; do not copy the whole braking solver and forget the positive-acceleration phase.
6. Return the earliest accepted continuous time. Return `None` if none lies in the declared horizon.

A tangency also counts because contact is gap <= 0, not necessarily a sign crossing. With **d=16**, restart gap is `(u-2)²` and first contact is **6 s**; it immediately opens again. Samples at 5 and 7 s both have gap 1 m. Test this explicitly. A shortcut that requires a negative endpoint fails this fixture.

Keep reference answers as literals with their derivation: d=15 event 5/final gap 2; d=18 no event/final gap 5; d=16 event 6. Never populate a reference field by calling the solver being tested.

### Your scenario check block

In `test_m3_scenarios.py`, test the full numeric table, boundary position/speed continuity at 2, 4 and 7 s, no reverse motion, constant ego speed, the two event fixtures, tangency, initial touching/overlap and horizon inclusion. Check event invariance with 1 s, 0.25 s and 4 s sample spacing at the same 8 s horizon. Add a positive-gap horizon just before the event and an inclusive horizon at the event, with numerical tolerance documented.

For a simple readable test, these proposed calls follow the signatures above:

```python
def test_stop_go_contact_reference(self):
    # make_stop_go_fixture is your test helper using the explicit values above.
    case = make_stop_go_fixture(initial_gap_m=15.0)
    self.assertAlmostEqual(first_stop_go_contact_time(case), 5.0, delta=1e-9)
    at_five = stop_go_truth_at(case, 5.0)
    self.assertAlmostEqual(at_five.ego_front_x_m, 20.0, delta=1e-9)
    self.assertAlmostEqual(at_five.lead_rear_x_m, 20.0, delta=1e-9)
```

The expected 20 m comes from separate distance calculations, not from invoking another branch of your own solver. Run:

```powershell
.\.venv\Scripts\python.exe -m unittest -v test_m3_scenarios
```

**Your meaningful attempt:** change the initial gap from 18 to 17 m, leaving the complete schedule fixed. Predict minimum gap, its time and final gap before running. Expected check after your attempt: minimum 1 m at 6 s; final gap 4 m; no contact on this horizon. Explain why changing sample spacing cannot change that continuous event conclusion.

## Block 5 — score boundaries independently and align errors correctly

Reference events belong to the clean continuous trajectory. Warning flags belong to available observations. Keeping these independent allows an honest result in which clean readings still produce a false warning or faulty readings produce no warning.

### Freeze the matching rule before measuring faults

Keep M2's scoring contract. Choose positive pre-event lookback W and minimum useful lead L, with `0 < L <= W`. For contact time te:

- Find the earliest active warning decision within `[max(0,te-W), te]`, including contact time itself.
- If there is no such decision, outcome is `missed`; matched time/lead are null.
- If there is a match, its lead is `te-warning_time`. Outcome is `useful` when lead is at least L; otherwise it is `late`.
- A warning exactly at contact is `late` with zero lead, not useful and not missed. A warning strictly after contact cannot rescue a miss.
- Earlier warnings outside the matching window are diagnostic; multiple true decision rows do not create multiple matched contacts.
- For a no-contact episode, any active warning within `[0,horizon]` makes one `false_warning` episode; otherwise it is `clear_negative`.

Report the exclusive useful/late/missed counts and, separately, `(late+missed)/positive` as the fraction **without a useful warning**. Do not call that derived quantity the M2 miss rate: the M2 miss rate is `missed/positive`. This distinction prevents a low miss rate from concealing late warnings without changing the predecessor's metric definition.

M2 scores active decision flags, while counting warning activations separately as False→True transitions. Preserve that rule rather than matching only onsets. Initial contact remains positive: a true decision at zero is late/zero lead, and no match at zero is missed. Show initial-contact count as a diagnostic so its lack of pre-event opportunity is visible. Contact exactly at a positive horizon also remains positive.

### A metric answer you can calculate without running replay

Use contact te=10 s, horizon 12 s, W=4 s and L=1 s. Useful warning interval is `[6,9]`; late interval is `(9,10]`.

| Episode | Reference | Active warning times (s) | Expected outcome |
| --- | --- | --- | --- |
| A | Contact at 10 | 5, 6, 8 | Useful; earliest matched warning 6; lead 4; early warning 5 recorded |
| B | Contact at 10 | 9.5 | Late; matched lead 0.5; no useful warning |
| C | Contact at 10 | none | Missed; no matched warning |
| D | No contact through 12 | 2, 2.5, 4 | One false-warning episode |
| E | No contact through 12 | none | No false-warning episode |

Expected aggregate: **3 positives, 2 negatives; 1 useful, 1 late, 1 missed; miss rate 1/3; without-useful-warning fraction 2/3; false-warning-episode rate 1/2**. Useful matched leads are `[4]`; the late matched lead is `[0.5]`; one case has no matched lead. Do not publish an attractive lead-time average by itself while hiding late and missed cases.

Add exact-boundary tests: 6 and 9 are useful; the float immediately before 6 is early; immediately after 9 is late; 10 is late with zero lead; immediately after 10 cannot match. Test a warning at negative-episode horizon 12, an empty positive subset, an empty negative subset, and invalid W/L/event/horizon inputs. Rates with denominator zero are `None`/JSON null with numerator/denominator visible, not zero percent.

Reuse M2's `score_case` result fields rather than one ambiguous success flag:

```text
outcome, reference_contact_time_s, horizon_s,
first_matched_warning_time_s, matched_lead_s, first_warning_time_s,
warning_activation_count, early_warning_decision_count,
post_contact_warning_decision_count
```

Derive `without_useful_warning` from a positive outcome in `{"late", "missed"}` for reporting if helpful; preserve the canonical `outcome`. Test aggregation with literal per-episode results as well as testing the scorer directly. Verify `useful+late+missed == successfully_scored_positive_count`.

### Distinguish sensor error from current-time error

A reading measured at 2 s with clean gap 20 m arrives at 4 s. The current clean gap at 4 s is 10 m. With no measurement noise:

- Measurement-time sensor error is `20-20=0 m`.
- If replay holds that raw reading as its current estimate, current-time gap error is `20-10=+10 m`.
- Its age is 2 s.

Neither error is wrong: they answer different questions. Name and align them correctly. Compare sensor error to truth at **measurement time**. Compare a decision-time estimate to truth at **decision time**, and report the estimate's age/availability policy. Do not call the first number current tracking error, or subtract current truth and claim it measures additive sensor noise alone.

For the stop-and-go family, use the continuous model to evaluate off-grid truth for offline alignment. Never feed that truth callback to `warning_policy.py`.

Use a small independent error fixture: errors `[-2,0,2]` metres give MAE `4/3` m and RMSE `sqrt(8/3)` m, approximately 1.632993 m. If only those 3 estimates are eligible across 5 pre-contact decision ticks, report count 3/5 and the reasons for the other two ticks. With no eligible estimates, error metrics are null/count zero; unavailable data is not a perfect estimate.

Choose and record one eligibility rule for published current-time errors, such as fresh arrived estimates only. For positive cases use meaningful pre-contact decision times; virtual post-contact paths are diagnostic and do not become physical tracking evidence. For negative cases the inclusive horizon is eligible. Keep excluded stale/unavailable counts visible so a method cannot appear better by producing almost nothing.

**Your task:** add the five-episode table and the error fixture to `test_m3_boundaries.py`. Explain the denominator difference between missed events and false-warning episodes, and the numerator difference between missed and without-useful-warning rates. Predict what happens to the matched-lead metric if every positive case is missed: null with zero matched count, not an average of zero seconds.

## Block 6 — reproduce a failure caused by latency

This regression is intentionally simple enough to predict fully. It is a diagnostic constant-speed fixture, not a third required scenario family or a replacement for lead-braking/stop-and-go.

Initial gap is 30 m; ego speed 10 m/s; lead speed 5 m/s. Horizon is 6 s. Clean geometry independently gives `30+5*t=10*t`, so first contact is **6 s**. Source observations occur at integer seconds 0 through 6; decisions occur every 0.5 s on `[0,6]`.

Keep all these policy parameters fixed across the contrast:

```text
TTC warning threshold: 2.0 s, inclusive
maximum observation age: 3.0 s, inclusive
pre-event lookback W: 3.0 s
minimum useful lead L: 1.0 s
noise: zero; dropout: zero; latency jitter: zero
```

The large age limit is deliberate for this diagnostic: it isolates delay from stale rejection. It is not a recommended operational value. The useful window is `[3,5]` and late interval `(5,6]`. This fixture uses a fixed half-second decision grid, an explicitly documented diagnostic override of M2's default sample-times/arrival-times union rule. All fixed arrivals in these arms lie on that grid, so no delivery is rounded to a later tick.

For clean source measurements the gap sequence is `[30,25,20,15,10,5,0]` m and TTC sequence is `[6,5,4,3,2,1,0]` s. The first alarming source sample is ID 4 at measurement time 4 s. Latency moves its arrival, not its stored value or its measurement time.

| Fixed latency | First active warning | Lead time | Expected scoring |
| ---: | ---: | ---: | --- |
| 0 s | 4 s | 2 s | Useful |
| 1 s | 5 s | 1 s | Useful exactly at the minimum-lead boundary |
| 1.5 s | 5.5 s | 0.5 s | Late; no useful warning |
| 2 s | 6 s | 0 s | Late exactly at contact; no useful warning |
| 2.5 s | None within horizon | null | Missed; first alarming sample arrives at 6.5 s, after horizon |

At delay 2 s, decision time 5.5 s still uses source ID 3, measured at 3 s, gap 15 m and TTC 3 s. Its age is 2.5 s, but it does not warn. At 6 s source ID 4 arrives and warns; that cannot retroactively become a warning at 4 s. Source IDs 5 and 6 remain pending beyond the horizon.

At delay 2.5 s, decision time 6 s still uses ID 3, age exactly 3 s and TTC 3 s: usable but clear. IDs 4, 5 and 6 remain pending. No active warning occurs within the horizon, so M2 scores a miss. Do not drop pending rows from provenance or flush them early.

This is a policy limitation under the chosen sampling, threshold and delay: the program can behave exactly as specified and still miss a useful warning. Do not repair this regression by reading future truth, shifting the contact event, changing parameters in just one arm or removing the failed case.

### Implement the regression around your M2 functions

In `test_m3_regression.py`, write `run_timing_fixture(latency_s)` as a test helper. It must construct the same truth once per fixture definition, inject fixed latency through your tested injector, replay the half-second grid, score against literal contact 6 s, and return the decisions/result. It must not hard-code the table's outcomes into the implementation.

Use these assertions as a guide after mapping to your M2 result names:

```python
def test_delay_can_remove_useful_lead(self):
    expected = [
        (0.0, 4.0, "useful"),
        (1.0, 5.0, "useful"),
        (1.5, 5.5, "late"),
        (2.0, 6.0, "late"),
        (2.5, None, "missed"),
    ]
    for delay, first_warning, outcome in expected:
        with self.subTest(delay_s=delay):
            trace, score = run_timing_fixture(delay)
            active = [row.decision_time_s for row in trace if row.is_warning]
            self.assertEqual(min(active, default=None), first_warning)
            self.assertEqual(score["outcome"], outcome)
            self.assertEqual(score["reference_contact_time_s"], 6.0)
```

Also assert equal clean-truth snapshots/reference events across all arms, zero measurement-time errors, correct selected sample/age at 5.5 s and 6 s, null matched lead in the 2.5 s case, and no use before arrival. Retain the failing behaviour as the **expected model outcome**, with tests passing when it is reproduced honestly. Add a separate test for an actual replay bug if your implementation exposes one; do not confuse a red unit test with an experimentally poor warning outcome.

Run after implementing the helper/test:

```powershell
.\.venv\Scripts\python.exe -m unittest -v test_m3_regression
.\.venv\Scripts\python.exe -m unittest -v
```

Expected outcomes are the table above; these commands have not been run as part of lesson authoring. If they disagree, trace selected source IDs and times before changing any warning/scoring parameter.

**Your meaningful attempt:** choose delay 0.5 s on the same grids and predict first warning and useful lead. Expected check after your prediction: first warning 4.5 s, useful lead 1.5 s. Explain why the underlying contact remains 6 s. Then increase only the observation-age limit in the 2.5 s delay case; explain why accepting an old non-alarming reading does not deliver the alarming ID 4 before the horizon.

## Block 7 — connect the section and inspect the evidence

Implement `m3_study.py` as a small driver around your completed modules. This is an M3 study command; M4 later provides a full configurable experiment/release command. Do not build a dashboard or add an estimator here.

### A bounded diagnostic set

Reuse M1's independent lead-braking contact/non-contact fixtures and your two stop-and-go cases. For each, run a clean condition and low/strong settings for each single fault. These are initial **experimental severity choices**, not measured sensor specifications:

| Condition | Gap sigma (m) | Closing sigma (m/s) | Base delay (s) | Additional uniform jitter range (s) | Drop probability |
| --- | ---: | ---: | ---: | --- | ---: |
| clean | 0 | 0 | 0 | 0 | 0 |
| noise_low | 0.2 | 0.1 | 0 | 0 | 0 |
| noise_strong | 1.0 | 0.5 | 0 | 0 | 0 |
| latency_low | 0 | 0 | 0.25 | [0,0.1) | 0 |
| latency_strong | 0 | 0 | 0.5 | [0,1.5) | 0 |
| dropout_low | 0 | 0 | 0 | 0 | 0.1 |
| dropout_strong | 0 | 0 | 0 | 0 | 0.4 |

Freeze your M2 warning/scoring policy across these conditions; record it in every result. The regression block has an explicitly separate diagnostic policy. Do not compare those different policies as though only latency changed.

One documented seed bundle is `(gap=101, closing=102, latency=103, dropout=104)`. Use another, such as `(201,202,203,204)`, for repeatability/isolation exercises. A shared bundle across cases deliberately reuses error patterns by source index; it does not create independent experimental replicates. Save a per-case seed manifest before running. Changing timestep changes the source count and interpretation of per-sample dropout; hold it fixed within each comparison. If M4 exposes a single case seed, map it deterministically to these stream fields at one documented adapter boundary; do not silently replace four streams with one global RNG.

The four cases × seven conditions give 28 diagnostic case-condition rows for the first bundle. That count is an enumeration target for your later driver, **not an observed result**. Run the second bundle on representative fault fixtures as a check without claiming statistical significance. M4 will formalize the release matrix, failure handling and complete reporting; C1 later separates tuning from final evaluation cases/seeds.

### Driver responsibilities in execution order

1. Validate settings and output destinations before writing. Keep outputs within the chosen project output directory; avoid overwriting sources, input fixtures or the original snapshot.
2. Construct/load all four configurations and independent references. For each case, generate clean truth once and verify event/final-gap references before fault injection.
3. Freeze a serializable truth snapshot and hash. Keep scenario/configuration and reference event fixed across its seven conditions.
4. Initialize fresh private RNGs for each case-condition; inject one fault mode; retain every source row in the offline audit.
5. Reuse M2's declared clock rule: the sorted union of source schedule times, zero/horizon and arrivals within the horizon. Keep that rule fixed across conditions, preserve base ticks even during dropout, and use observations only in warning decisions. Variable jitter adds different arrival ticks, so report decision counts and label current-error averages as decision weighted. If you choose a fixed-grid diagnostic instead, record that explicit override and use it in every compared arm; never add the true contact time to a decision clock.
6. Evaluate using independent event/horizon and the frozen scoring policy. Calculate aligned errors/counts under the declared eligibility rule.
7. Save observations, audit, decisions, full per-case results and a readable trace of the latency regression. Include every diagnostic row, even when the outcome is a miss.
8. Mark completed, failed and partial execution distinctly. An experimentally missed warning can be a technically complete run. An exception during a case is a failed execution, not a sensor dropout or a zero-valued result.
9. Export a summary with the full declared 28-row diagnostic set plus separate fixed-latency regression results. If a run fails, retain its error/status and do not call the set complete. Exit nonzero on execution failure.

Implemented local layout (supersedes the earlier authoring suggestion):

```text
outputs/m3-study/run-a/
  manifest.json
  configuration.json
  study-summary.json
  cases.csv
  report.html
  truth/<scenario_id>/{truth.csv,configuration.json,reference.json}
  cases/case-001/...case-028/
    observations.csv
    fault-audit.csv
    decisions.csv
    result.json
    timeline.png  # Selected cases only, or all with --all-plots.
  cases/regression-001/...regression-005/
    observations.csv
    fault-audit.csv
    decisions.csv
    result.json
    timeline.png  # Default clean and 2.5-second arms.
```

The brace notation above describes files; it is not a literal Windows filename. Save UTF-8 CSV/JSON with unrounded numeric values, explicit schema/version and `allow_nan=False` for JSON. Use null for absent TTC/metrics, and explicit status/reason fields. Preserve full settings, runtime versions and draw-order version; a seed alone is insufficient provenance.

Decisions should expose at least decision time, selected sample ID/measurement time, age, TTC, warning flag and reason. Add arrival time or an arrival trace so availability can be checked. Reference data and fault-audit values belong in separate offline artifacts, never in the warning function's signature.

### Plots should explain an observed change

Reuse Matplotlib from M1 after you have implemented the driver. Make one plot with clean gap versus measurement time, noisy gap samples located at their measurement times, zero gap and independent contact/horizon markers. For latency, a timeline showing measurement → arrival → decision is clearer than plotting every old value at the wrong time.

The regression figure can use three shared-time panels: clean gap/contact, selected reading age/availability, and warning flags for each fixed delay. Mark useful/late windows explicitly. Show unavailable intervals as gaps/status, not zero-valued measurements. Shade virtual post-contact trajectories as diagnostic. Label seconds, metres and m/s where used; do not crop away a negative gap or failed condition to make a result look cleaner.

### Commands you run after implementing the driver

The implemented driver supports these reproduction commands. Use fresh folder names because existing destinations are rejected. Actual accepted `run-a`/`run-b` outputs are recorded above; the example folder names below are proposed new runs:

```powershell
.\.venv\Scripts\python.exe -m unittest -v test_m3_faults test_m3_injection test_m3_scenarios test_m3_boundaries test_m3_regression test_m3_study
.\.venv\Scripts\python.exe -m unittest -v
.\.venv\Scripts\python.exe .\m3_study.py --output-dir .\outputs\m3-study\example-a
.\.venv\Scripts\python.exe .\m3_study.py --output-dir .\outputs\m3-study\example-b
Get-Content -LiteralPath .\outputs\m3-study\example-a\study-summary.json
Get-Content -LiteralPath .\outputs\m3-study\example-a\cases\regression-005\decisions.csv
```

Expected later checks:

- Both test commands report `OK` with your real test count; every implemented scaffold is completed.
- The summary has all 28 diagnostic rows with explicit execution statuses; no warning success rate is promised.
- The fixed-latency regression reproduces first warning times 4, 5, 5.5 and 6 s for delays 0/1/1.5/2 s, and no warning within the horizon for delay 2.5 s.
- Stop-and-go references are event 5/final gap 2 for contact and no event/minimum gap 2/final gap 5 for non-contact.
- Truth/config/reference hashes match across conditions for each scenario. Stable data/audit/decision/result files match between repeated runs under the same settings/runtime. If metadata includes output paths or wall-clock timestamps, compare the stable content separately and document excluded fields.
- Every plotted warning can be traced to an arrived retained source ID. Dropped and pending counts are distinct; stale ticks remain visible.

For a concrete repeated-data check after you create the suggested layout:

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath .\outputs\m3-study\run-a\timing_regression\truth.csv
Get-FileHash -Algorithm SHA256 -LiteralPath .\outputs\m3-study\run-b\timing_regression\truth.csv
Get-FileHash -Algorithm SHA256 -LiteralPath .\outputs\m3-study\run-a\timing_regression\trace.csv
Get-FileHash -Algorithm SHA256 -LiteralPath .\outputs\m3-study\run-b\timing_regression\trace.csv
```

Matching hashes verify those bytes, not broad model validity, learning mastery or determinism on every future Python version. Also inspect the JSON/CSV and open the plots yourself.

## Debugging guide

| Symptom | Inspect first | Why it matters |
| --- | --- | --- |
| Same noise repeats at every sample | Where RNGs are initialized | Seeding inside the loop restarts a sequence |
| Dropout changes later per-source noise | Draw order and skipped draws | Drop decisions must not advance unrelated streams differently |
| Clean truth differs across conditions | Mutation and scenario creation | Fault injection belongs after fixed truth generation |
| Latency improves a warning unexpectedly | Arrival gate and selected source ID | A future reading may be leaking into replay; improvement itself is not proof of a bug |
| Age resets to zero when an old reading arrives | Measurement versus arrival time | Arrival is not measurement freshness |
| Gap jumps to zero on a dropped tick | Missing-data representation | Missing cannot mean contact |
| Late older sample replaces newer state | State-selection rule | Arrival ordering alone does not establish freshness |
| Stop-and-go position drifts while stopped | Phase position equation | Clipping speed without freezing distance is inconsistent |
| Coarse samples report no contact | Continuous phase solver | Contact can occur and clear between positive sampled endpoints |
| Two contacts counted after overlap | First-event episode boundary | Prescribed post-contact geometry is virtual |
| False-warning rate denominator is all episodes | Negative-episode subset | The rate is defined on no-contact episodes |
| High lead-time mean with many misses | Per-case outcomes/matched count | Successful cases alone can hide failure |
| Zero error when all readings are missing | Null/count handling | No estimate is not a perfect estimate |
| A failed case disappears from the summary | Driver exception/status handling | Execution failures must remain visible |

When debugging, keep the failing inputs/settings fixed, inspect one short trace, identify the violated rule, add an independent expected check, and then change the smallest relevant function. Re-run the focused tests followed by the whole suite. Do not keep running more seeds until an inconvenient failure disappears.

## Completion and handoff to M4

Mark **lesson ready** separately from these later implementation checks. Your M3 implementation is technically ready to hand off when:

- All three faults work separately at clean/low/strong settings with saved units, configuration and independent seeds.
- The same clean truth/configuration/reference event is used across fault conditions, and repeatability/isolation tests pass.
- Both required families have independent contact/non-contact references; stop/hold/restart and continuous contact/tangency are checked.
- Arrival, ordering, unavailable/stale data, variable intervals, duplicates, invalid values and TTC/metric boundaries have meaningful tests.
- The fixed-latency failure is reproduced with saved trace/plot and preserved as an expected-outcome regression.
- Every run/result is reported honestly, with exclusive useful/late/missed outcomes, the separate without-useful-warning rate, false-warning denominators, aligned errors and unavailable/stale counts.
- Your focused/full test commands and study driver have actual recorded results. No generated expected table is substituted for an observed run.

For learning review, prepare three short explanations and one small code change: trace a delayed reading; derive one stop-and-go reference; explain the metric denominators; and implement a changed-gap or ordering test with your prediction. These tasks can be completed without posting after every step. Assistant-written prose and tests alone do not demonstrate your understanding.

Your M4 handoff should identify the actual function names/schema versions, policy values, truth references, test commands/results, stable output location, the latency failure, and one unresolved limitation. M4 then formalizes the full experiment matrix, release CLI/report, clean-environment reproduction and CI configuration. C1 later chooses a comparison from measured evidence; it must use the same causal streams/policies and separate development from evaluation cases.

Keep Git staging, commits, remotes, publication and remote CI under your control. This lesson neither performs those actions nor claims an actual remote run. CARLA remains optional later work.

**Current checkpoint,1 November2026:** all five M3 technical blocks are accepted locally, with131 passing tests and two complete33-case studies whose artifacts/plots are reviewed. Block4 commit419c2e2 is observed. Final selective learner commit/push/main merge remains next. Learner interpretation/independent transfer, clean-environment reproduction and remote CI are separate from this local acceptance.
