# Methods and technical references

DriveCheck uses a deliberately small model so its assumptions, reference events and failures can be inspected. The references below support the equations and APIs; project-specific warning thresholds, scoring windows and fault settings are experimental conventions.

## Motion and independent contact events

- [OpenStax University Physics, motion with constant acceleration](https://openstax.org/books/university-physics-volume-1/pages/3-4-motion-with-constant-acceleration) supports the position/velocity equations and displacement reasoning. Vehicle positions refer to the ego front bumper and lead rear bumper on a common forward axis.
- Clean motion is evaluated analytically within each phase. Lead braking stops at zero speed; stop-and-go adds hold/restart phases. This avoids making the physical trajectory depend on the chosen sampling interval.
- Contact is the first continuous bumper-gap crossing/touch within the inclusive declared horizon. Independent literal fixtures and hand derivations check event times, phase boundaries, tangency and non-contact cases. A TTC threshold does not generate its own reference labels.
- Signed geometric paths continue after contact for inspection. Negative gap is virtual overlap, not an impact model. Numerical endpoint tolerances and invalid-input policies are defined in the source and boundary tests.

## Time to collision and causal inputs

[SUMO's SSM documentation](https://sumo.dlr.de/docs/Simulation/Output/SSM_Device.html#ttc) documents TTC under unchanged current speeds. For positive gap and positive closing speed, DriveCheck uses `TTC = gap / closing_speed`, with closing speed defined as ego minus lead speed. Contact/overlap, non-closing motion, unavailable and stale readings have explicit branches.

An observation retains separate measurement and arrival timestamps. Replay releases it only after arrival, preserves its original age and keeps the newest eligible measurement under the declared ordering policy. Offline truth is available to scoring and error calculation, not the warning algorithm.

| Policy | Main comparison | Separate fixed-delay diagnostics |
| --- | ---: | ---: |
| TTC warning threshold | 3 s | 2 s |
| Maximum source age | 1.25 s | 3 s |
| Pre-event matching window | 4 s | 3 s |
| Minimum useful warning lead | 1 s | 1 s |

These values are experimental settings, not human response-time claims, driving advice or regulatory thresholds. Diagnostic outcomes are not pooled into evaluation denominators.

## Controlled faults and reproducibility

Noise, latency and dropout are evaluated separately on unchanged clean trajectories. Settings record distributions, magnitudes, units and seeds. Missing readings remain absent rather than becoming zero-gap measurements; delayed readings remain unavailable until arrival.

[Python's `random.Random`](https://docs.python.org/3.14/library/random.html#random.Random) supports generator instances with separate state. Four streams preserve gap-noise, closing-speed-noise, latency and dropout draws. Separate state does not establish statistical independence. Runtime/seed/configuration identity is recorded because [random reproducibility guarantees](https://docs.python.org/3.14/library/random.html#notes-on-reproducibility) have defined limits.

The frozen comparison creates each paired observation stream once and reuses it for both methods. Development and evaluation use distinct physical configurations and derived seed bundles. Related synthetic cases and repeated source trajectories do not establish real-road generalisation or statistical significance.

## Compared method

The alternative projects an eligible old gap using constant closing speed:

`estimated_gap_now = measured_gap - measured_closing_speed * source_age`.

Source timestamps and measured closing speed remain unchanged; the shared freshness gate runs before projection. The method is not a Kalman filter, noise smoother or learned model. Changing acceleration or speed error can invalidate its assumption.

The complete [investigation](c1-investigation.md) connects the original failure to the alternative and all measured gains/losses. [Results](results.md) show that improved gap MAE did not improve positive outcome counts and increased finite-horizon negative warning episodes.

## CARLA export mapping

The optional [CPU import/replay adapter](carla-import.md) uses a custom JSON interchange format. The [CARLA 0.9.16 API](https://carla.readthedocs.io/en/0.9.16/python_api/) motivates world-space bounding-box vertices and simulation snapshot timing; its [collision sensor reference](https://carla.readthedocs.io/en/0.9.16/ref_sensors/#collision-detector) supplies the frame/time and actor identity model for independent contact labels. The [synchrony guide](https://carla.readthedocs.io/en/0.9.16/adv_synchrony_timestep/) informs the capture-time contract. These are API references, not a claim that a simulator capture has been performed. Included exports are original synthetic fixtures; sampled box geometry and linear interpolation are limited offline approximations.

## Implementation and environment

- [Python `dataclasses`](https://docs.python.org/3.14/library/dataclasses.html) provides explicit records. Frozen records preserve observation identity; type annotations alone do not replace runtime validation.
- [Python `unittest`](https://docs.python.org/3.14/library/unittest.html) supplies known-answer, boundary, regression and end-to-end checks without another test framework.
- [Python `venv`](https://docs.python.org/3.14/library/venv.html) isolates the package environment and supports direct interpreter invocation without shell activation.
- [Matplotlib's backend documentation](https://matplotlib.org/stable/users/explain/figure/backends.html) and [`savefig`](https://matplotlib.org/stable/api/_as_gen/matplotlib.figure.Figure.savefig.html) support local noninteractive PNG rendering. Reports use ordinary escaped HTML and relative local assets, without a CDN or dashboard framework.
- [pip hash-checking guidance](https://pip.pypa.io/en/stable/topics/secure-installs/) supports binding exact selected wheel bytes. The checked target is CPython 3.14.7 / Windows x64; the lock is not a claim of arbitrary-platform support.
- [Ruff configuration](https://docs.astral.sh/ruff/configuration/) documents the restricted lint rule set and explicit source/environment exclusions.

Exact selected versions and upstream notices are in [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md), with wheel hashes in [requirements-lock.txt](../requirements-lock.txt). See [reproduction](reproduction.md) for commands and [verification](verification.md) for revision-specific evidence and remaining validation limits.
