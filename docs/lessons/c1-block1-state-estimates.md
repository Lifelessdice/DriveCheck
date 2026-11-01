# C1 Block 1 — Preserve the reading and estimate the current gap

Prepared 1 November 2026; reviewed 2 November 2026. The learner saved the supplied `c1_estimators.py` and `test_c1_estimators.py` implementation. Assistant review required no source changes; independent read-only review found no blocking issue. Actual project-interpreter checks passed **15 focused tests in 0.001 s** and **184 full-suite tests in 64.138 s**, both exit 0. C1 is **1 of 5 blocks technically verified locally**. These checks establish the model/contract fixtures, not a warning improvement or independent learner mastery. Replay integration, paired evaluation and interpretation remain pending. The instructions below preserve the complete study block and its original predicted checks.

## Starting point and section sequence

The assistant created `feature/c1-fair-comparison` from locally observed `main` at `b727acb` in response to the request for a new C1 branch. Existing unrelated `.vscode/`, `practice_m1.py` and `t_motion.py` were preserved. No staging, commit, push or merge was performed. Keep this branch through C1.

The five substantial blocks are: (1) the estimate contract and arithmetic; (2) causal replay/policy integration with raw-baseline compatibility; (3) separate development/evaluation configuration and paired inputs; (4) complete paired execution/report/regression checks; (5) interpretation, limitations and M5 handoff. The learner implements and runs them; the assistant maintains documentation and reviews requested work.

Use the actual M4 contracts, not the old 27 October examples. The implemented main matrix has 76 cases: four scenarios × (one clean + six stochastic profiles × three seed bases). Both latency profiles have jitter. Native seed bases 100/200/300 map to base+1, +2, +3, +4 stream seeds. The five fixed-delay diagnostics have their own unchanged policy and separate denominator. Current errors are the implemented aligned MAEs; any additional RMSE must be separately specified, named and checked. Historical C1 seed mapping, RMSE assumptions and 60/92 counts are not the current release contract.

## Why choose age projection?

The saved [M4 failure investigation](../failure-study.md) shows a suitable mechanism. Contact is independently at 6 s. In the strongest diagnostic, at decision time 6 s the selected reading was measured at 3 s and arrived at 5.5 s. It says gap 15 m and closing speed 5 m/s, so the held-value TTC is 3 s, above the diagnostic threshold 2 s. Source ID4 would satisfy the threshold but arrives at 6.5 s, after the horizon. The selected source is fresh at the diagnostic's inclusive age limit 3 s; it is not a stale-data rejection.

Our one candidate is **constant-closing-speed age projection**. It asks where the bumpers would be now if the measured closing speed stayed unchanged since measurement. No smoothing, covariance model, Kalman filter or new dependency is needed. The comparison can still lose under changing speed or noisy measurements.

Let `d` be measured gap, `c` positive closing speed and `a` measurement age. During that age the ego gains `c*a` metres, so `estimated_gap = d - c*a`. Units check: metres minus (metres/second × seconds) gives metres. This follows displacement reasoning in [OpenStax University Physics §3.4](https://openstax.org/books/university-physics-volume-1/pages/3-4-motion-with-constant-acceleration). [SUMO's TTC documentation](https://sumo.dlr.de/docs/Simulation/Output/SSM_Device.html#ttc) supports the gap/closing-speed baseline; neither source validates our warning thresholds. Sources rechecked 1 November 2026.

### Work a prediction before the code

At diagnostic decision time 4 s, source ID1 was measured at 1 s, arrived at 3.5 s and says gap 25 m / closing speed 5 m/s. Its age is 3 s. Raw holds 25 m, producing TTC 5 s. Projection gives `25 - 5*3 = 10 m`, producing TTC 2 s. Under the same diagnostic threshold 2 s and age limit 3 s, a warning is predicted at 4 s, two seconds before independent contact at 6 s. This is a hand prediction, not an observed C1 run.

We must preserve the source timestamps: it remains a 1 s measurement arriving at 3.5 s. Estimating at 4 s does not turn it into a new sensor reading. Main M4 uses maximum age 1.25 s, while the separate diagnostic uses 3 s. Those limits stay unchanged. Projection cannot make an unarrived or rejected stale reading eligible.

## File 1 — `c1_estimators.py`

Create this new file in the project root. Leave `observations.py`, `warning_policy.py`, `replay.py` and the M4 runner untouched in this block.

`Observation` stores what the sensor supplied. The new frozen `StateEstimate` stores the original source plus estimated values at a decision time. Keeping the source object avoids resetting its age or silently overwriting measured gap. The raw adapter is an explicit hold of the measured values.

```python
"""Current-state estimates derived only from an arrived sensor reading."""

from dataclasses import dataclass

from motion import require_finite
from observations import Observation


METHODS = ("raw", "age_projection")


@dataclass(frozen=True)
class StateEstimate:
    """Separate estimated values from their immutable source and timestamps."""

    source: Observation
    estimate_time_s: float
    gap_m: float
    closing_speed_mps: float

    def __post_init__(self):
        if not isinstance(self.source, Observation):
            raise ValueError("source must be an Observation")
        require_finite("estimate_time_s", self.estimate_time_s, minimum=0)
        require_finite("estimated gap_m", self.gap_m)
        require_finite("estimated closing_speed_mps", self.closing_speed_mps)
        if self.source.arrival_time_s > self.estimate_time_s:
            raise ValueError("source has not arrived at the estimate time")

    @property
    def observation_age_s(self):
        return self.estimate_time_s - self.source.measurement_time_s


def estimate_state(observation, now_s, method="raw"):
    """Estimate without truth access, warning thresholds or freshness overrides."""

    require_finite("now_s", now_s, minimum=0)
    if method not in METHODS:
        raise ValueError(f"unknown estimation method: {method!r}")
    if observation is None:
        return None
    if not isinstance(observation, Observation):
        raise ValueError("observation must be an Observation or None")
    if observation.arrival_time_s > now_s:
        raise ValueError("observation has not arrived at now_s")

    gap_m = observation.gap_m
    if method == "age_projection":
        age_s = now_s - observation.measurement_time_s
        gap_m = observation.gap_m - observation.closing_speed_mps * age_s

    return StateEstimate(
        source=observation,
        estimate_time_s=now_s,
        gap_m=gap_m,
        closing_speed_mps=observation.closing_speed_mps,
    )
```

The helper intentionally has no warning threshold, maximum age, horizon or reference event. Block 2 will apply the existing eligibility rule before using an estimate for a warning. A pure arithmetic estimate does not itself grant permission to warn. `None` remains no estimate; a negative projected gap remains signed, rather than being clipped or used as a truth contact label. Repeated calls always start from the original measurement, avoiding repeated subtraction from an already projected value.

## File 2 — `test_c1_estimators.py`

Create the following test module. Literal answers come from the worked calculations; expected values do not call the implementation's formula. The last case deliberately shows larger error under the alternative.

```python
"""Independent arithmetic, source provenance and availability checks."""

import unittest

from c1_estimators import estimate_state
from observations import Observation


def reading(gap=25.0, closing=5.0, measured=1.0, arrived=2.0):
    return Observation("c1_fixture", 1, measured, arrived, gap, closing)


class TestStateEstimates(unittest.TestCase):
    def test_raw_holds_original_values_and_source(self):
        source = reading()
        result = estimate_state(source, 3.0)
        self.assertIs(result.source, source)
        self.assertEqual(result.gap_m, 25.0)
        self.assertEqual(result.closing_speed_mps, 5.0)
        self.assertEqual(result.observation_age_s, 2.0)

    def test_existing_diagnostic_hand_prediction(self):
        source = reading(arrived=3.5)
        result = estimate_state(source, 4.0, "age_projection")
        self.assertEqual(result.gap_m, 10.0)
        self.assertEqual(result.observation_age_s, 3.0)
        self.assertEqual(result.source.measurement_time_s, 1.0)
        self.assertEqual(result.source.arrival_time_s, 3.5)
        self.assertEqual(source.gap_m, 25.0)

    def test_fractional_age(self):
        source = reading(gap=18.0, closing=4.0, measured=1.25)
        result = estimate_state(source, 2.0, "age_projection")
        self.assertEqual(result.observation_age_s, 0.75)
        self.assertEqual(result.gap_m, 15.0)

    def test_zero_age_matches_raw(self):
        source = reading(measured=2.0)
        self.assertEqual(
            estimate_state(source, 2.0, "raw"),
            estimate_state(source, 2.0, "age_projection"),
        )

    def test_opening_motion_increases_projected_gap(self):
        source = reading(gap=18.0, closing=-2.0, measured=1.25)
        self.assertEqual(
            estimate_state(source, 2.0, "age_projection").gap_m, 19.5
        )

    def test_zero_closing_speed_keeps_gap(self):
        source = reading(gap=18.0, closing=0.0)
        self.assertEqual(
            estimate_state(source, 3.0, "age_projection").gap_m, 18.0
        )

    def test_projected_overlap_remains_signed(self):
        source = reading(gap=10.0, measured=0.0, arrived=3.0)
        self.assertEqual(
            estimate_state(source, 3.0, "age_projection").gap_m, -5.0
        )

    def test_repeated_calls_do_not_project_previous_estimate(self):
        source = reading(gap=18.0, closing=4.0, measured=1.25)
        first = estimate_state(source, 2.0, "age_projection")
        second = estimate_state(source, 2.0, "age_projection")
        self.assertEqual(first, second)
        self.assertEqual(second.gap_m, 15.0)
        self.assertEqual(source.gap_m, 18.0)

    def test_no_reading_produces_no_estimate(self):
        for method in ("raw", "age_projection"):
            with self.subTest(method=method):
                self.assertIsNone(estimate_state(None, 0.0, method))

    def test_future_arrival_is_unavailable(self):
        for method in ("raw", "age_projection"):
            with self.subTest(method=method):
                with self.assertRaises(ValueError):
                    estimate_state(reading(), 1.5, method)

    def test_invalid_decision_time_is_rejected(self):
        for now_s in (-1.0, float("nan"), float("inf"), True):
            with self.subTest(now_s=now_s):
                with self.assertRaises(ValueError):
                    estimate_state(None, now_s)

    def test_unknown_method_is_rejected_even_without_data(self):
        with self.assertRaises(ValueError):
            estimate_state(None, 0.0, "projectoin")

    def test_wrong_source_type_is_rejected(self):
        with self.assertRaises(ValueError):
            estimate_state({"gap_m": 25.0}, 2.0)

    def test_projection_overflow_is_rejected(self):
        source = reading(gap=1e308, closing=1e308, measured=0.0)
        with self.assertRaises(ValueError):
            estimate_state(source, 2.0, "age_projection")

    def test_changing_speed_can_make_projection_worse(self):
        source = reading(gap=15.0, measured=0.0)
        raw = estimate_state(source, 2.0, "raw")
        alternative = estimate_state(source, 2.0, "age_projection")
        # Closing speed falls 5 -> 0 over 1 s: only 2.5 m is gained.
        independently_checked_current_gap_m = 12.5
        self.assertEqual(raw.gap_m, 15.0)
        self.assertEqual(alternative.gap_m, 5.0)
        self.assertEqual(abs(raw.gap_m - independently_checked_current_gap_m), 2.5)
        self.assertEqual(
            abs(alternative.gap_m - independently_checked_current_gap_m), 7.5
        )


if __name__ == "__main__":
    unittest.main()
```

For the counterexample, closing speed decreases linearly from 5 to 0 m/s during the first second and remains zero. The gained distance is the triangular area `0.5*1*5 = 2.5 m`, leaving gap 12.5 m. Projection assumes 5 m/s for the entire two-second age, predicting only 5 m gap. It is worse by the current-gap error metric. This is a synthetic calculation test, not a measured M4 loss or final evaluation case.

## Run and inspect the complete block

Learner-run commands, not commands already executed:

```powershell
Set-Location 'E:\DriveCheck'
git branch --show-current
.\.venv\Scripts\python.exe -m unittest -v test_c1_estimators
.\.venv\Scripts\python.exe -m unittest discover -v
```

Expected branch: `feature/c1-fair-comparison`. The new module contains 15 test methods. If saved exactly as supplied and the existing 169-test suite is unchanged, expect 15 focused and 184 total tests. These are expectations, not passing results. No package installation is needed. If an import fails, check file spelling/location, the project directory and existing `.venv` interpreter. If raw tests fail, the raw branch should hold the source values. If repeated projection fails, check source mutation. If opening motion fails, inspect the sign. Infinity must raise rather than produce a valid-looking report number.

Meaningful attempt: without changing the implementation, predict a reading with gap 18 m, closing speed 4 m/s, measurement time 1.25 s, arrival 2 s and decision 2 s. Explain why age is 0.75 s, projected gap 15 m and implied positive-closing-speed TTC 3.75 s. Then predict the sign when closing speed is negative. This explanation is learner evidence only when actually supplied; it is not an extra reply gate before doing the rest of the block.

After saving/running, request review with the output or any error. Do not claim a warning improvement from these unit tests. This block implements a model/contract only; the existing policy/replay and all M4 results must remain unchanged. Review and a selective checkpoint come before Block 2 integration. Expected public implementation paths for that checkpoint are `c1_estimators.py` and `test_c1_estimators.py`, plus documentation actually reviewed at that boundary. Do not use blanket `git add .`; the exact final list/commands will be supplied after review. No push-confirmation reply gate is required.

**Checkpoint after review, 2 November 2026:** learner code is saved; Block 1 is technically verified at 15 focused/184 full passing tests. No assistant source/test change, installation, Git mutation or persistent comparison experiment was needed for this review. Replay integration, split/freeze, complete paired results and learner interpretation remain later work. Save the reviewed selective checkpoint on `feature/c1-fair-comparison` before the next substantial block; no merge is needed between blocks.
