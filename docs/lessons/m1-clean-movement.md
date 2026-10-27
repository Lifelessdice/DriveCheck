# M1 — Clean movement: a complete study block

**Status: lesson ready; learner M1 completion pending.** I work in the original project files. At my request, the active source was restored to the recorded pre-assistant implementation state: the original gap function, partial sampler and manual table in `motion.py`, and original known-answer test in `test_motion.py`. The partial sampler still has the `elasped_s`/`elapsed_s` bug for me to fix. The assistant-generated complete M1 code/tests/configuration/outputs were preserved privately under `.private/assistant-m1-reference/2026-10-27/`; they are not active project features or evidence of my understanding. My reviewed work remains the original calculation/test, guided five-row table and first CSV save/read-back.

This lesson is the route I follow myself. I can work through it in several sittings, continue without replying between small steps and ask for review when useful. Code below is teaching material for my deliberate edits to the original files. Lesson preparation did not run these learner exercises or implement their code.

## The outcome and how to work

By the end I should be able to construct and explain a clean longitudinal trajectory, check a braking event independently, distinguish continuous contact from a sampled crossing, save inspectable data/configuration and interpret a labelled plot. This milestone does not include sensors, warnings or fault injection.

Use the original files and grow the project in place:

| Path | Purpose |
| --- | --- |
| `E:\DriveCheck\motion.py` | Existing calculation/sampler; later add clean trajectory records and functions |
| `E:\DriveCheck\test_motion.py` | Keep the original test and add my sampling/model/event tests |
| `E:\DriveCheck\scenarios.py` | Later learner-created module for independently specified cases/references |
| `E:\DriveCheck\m1.py` | Later learner-created module for export, plot and CLI |
| `E:\DriveCheck\outputs\m1-study\` | Outputs from my own study runs |
| `E:\DriveCheck\docs\m1-study-notes.md` | Optional short calculations, questions and explanation |

Open the existing `motion.py` and `test_motion.py`; do not create another model/test copy. Preserve the original `TestGapAfterSeconds` test and `outputs/constant_speed.csv`. The remaining original project modules are created when this lesson reaches them. Leave the private assistant archive intact. An unused empty practice file may exist from the earlier suggestion; this lesson does not use it or require deleting it. The existing `.venv` and installed dependencies are retained; do not recreate setup.

For each block: predict or calculate first, reconstruct the specified logic, run that block's checks, then compare with the reference only where needed. When using reference code, record that assistance honestly. A good result is code I can explain and change, even if I needed hints; memorising a long implementation is not the goal.

All commands in this lesson are **for me to run**, from PowerShell in `E:\DriveCheck`. Expected outputs are predictions, not new observed learner results. Begin each session with:

```powershell
Set-Location 'E:\DriveCheck'
```

## Block 1 — From one calculation to a sampled trajectory

### Understand what the numbers describe

The ego is the rear vehicle. The lead is ahead. Both move forward along positive x. Put the ego front bumper at x = 0 initially and the lead rear bumper at x = 30 m. This measures the actual clear bumper gap; it is not an unexplained distance between vehicle centres.

At constant speed, distance travelled is speed multiplied by elapsed time. At 2 s, ego speed 20 m/s gives 40 m and lead speed 15 m/s gives 30 m. Therefore:

`gap = initial gap + lead travel - ego travel = 30 + 30 - 40 = 20 m`.

The closing speed is `ego speed - lead speed = 5 m/s`, positive when the gap shrinks. The general equation is:

`gap(t) = d0 - (vE - vL)*t`.

The units check is `m - (m/s)*s = m`. Kilometres/hour would have to be explicitly divided by 3.6 before entering this model. Nothing here converts units automatically.

**Do now:** calculate the 3 s gap from the two separate travel distances. Then predict what happens if both speeds are 20 m/s, and if lead speed is 25 m/s. Check answers after your attempt: 15 m; a constant 30 m gap; a gap that grows by 5 m every second.

### Understand sample index versus time

A sample ID labels a saved row; it is not necessarily a time in seconds. With timestep Δt, row i occurs at `t_i = i*Δt`. IDs start at zero so the initial condition is saved.

| Sample ID | Time with Δt = 1 s | Time with Δt = 0.5 s |
| ---: | ---: | ---: |
| 0 | 0 | 0 |
| 1 | 1 | 0.5 |
| 2 | 2 | 1 |
| 3 | 3 | 1.5 |
| 4 | 4 | 2 |

Five samples contain four intervals. The inclusive horizon is `H = (sample_count - 1)*timestep_s`. Halving the timestep while keeping the count fixed shortens the horizon. To keep a 4 s horizon at 0.5 s spacing, use nine samples.

Each row evaluates the same initial conditions at its own absolute elapsed time. Do not feed the previous row's gap back into a function that subtracts motion over the full elapsed time; that would subtract earlier motion again.

### Finish the existing sampler

Open `motion.py`. Your elementary gap calculation and the sampling loop are already there; do not replace them with a new scaffold. In `sample_constant_speed`, the assigned variable is `elasped_s`, that spelling is passed to the gap function, but the dictionary refers to `elapsed_s`.

**First change:** use `elapsed_s` consistently in all three places. Read the loop as three actions: calculate the current time, evaluate the original initial state at that time, and append the row. The time calculation is `sample_id * timestep_s`; the saved `time_s` must contain that same value.

The original script's manual print loop does not call this sampler, and the original test checks only `gap_after_seconds`. Therefore those old commands can succeed while this sampler is broken. The new tests below are what exercise the sampler.

Add `import math` at the top. This supplied helper handles the repetitive number checks so the first exercise can focus on sampling:

```python
def require_finite(name, value, *, minimum=None, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite:
        raise ValueError(f"{name} must be finite")
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    if positive and value <= 0:
        raise ValueError(f"{name} must be positive")
```

`True` counts as an integer in Python, which is why the boolean check comes first. A NaN is an unavailable/invalid number here, not a valid gap or speed.

Next, strengthen only the existing sampler's input-check section. Add calls to the supplied helper and replace the old minimal count/timestep checks with this validation block; keep the corrected sampling loop below it:

```python
require_finite("initial_gap_m", initial_gap_m)
require_finite("ego_speed_mps", ego_speed_mps, minimum=0)
require_finite("lead_speed_mps", lead_speed_mps, minimum=0)
require_finite("timestep_s", timestep_s, positive=True)
if isinstance(sample_count, bool) or not isinstance(sample_count, int) or sample_count < 1:
    raise ValueError("sample_count must be an integer >= 1")
```

Indent that validation block inside `sample_constant_speed`. Add the helper above the sampler, and keep imports at the top. Do not create a second definition with the same name. Calculate each time directly from its ID rather than repeatedly adding the timestep.

### Write tests with independently specified answers

Open the existing `test_motion.py`. Keep `import unittest` and the original `TestGapAfterSeconds` class unchanged. Extend its import line to `from motion import gap_after_seconds, sample_constant_speed`, then append the following new class below the original class. The historical assistant tests are in the private archive; the active tests here exercise the source I am editing.

```python
class SamplingTests(unittest.TestCase):
    def test_original_five_rows(self):
        rows = sample_constant_speed(30, 20, 15, 1, 5)
        self.assertEqual([r["sample_id"] for r in rows], [0, 1, 2, 3, 4])
        self.assertEqual([r["time_s"] for r in rows], [0, 1, 2, 3, 4])
        self.assertEqual([r["gap_m"] for r in rows], [30, 25, 20, 15, 10])

    def test_half_step_with_five_samples(self):
        rows = sample_constant_speed(30, 20, 15, 0.5, 5)
        self.assertEqual([r["time_s"] for r in rows], [0, 0.5, 1, 1.5, 2])
        self.assertEqual([r["gap_m"] for r in rows], [30, 27.5, 25, 22.5, 20])

    def test_one_sample_is_only_the_initial_state(self):
        self.assertEqual(sample_constant_speed(30, 20, 15, 1, 1),
                         [{"sample_id": 0, "time_s": 0, "gap_m": 30}])

    def test_invalid_grid(self):
        for step, count in [(0, 5), (-1, 5), (float("nan"), 5), (1, 0), (1, 2.5), (1, True)]:
            with self.subTest(step=step, count=count), self.assertRaises(ValueError):
                sample_constant_speed(30, 20, 15, step, count)
```

Run after completing your sampler:

```powershell
.\.venv\Scripts\python.exe -m unittest -v test_motion
```

**Expected after my changes:** five tests pass: the original one plus the four new supplied sampling tests. A `NameError` before the spelling fix or a failed validation test before strengthening the guards is useful evidence of the missing behaviour. The lesson does not claim these tests have been run by me yet.

Add my own sixth test inside `SamplingTests`: use 0.5 s timesteps with nine samples and assert row count 9, final time 4 s and final gap 10 m. Rerun the same command; six tests should pass. After that I can add equal-speed/opening-gap tests if useful. Do not compute expected gaps by calling the function being tested.

### A small real-source improvement

Once those checks pass, optionally update only the existing `if __name__ == "__main__":` block in `motion.py` so it obtains rows from `sample_constant_speed` instead of duplicating the sampling loop. Keep the same initial settings and header. The final loop can be:

```python
for row in sample_constant_speed(
    initial_gap_m, ego_speed_mps, lead_speed_mps, timestep_s, 5
):
    print(f"{row['time_s']:.1f},{row['gap_m']:.1f}")
```

Indent that loop inside the existing main guard. This is a learner edit, not a change made during lesson preparation. Run `.\.venv\Scripts\python.exe .\motion.py`; expected output remains the header and the original five rows. This makes the console example exercise the same reusable sampler as the tests. Do not overwrite the preserved first CSV snapshot to prove that the output matches.

**Block result:** I can explain why five rows span four seconds and show my own sampler being tested. I do not need to send a reply before continuing.

## Block 2 — Define clean truth and reconstruct braking

### The data contract

The shared clean schema is `drivecheck.truth.v1`. Use these names consistently so later observation/replay lessons have an unambiguous starting point:

| Field | Meaning | Unit |
| --- | --- | --- |
| `scenario_id` | Which configured trajectory this row belongs to | Text |
| `sample_id` | Contiguous row ID beginning at zero | Integer |
| `time_s` | Absolute elapsed simulation time | s |
| `ego_front_x_m` | Ego front-bumper position | m |
| `lead_rear_x_m` | Lead rear-bumper position | m |
| `ego_speed_mps` | Nonnegative forward ego speed | m/s |
| `lead_speed_mps` | Nonnegative forward lead speed | m/s |
| `gap_m` | Lead rear minus ego front position | m |
| `closing_speed_mps` | Ego speed minus lead speed | m/s |

Positive gap means separation, zero means touching and negative gap means overlap of the prescribed paths. Do not clip the gap to zero. After first contact these are virtual paths, not a crash simulation. Initial touching/overlap counts as a reference event at time zero even if the vehicles subsequently separate.

There is no sensor timestamp/arrival time yet. `time_s` belongs to **truth**. M2 will define separate observations with measurement and availability times. Keeping those concepts separate now prevents future truth from accidentally becoming a warning input.

Configuration must preserve initial gap/speeds, timestep/count, brake delay, positive deceleration magnitude, horizon, schema/model version, units, origin/sign conventions and source provenance. M1 has no random process, so record a null seed with the reason instead of inventing one. A configuration sidecar is part of the dataset, not an optional note.

### Use records without hiding the physics

A dataclass is a named collection of fields. `frozen=True` prevents later reassignment, which helps stop scenario configuration being silently changed during a run. Add the following record scaffolding to `motion.py`, below the existing helper/function definitions but **above the existing main guard**. Keep all imports at the top and keep only one definition of each class/function. These classes do not exist in the restored active source yet; I build them as this block proceeds:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    initial_gap_m: float
    ego_speed_mps: float
    lead_speed_mps: float
    timestep_s: float
    sample_count: int
    brake_start_s: float = 0.0
    lead_deceleration_mps2: float = 0.0

    @property
    def horizon_s(self):
        return (self.sample_count - 1) * self.timestep_s

    @property
    def stop_time_s(self):
        if self.lead_deceleration_mps2 == 0:
            return None
        return self.brake_start_s + self.lead_speed_mps / self.lead_deceleration_mps2

    def __post_init__(self):
        # Task: validate the configuration here using the policy below.
        raise NotImplementedError("Validate a Scenario")


@dataclass(frozen=True)
class TruthSample:
    scenario_id: str
    sample_id: int
    time_s: float
    ego_front_x_m: float
    lead_rear_x_m: float
    ego_speed_mps: float
    lead_speed_mps: float
    gap_m: float
    closing_speed_mps: float
```

For `__post_init__`, reuse `require_finite` to check the numeric fields. Speeds, brake delay and deceleration may be zero but not negative. Timestep must be positive. Initial gap may be negative if explicitly representing initial overlap. Require a positive integer count and reject booleans. Check that the resulting horizon and any finite stop time are finite; turn horizon arithmetic overflow into a useful `ValueError`. Use a nonempty lowercase ID containing only letters/digits/underscores/hyphens. Reserve `manifest` and Windows device names such as `con`, `nul`, `com1` and `lpt1` because IDs become filenames. If needed, the archived `.private/assistant-m1-reference/2026-10-27/motion.py` contains one implementation of these software checks. Selective reference use with attribution is fine; do not restore the entire archived module over my current work.

Do not obtain validation by calling the sampler from the configuration: constructing thousands of rows just to check input types is unnecessary.

### Derive the lead's piecewise motion

Let b be brake start time, a be the **positive magnitude** of deceleration, and vL be initial lead speed. During braking the signed acceleration is −a.

Before braking, lead travel is `vL*t`. Braking lasts `vL/a` seconds, so the lead stops at `b + vL/a`. After stopping its position must remain fixed.

For a > 0 and t > b, use:

`u = min(t-b, vL/a)`

`lead travel = vL*b + vL*u - 0.5*a*u²`

`lead speed = max(0, vL-a*u)`.

The ego stays at its configured constant speed: `ego front x = vE*t`. Add the initial gap to lead travel to obtain the lead rear position. Then subtract positions for gap and subtract speeds for closing speed.

If a = 0, use the constant-speed branch; do not divide by zero. If the initial lead speed is zero, it remains stationary. The position and speed should be continuous at both brake start and stop. Acceleration changes abruptly in this simplified model.

These equations are the constant-acceleration model described in [OpenStax University Physics §3.4](https://openstax.org/books/university-physics-volume-1/pages/3-4-motion-with-constant-acceleration). The bumper origin, stop-at-zero rule and post-contact continuation are our experiment conventions.

### Worked contact trajectory: calculate before implementing

Use initial gap 30 m, ego speed 20 m/s, lead speed 15 m/s, brake delay 1 s and deceleration 5 m/s². At 1 s the ego front is at 20 m and lead rear at `30+15=45 m`, leaving 25 m. Braking lasts `15/5=3 s`; the stop time is 4 s.

At 2 s, the lead has moved 15 m before braking plus `15*1-0.5*5*1²=12.5 m` while braking. Its rear is at 57.5 m and the ego front at 40 m, giving 17.5 m gap. At stop, lead travel is `15+45-22.5=37.5 m`, so the lead rear freezes at 67.5 m.

| Time (s) | Ego front (m) | Lead rear (m) | Gap (m) | Lead speed (m/s) |
| ---: | ---: | ---: | ---: | ---: |
| 0 | 0 | 30 | 30 | 15 |
| 1 | 20 | 45 | 25 | 15 |
| 2 | 40 | 57.5 | 17.5 | 10 |
| 3 | 60 | 65 | 5 | 5 |
| 4 | 80 | 67.5 | −12.5 | 0 |
| 5 | 100 | 67.5 | −32.5 | 0 |

### Implement state evaluation and sampling

Add `truth_at(scenario, elapsed_s, sample_id=0)` to `motion.py`, above its main guard. Follow this algorithm rather than copying the private reference immediately:

1. Validate elapsed time as finite and nonnegative and sample ID as a nonnegative integer.
2. Compute ego position from its constant speed.
3. If deceleration is zero or time is before/equal to brake start, compute ordinary lead travel and unchanged lead speed.
4. Otherwise compute capped braking duration u, then lead travel and speed from the equations above.
5. Add initial gap to lead travel; compute signed gap and closing speed.
6. Reject non-finite computed positions/gap rather than exporting overflow.
7. Return `TruthSample` with the scenario ID and supplied sample ID.

This evaluator may intentionally be called outside the configured sampling horizon for a diagnostic. The event search in the next block will enforce the horizon.

Add `sample_truth(scenario)`. It should loop over the count, calculate each absolute time, call `truth_at` with that time and ID, and return a list. Reject times that cease to increase due to floating-point representation. Do not round timestamps before calculation. This is the same sampling idea as Block 1 with richer records.

In `test_motion.py`, extend the import from `motion` to include the new `Scenario`, `truth_at` and `sample_truth`. Keep all earlier tests and append:

```python
class BrakingTests(unittest.TestCase):
    def test_known_rows_and_stop(self):
        s = Scenario("braking_contact", 30, 20, 15, 1, 6, 1, 5)
        rows = sample_truth(s)
        self.assertEqual([r.gap_m for r in rows], [30, 25, 17.5, 5, -12.5, -32.5])
        self.assertEqual([r.lead_speed_mps for r in rows], [15, 15, 10, 5, 0, 0])
        for t in [4, 5, 20]:
            row = truth_at(s, t)
            self.assertEqual(row.lead_rear_x_m, 67.5)
            self.assertEqual(row.lead_speed_mps, 0)
```

Your tasks: add one continuity test around 1 s and 4 s; a zero-deceleration case; a stationary ego case; a lead initially at zero; and invalid configuration cases. For continuity, compare positions/speeds at `boundary±1e-8` using `assertAlmostEqual(..., places=6)` rather than exact equality. For the stationary example `(gap=2, ego=0, lead=4, delay=1, deceleration=2)`, expected gaps at 0/1/2/3/5 s are `2,6,9,10,10 m`.

```powershell
.\.venv\Scripts\python.exe -m unittest -v test_motion.SamplingTests test_motion.BrakingTests
```

**Expected:** your earlier sampling tests still pass, and the lead stops without reversing. Explain why clipping speed alone is insufficient if the uncapped position equation continues after stop.

## Block 3 — Independent events, between-sample contact and non-contact

### Calculate exact contact independently

Contact means the bumpers occupy the same longitudinal position. For the worked braking fixture, during its braking phase:

`ego front x = 20t`

`lead rear x = 30+15t-2.5(t-1)²`.

Equate them and expand:

`30+15t-2.5(t²-2t+1)=20t`

`27.5-2.5t²=0`, therefore `t²=11`.

The positive root is **√11 ≈ 3.3166247903554 s**. Check its phase: it is after brake start at 1 s, before stop at 4 s and inside the 5 s horizon. A quadratic root outside the phase where its equation applies must be rejected.

The first nonpositive sampled gap is at 4 s, about 0.6834 s later. Using that row as the event creates sample-rate error. Straight-line interpolation between the 3 s and 4 s gaps also misses the exact value because gap is quadratic during braking. The event should come from the continuous model; saved rows are for inspection.

### Work a non-contact case with an explicit horizon

Use initial gap 40 m, ego speed 10 m/s, lead speed 20 m/s, brake delay 1 s, deceleration 5 m/s² and horizon 8 s. The lead brakes for 4 s and stops at 5 s. Its total travel is `20*1 + 20*4 - 0.5*5*4² = 60 m`. Its stopped rear position is `40+60=100 m`.

At the 8 s horizon, the ego front is at 80 m, so the final gap is 20 m. Gap first grows to 60 m at 3 s, when the speeds match, then decreases. Its minimum over `[0,8]` is 20 m: no contact in this interval. If extended unchanged the ego reaches 100 m at 10 s. Thus **non-contact is a horizon-specific label, not a claim that this configuration can never collide**.

For one-second samples, use nine rows to include 0 through 8 s. Check selected gaps: at 0/1/3/5/8 s they are `40,50,60,50,20 m`.

### Build an analytic event search in manageable parts

Define the event policy before writing code:

- Search the inclusive interval `[0,H]` for the first contact.
- Initial gap <= 0 returns `0.0`, including initial overlap or separating vehicles.
- No event within the horizon returns `None`; JSON will represent it as `null`.
- Continue signed virtual paths after contact for inspection; do not simulate impact response.
- Treat floating-point phase endpoint rounding explicitly, rather than hiding it in a large gap/time epsilon.

**Part A: implement `contact_delay(gap_m, closing_speed_mps, deceleration_mps2)`.** This helper assumes positive starting gap and one phase with constant lead deceleration magnitude a, including a = 0. It solves:

`gap(u) = gap_m - closing_speed_mps*u - 0.5*a*u² = 0`.

If a = 0 and closing speed c > 0, the candidate delay is `gap_m/c`. If a = 0 and c <= 0, there is no candidate in that phase.

If a > 0, define `D = sqrt(c²+2*a*gap_m)`. The positive candidate can be evaluated without cancellation:

| Starting closing speed | Candidate delay |
| --- | --- |
| c >= 0 | `2*gap_m/(c+D)` |
| c < 0 | `(D-c)/a` |

These are equivalent ways to compute the positive quadratic root. The first avoids subtracting almost equal numbers when the closing speed is large and the event time small. A candidate may lie beyond the current phase; this helper alone does not decide whether the event occurs in the configured trajectory.

**Part B: implement `first_contact_time(scenario)`.** Make a sorted unique list of boundaries containing 0, horizon and any brake-start/stop times strictly inside the horizon. For each adjacent pair `(left,right)`:

1. Evaluate the truth at `left`. If its gap is already <= 0, return `left`.
2. The phase is braking only when deceleration > 0 and `brake_start_s <= left < stop_time_s`. Otherwise use a = 0.
3. Pass the starting gap/closing speed and this phase's a to `contact_delay`.
4. Accept a nonnegative candidate only if it lies inside the phase width `right-left`, allowing the small endpoint rounding policy below.
5. Return `left+candidate` for the first accepted event. If none qualifies, return `None`.

Check initial overlap before the loop, including when N = 1 and H = 0. At zero horizon with a positive gap there are no phases to search and no event.

For agreement with the reference numerical convention, use:

```python
tolerance_s = 32 * math.ulp(max(abs(left), abs(right)))
```

An ULP is the spacing of adjacent floating-point values. Accept `candidate <= width+tolerance_s` and clamp accepted slight overshoot to `width`. There is **no one-second floor**: an event at 1e-15 s must not be accepted inside a 1e-18 s horizon just because a tolerance was calculated at 1 s. This rule addresses arithmetic rounding, not sensor uncertainty. Do not use a fixed positive gap tolerance to turn an initially separated vehicle into initial contact.

If you need a different root-solving presentation, inspect `first_contact_time` in the archived `.private/assistant-m1-reference/2026-10-27/motion.py` after your attempt. It uses the general q-form quadratic, whereas the helper above uses the special concave gap equation. Explain their relationship rather than copying one unexplained expression. Implement my chosen helper and event function in the active original `motion.py`, not in a separate model copy.

### Add fixed-answer event tests

Import your own `first_contact_time` into `test_motion.py`. Add a `ContactTests` class and these cases. Literal expected numbers come from calculations, not from calling another copy of your solver:

| Configuration: gap, ego, lead, brake delay, deceleration | Grid/horizon | Expected event |
| --- | --- | --- |
| 30,20,15,1,5 | Δt=1, N=6; H=5 | 3.3166247903554 s |
| Same | Δt=0.5, N=11; H=5 | Same event |
| Same | Δt=2.5, N=3; H=5 | Same event despite no nearby saved row |
| 10,20,15,3,5 | Δt=1, N=6 | 2 s, before braking |
| 15,20,15,3,5 | Δt=1, N=6 | 3 s, exactly brake start |
| 10,10,10,1,5 | Δt=1, N=6 | 3 s, exactly lead stop |
| 20,10,10,1,5 | Δt=1, N=6 | 4 s, after lead stop |
| 40,10,20,1,5 | Δt=1, N=9; H=8 | None |
| Same | Δt=1, N=11; H=10 | 10 s |
| 30,20,15,0,0 | Δt=1, N=6; H=5 | None |
| Same | Δt=1, N=7; H=6 | 6 s, horizon included |
| 0,0,15,1,5 | Δt=1, N=1 | 0 s, initial touching |
| −1,0,15,1,5 | Δt=1, N=1 | 0 s, initial overlap |
| 1e-15,1,0,0,0 | Δt=1e-18, N=2 | None |

Example test shape:

```python
class ContactTests(unittest.TestCase):
    def test_independent_braking_event(self):
        s = Scenario("contact", 30, 20, 15, 1, 6, 1, 5)
        self.assertAlmostEqual(first_contact_time(s), 3.3166247903554, places=10)
        self.assertGreater(truth_at(s, 3).gap_m, 0)
        self.assertLess(truth_at(s, 4).gap_m, 0)

    def test_noncontact_only_within_horizon(self):
        short = Scenario("negative", 40, 10, 20, 1, 9, 1, 5)
        long = Scenario("extended", 40, 10, 20, 1, 11, 1, 5)
        self.assertIsNone(first_contact_time(short))
        self.assertEqual(first_contact_time(long), 10)
```

Implement the remaining table entries yourself, grouping related boundary cases if helpful. Add a one-sample positive-gap case, equal/opening speeds without braking, tiny positive initial gap, a just-outside-horizon event and one invalid numeric input. `assertAlmostEqual` is appropriate for a computed irrational root; `assertIsNone` checks absence. Avoid `assertIsNotNone` as your only assertion: a wrong contact time would still pass.

```powershell
.\.venv\Scripts\python.exe -m unittest -v test_motion
```

**Expected:** all tests you added pass. The count depends on your organisation; the historical assistant-reference count of 35 is not a target or your completion evidence. A test has value because it checks a stated behaviour, not because it increases a total.

## Block 4 — Save CSV/configuration and make the result inspectable

### Choose the three study cases

Create the original project module `scenarios.py` when reaching this block. Add `from motion import Scenario`, then define these independently specified inputs and expected values there. This separates scenario data from motion equations without duplicating the model:

```python
STUDY_CASES = [
    Scenario("constant_speed_original", 30, 20, 15, 1, 5),
    Scenario("lead_braking_contact", 30, 20, 15, 1, 6, 1, 5),
    Scenario("lead_braking_noncontact", 40, 10, 20, 1, 9, 1, 5),
]

# Independently specified expectations; never fill these from the solver.
REFERENCE = {
    "constant_speed_original": {"contact_time_s": None, "final_gap_m": 10.0},
    "lead_braking_contact": {"contact_time_s": 3.3166247903554, "final_gap_m": -32.5},
    "lead_braking_noncontact": {"contact_time_s": None, "final_gap_m": 20.0},
}
```

`Scenario` comes from the original `motion.py`; do not define another class in `scenarios.py`. Keep the independent derivations above alongside the numeric expectations in notes/configuration. JSON fixture input is an optional next refinement: if added, reject duplicate keys/IDs and unknown schemas. A file parsing successfully is not enough to establish a valid experiment.

### Implement one export function

CSV is convenient for rows; JSON is convenient for nested configuration. Create the original project module `m1.py` for the runner/export/plot responsibilities. Add imports for `csv`, `json`, `hashlib`, `math`, `platform`, `Path`, and `asdict`/`fields` from `dataclasses`. Import `TruthSample`, `sample_truth`, `truth_at` and `first_contact_time` from `motion`, and `STUDY_CASES`/`REFERENCE` from `scenarios`. These are proposed learner-created modules, not active implemented features at the lesson's starting point.

Implement `export_case(output_dir, scenario, samples, event, reference)` using these concrete steps:

1. Use the stem `output_dir / scenario.scenario_id` and suffixes `.csv`, `.json`, `.png`.
2. Write the CSV with `encoding="utf-8"` and `newline=""`. Use `csv.DictWriter` with `[f.name for f in fields(TruthSample)]`, call `writeheader()`, then write `asdict(row)` for every row. `newline=""` lets the CSV library manage line endings on Windows.
3. Construct a JSON dictionary with the fields shown below. Preserve reference and computed results separately.
4. Write JSON using `json.dumps(metadata, indent=2, allow_nan=False) + "\n"` and UTF-8. Python `None` becomes JSON `null`.
5. Call your plot function for the `.png` path.
6. Return a compact case summary including row count, horizon, event, final gap and each artifact's SHA-256 digest.

Use this sidecar structure, filling values from the actual scenario/run:

```python
metadata = {
    "schema_version": "drivecheck.truth.v1",
    "configuration": asdict(scenario),
    "horizon_s": scenario.horizon_s,
    "units": {"time": "s", "position_and_gap": "m", "speed": "m/s", "deceleration": "m/s^2"},
    "axis": "+x forward; ego front initially 0; lead rear initially initial_gap_m",
    "contact_policy": "first contact on inclusive horizon; initial gap<=0 gives event 0; virtual signed paths continue; endpoint tolerance=32 ULPs of represented phase endpoint times",
    "truth_only": True,
    "reference": reference,
    "computed": {"first_contact_time_s": event, "final_gap_m": samples[-1].gap_m},
    "provenance": {
        "generator": "DriveCheck M1 built with supplied lesson and acknowledged AI help",
        "python_version": platform.python_version(),
        "seed": None,
        "randomness": "none",
        # Add source/lock hashes and installed package versions below.
    },
}
```

A file digest can be computed as `hashlib.sha256(path.read_bytes()).hexdigest()`. Record hashes of the active `motion.py`, `test_motion.py`, `scenarios.py` and `m1.py` using workspace-relative names. The hash identifies which bytes were used even though Git has not been set up. Record exact installed dependency versions with `importlib.metadata`, including the plotting dependencies. The historical lock/license inventory is in the private archive; there is no restored root lock to hash. Later reproduction work can introduce an explicitly reviewed active lock. Do not copy private directory names into public result provenance or describe the environment solely by an unpinned package name.

Do not round values before writing them. Floating-point values such as `0.7*3` may display as `2.0999999999999996`; that is not evidence that the simulation used a different timestep. Use tolerances for numeric checks and round only human-facing labels.

### Preflight before writing and label a failed run

In `m1.py`, write the coordinator with this proposed interface so it is also easy to test:

```python
def run(output_dir=None, cases=None, references=None, input_paths=()):
    # Default to outputs/m1-study, STUDY_CASES and REFERENCE.
    # A test can supply different study inputs/outputs without editing globals.
    raise NotImplementedError("Coordinate preflight, checks, exports and manifest")
```

When `output_dir is None`, use `Path(__file__).resolve().parent / "outputs" / "m1-study"`; when `cases is None` or `references is None`, use `STUDY_CASES` or `REFERENCE`. Use explicit `is None` checks so an empty supplied list is not silently replaced by the defaults. Reject an empty case list and missing/extra reference IDs rather than claiming an empty success. Return the final manifest dictionary. The no-argument main entry still works, while tests can choose their own output subfolder and independent references.

Keep outputs under the project output tree; do not redirect them to `configs/` or the source directory. `input_paths` is only an optional list of additional paths to protect; it does not load or parse those files. With in-memory study cases it remains empty. Adding a JSON fixture loader is optional here because the study cases already preserve the full configuration in memory and in their exported JSON.

Plan all filenames first, including `manifest.json`. Before creating the folder or writing a manifest:

- Resolve the output folder and every planned destination and require them to remain within the project's `outputs/` tree.
- Require unique scenario IDs/destinations, and avoid protected input/source paths, the first CSV snapshot and the assistant-reference output tree. A symlink can change a resolved path, so check destinations as well as their textual parent.
- If you add input configuration files, explicitly ensure no destination is that input file. Read/validate all inputs before any output write. A manifest named like an input can otherwise destroy the input before loading it.

Then evaluate each case and compare against the fixed reference. None must match None; two finite events should compare within an absolute 1e-9 s, and final gaps within an absolute 1e-9 m. Raise an informative error naming the case on mismatch. A mismatch is a failed check, not permission to replace the expected answer with the current output.

For execution, use a manifest with `status="running"` and a cases list. On success set `complete`; on an exception set `failed`, save the error and any completed case summaries, then re-raise. A `finally` block can write the final manifest. Preflight errors occur before any write. In a reused output folder, stale files can remain after failure, so file existence alone is not success. The authoritative successful set is the complete manifest and its matching artifact hashes.

This is useful engineering practice, not a requirement to reproduce every line of the archived exporter. Sketch the file flow in words first. The private archive's `m1.py` contains one export approach if a specific part needs clarification; its interface can differ from the proposed `run` above. I implement the actual active interface in the original project and adjust tests/documentation honestly.

### Make a labelled local plot

The existing environment already contains Matplotlib and its resolved dependencies. There is no need to install another plotting stack. If imports fail, first check the interpreter rather than rebuilding the environment:

```powershell
.\.venv\Scripts\python.exe -c "import sys, matplotlib; print(sys.executable); print(matplotlib.__version__)"
```

Expected for the preserved environment: the interpreter is under `E:\DriveCheck\.venv\Scripts`, and Matplotlib is 3.11.2. If that package is actually missing, the existing pinned install command is available for **you** to run as a recovery step:

```powershell
.\.venv\Scripts\python.exe -m pip install --only-binary=:all: --require-hashes -r .\.private\assistant-m1-reference\2026-10-27\requirements-m1-lock.txt
```

This is a recovery command for a genuinely missing dependency, not a setup step to repeat. The archived lock is specific to the checked Windows CPython 3.14 wheels. Do not upgrade packages or copy an install command for a different Python/platform without checking compatibility. The historical installed version/license inventory is `.private/assistant-m1-reference/2026-10-27/docs/m1-dependencies.json`; bounded technical sources are also recorded in `docs/research.md`. The retained installed environment is not a claim of learner reproduction or a fresh setup test.

This supplied plotting scaffold keeps unfamiliar Matplotlib details from obscuring the modelling exercise. Add it to the new active `m1.py` and complete the marker tasks. Keep plotting out of `motion.py`, so the model itself remains standard-library-only:

```python
def save_plot(path, scenario, samples, event):
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    # A dense analytic curve and the saved sample grid are different objects.
    times = {scenario.horizon_s * i / 400 for i in range(401)}
    times.update(row.time_s for row in samples)
    if event is not None:
        times.add(event)
    # Task: add brake-start/stop times when they are inside the horizon.
    states = [truth_at(scenario, t) for t in sorted(times)]

    fig, (gap_ax, speed_ax) = plt.subplots(
        2, 1, sharex=True, figsize=(9, 7), layout="constrained"
    )
    fig.suptitle(f"{scenario.scenario_id}: clean kinematic truth")
    gap_ax.plot([r.time_s for r in states], [r.gap_m for r in states], label="Analytic gap")
    gap_ax.scatter([r.time_s for r in samples], [r.gap_m for r in samples], label="Saved samples")
    gap_ax.axhline(0, color="black", linewidth=1, label="Touching: gap=0 m")
    gap_ax.set_ylabel("Bumper gap (m)")

    speed_ax.plot([r.time_s for r in states], [r.ego_speed_mps for r in states], label="Ego")
    speed_ax.plot([r.time_s for r in states], [r.lead_speed_mps for r in states], label="Lead")
    speed_ax.set_ylabel("Forward speed (m/s)")
    speed_ax.set_xlabel("Elapsed simulation time (s)")
    speed_ax.set_ylim(bottom=0)

    for ax in (gap_ax, speed_ax):
        ax.axvline(scenario.horizon_s, color="gray", linestyle=":", label="Horizon")
        if event is not None:
            ax.axvline(event, color="red", linestyle="-.", label=f"Contact {event:.6f} s")
        # Task: mark brake start/stop, when inside the horizon.
        ax.set_xlim(0, max(scenario.horizon_s, 0.1))
        ax.grid(alpha=0.25)
        ax.legend(fontsize=8)

    # Task: title the gap panel with either horizon-limited non-contact or
    # an explicit virtual-overlap/no-impact-physics statement.
    fig.savefig(path, dpi=140, format="png")
    plt.close(fig)
```

Agg writes image files without a GUI. The dense curve is evaluated from your model; the dots are the actual saved rows. Including phase boundaries avoids a line segment that visually smears a brake/stop change. The red event line should cross the zero-gap level between the 3 s and 4 s dots in the contact fixture. Do not set the gap axis minimum to zero: that would hide the negative path continuation.

Official rendering references: [Matplotlib backends](https://matplotlib.org/stable/users/explain/figure/backends.html) and [Figure.savefig](https://matplotlib.org/stable/api/_as_gen/matplotlib.figure.Figure.savefig.html). The lesson uses the already selected dependency; it does not claim that a newer version or a fresh environment was tested.

### Add a main entry and run the complete block

At the bottom of the new `m1.py`, after all definitions, add this proposed CLI. It makes the command below accept an output directory without touching the original console demonstration in `motion.py`:

```python
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Export DriveCheck M1 clean truth")
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()
    run(output_dir=args.output_dir)
```

The guard keeps imports for tests from automatically writing files. Keep the separate original main guard in `motion.py` for its five-row demonstration. In `m1.run`, print a short summary after success with scenario ID, row count, horizon, event and final gap; wording can be my own.

Run the whole check block when your functions are implemented:

```powershell
Set-Location 'E:\DriveCheck'
.\.venv\Scripts\python.exe -m unittest -v
.\.venv\Scripts\python.exe .\motion.py
.\.venv\Scripts\python.exe .\m1.py --output-dir .\outputs\m1-study
Get-Content -LiteralPath .\outputs\m1-study\lead_braking_contact.csv
Get-Content -LiteralPath .\outputs\m1-study\lead_braking_contact.json
Get-Content -LiteralPath .\outputs\m1-study\manifest.json
```

The `m1.py` command becomes available only after I create that active original project module in this block. These are proposed learner-run commands, not checks performed during lesson preparation. If tests fail, debug before treating later exports as accepted; PowerShell may still execute a later command after a failed external command. The private assistant archive is not part of my active implementation or my learner test evidence.

Expected case checks:

| Case | Rows | Horizon | Event | Last gap |
| --- | ---: | ---: | ---: | ---: |
| Original constant speed | 5 | 4 s | None | 10 m |
| Braking contact | 6 | 5 s | 3.3166247903554 s | −32.5 m |
| Braking non-contact | 9 | 8 s | None | 20 m |

Read the files from disk, not just the printed summary. CSV headers should match the contract, IDs should be contiguous and the final timestamp should equal the horizon. JSON should preserve independent and computed answers separately, mark truth-only data and explain null seed/provenance. The manifest should say complete and list all three cases.

Open each PNG from `outputs/m1-study/` in your editor/image viewer. Check labels, units, event time, zero-gap line, brake/stop/horizon markers and visible negative gap. The lead speed must stay at zero after stopping. A PNG opening successfully does not prove its labels or meaning are correct.

Add an integration test class to the active `test_motion.py` after the model/event tests, or create a deliberately named active test module when a split helps readability. Import `run` from the active `m1.py`. Call it with a separate folder under `outputs/m1-study-test/`, read CSV/JSON back, compare fixed expected values and check listed hashes. For example, pass the folder with `run(output_dir=folder)` and assert complete before inspecting files. Do not import the private archive's modules into the active test suite.

Add a deliberate wrong-reference test using a copied reference dictionary passed through `references=...`: change one expected final gap to 99, expect a clear error and a failed manifest. Do not mutate the shared `REFERENCE` in place.

Add a preflight test that rejects a destination outside the allowed project output tree before creating files. It can use a harmless hypothetical path; do not actually write into the private archive. If introducing file-based fixtures, also test input collision with a temporary valid JSON copy at `outputs/m1-study-test/collision/manifest.json`, protect it through `input_paths` and use its containing folder as the proposed output directory. The runner must refuse before its initial manifest write and preserve the input bytes. This path-protection rule can also be unit-tested without a loader. Never test an overwrite against the actual source, snapshot or personal files. Study test outputs can remain in their named ignored folder; no cleanup/delete exercise is required.

## Block 5 — Transfer the idea and decide what is complete

### A changed case to solve yourself

Before running code, use initial gap 24 m, ego speed 18 m/s, lead speed 12 m/s, no braking, timestep 0.7 s and eight samples. Write down:

1. The horizon and all sample times.
2. The continuous contact time from the two bumpers' travelled distances.
3. The first saved row with a nonpositive gap.
4. Whether changing timestep to 0.5 s with eleven samples changes the continuous event.

Then add a test for your prediction and generate a separately named study output. Compare floating-point values with tolerances rather than exact strings.

<details>
<summary>Answer check after my attempt</summary>

The horizon is 4.9 s. Times are `0,0.7,1.4,2.1,2.8,3.5,4.2,4.9 s`; gaps are `24,19.8,15.6,11.4,7.2,3,-1.2,-5.4 m`. The ego gains 6 m each second, so closing the 24 m gap takes 4 s. The first nonpositive saved row is at 4.2 s. A 0.5 s timestep with eleven samples gives a 5 s horizon and the same continuous event at 4 s. It changes the saved grid, not the prescribed motion.

</details>

For one braking transfer, derive and test this case without using the original quadratic answer: gap 20 m, both initial speeds 10 m/s, brake delay 1 s, deceleration 5 m/s², horizon 5 s. The lead stops at 3 s after 20 m travel. Its rear is at 40 m; the ego front is then at 30 m. The remaining 10 m gap closes in one second after stop, giving contact at 4 s. Explain why searching only the braking quadratic would miss this event.

### Debug with the symptom, not by changing the expected answer

| Symptom | First thing to inspect |
| --- | --- |
| `NameError` mentioning elapsed time | Compare assigned and referenced spellings, including the original `elasped_s` mistake |
| Every row has the same value | Does the current sample ID actually enter `elapsed_s`? |
| Gap shrinks too fast over the table | Are you reusing the previous gap with absolute elapsed time and subtracting travel twice? |
| Horizon one step too long | N samples have N−1 intervals; include t=0 |
| Half timestep changes the event | Separate the continuous model/event from the sampling loop; also compare horizons |
| Lead speed or position reverses | Cap braking duration and freeze distance after stop, not just displayed speed |
| Event equals first negative sample | Search the continuous phase equation rather than returning a saved row time |
| Braking root looks right but event is wrong | Check whether the root lies before brake start/after stop/outside horizon |
| Tiny positive gap becomes event zero | Remove a broad gap epsilon; initial contact uses the declared sign rule |
| Tiny horizon accepts a much later event | Scale endpoint tolerance to represented phase times, without a one-second floor |
| Tests pass before the sampler fix | The original test never called the sampler; check the new tests/imports and assert numeric answers |
| `None` in arithmetic/assertions | Check unfinished `pass`, missing return, and correct no-event handling |
| Empty/extra-line CSV on Windows | Check writer header/rows, UTF-8 and `newline=""` |
| JSON rejects a value | Investigate NaN/infinity or a nonserializable object; don't disable finite checks |
| Plot hides overlap | Remove zero minimum from the gap axis; keep speed minimum at zero |
| Import writes/changes output files | Move the runner call under the main guard |
| Import says Matplotlib is absent | Use the existing `.venv` interpreter; do not recreate setup as the first response |
| A failed run still has old PNGs | Check current manifest status/hashes, not file existence |

### One consolidated review when useful

I can submit my changed original source/tests, run output, one plot and a short explanation together. There is no need to reply between the tasks above. A useful explanation covers:

- How positions produce bumper gap and closing speed, with units/signs.
- Why five samples at 1 s spacing span 4 s.
- How the lead stops without reversing and why the original event is √11 s.
- Why the 8 s non-contact label changes if the horizon is extended.
- How the reference answer is independent of the tested solver.
- Which parts I reconstructed, which scaffolds/reference help I used, and one remaining uncertainty.

The M1 learner checkpoint is ready for completion review when I have my own working attempt, checked outputs, the changed-input transfer and an explanation. Passing existing assistant-reference tests alone does not satisfy that. A struggle or a failed prediction is useful evidence for coaching; it is not a reason to invent understanding.

## Handoff to M2

Carry forward the clean truth fields, SI/sign conventions, full configuration, inclusive horizons and independently checked continuous contact events. Keep the first contact meaningful as the boundary for pre-contact warning evaluation; virtual post-contact gaps are for model inspection.

M2 introduces separate observations with measurement time, arrival/availability time and observation age. A causal replay exposes only arrived observations. The time-to-collision baseline uses positive gap divided by positive closing speed under unchanged current speeds, with explicit contact/non-closing/missing/stale policies. Scoring rules must be specified before tuning, and reference events remain offline evaluator inputs rather than warning inputs. One clean-versus-latency/noise comparison produces the first small report. The full three-fault suite and stop-and-go family remain M3.

The [study guide](../study-guide.md) provides the curriculum order. The next lesson being available does not mean M1 learning or later implementation is complete. My assistant will review the evidence I actually provide and help when I ask; it will not autonomously build the remaining project.
