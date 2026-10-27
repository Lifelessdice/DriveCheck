# M4 — Build a reproducible CPU release

Prepared 27 October 2026. **This lesson is study material. Its proposed code, commands and expected answers have not been implemented or run as M4.** You implement the section and collect the evidence. Read the blocks in order, work at your own pace and ask for help when useful; no reply is required between steps.

The latest instruction is lesson authoring, correcting the earlier request that was interpreted as permission for autonomous implementation. Some M1 source, tests, dependencies and plots already exist as preserved AI reference material. Their presence does not mean you completed or understand M1. At authoring time, the inspected product has the M1 reference interfaces; the later modules below are proposed. This lesson changes only this document.

## Before you start

Complete the learner work in [M1](m1-clean-movement.md), [M2](m2-warning-and-report.md) and [M3](m3-fault-suite.md) first. M4 joins and checks their work rather than replacing it. You should have both scenario families, independent contact/non-contact references, causal replay, the TTC policy, all three single-fault mechanisms and meaningful regression tests. Keep their choices fixed while building the release. If your implemented names differ from this lesson, write a small adapter at the experiment boundary and record the mapping.

The existing M1 reference has `motion.Scenario`, `motion.TruthSample`, `sample_truth`, `truth_at`, `first_contact_time` and `scenarios.load_fixtures`. Truth fields are:

```text
scenario_id, sample_id, time_s,
ego_front_x_m, lead_rear_x_m,
ego_speed_mps, lead_speed_mps, gap_m, closing_speed_mps
```

Both positions share a forward axis. Gap is lead rear minus ego front, in metres; closing speed is ego minus lead speed, in m/s. Contact is independently determined from continuous clean trajectories within the declared horizon. A negative label means no contact within that horizon.

Follow the [shared study guide](../study-guide.md) for later interfaces:

| Proposed module | Responsibility you should already have or complete here |
| --- | --- |
| `observations.py` | `Observation(scenario_id, sample_id, measurement_time_s, arrival_time_s, gap_m, closing_speed_mps)`; fault settings/seeds stored separately |
| `replay.py` | Releases only arrived observations; explicit duplicate, ordering, missing and stale policies |
| `warning_policy.py` | Uses arrived observations/current time; records decision time, measurement time, age, TTC, warning and reason |
| `evaluation.py` | Uses independent truth/reference events offline to score decisions and aligned errors |
| `experiments.py` | Expands cases, calls the preceding modules and saves every outcome |
| `reporting.py` | Renders saved evidence into a local HTML report and plots |
| `drivecheck.py` | Proposed CLI entry point |

Use `warning_policy.py`: naming your module `warnings.py` would shadow Python's standard-library module. Dropout omits observations; it never means zero gap. An absent value is `None`/JSON `null` with an explanation, not a fabricated numeric result.

All learner commands below run from `E:\DriveCheck`, with the existing `.venv` unless a fresh environment is explicitly named. A proposed command becomes verified only after you run it and inspect its output. There is no CARLA, cloud service, credential or paid dependency in the CPU workflow.

## Block 1 — Freeze the question and count the work before running it

Your outcome is a configuration that enumerates exactly what will run. An experiment matrix is an inventory of cases, not a list of selected attractive results. Freeze it before inspecting outcomes. You can investigate surprising cases afterward, but retain the original matrix and record any revised experiment as a new configuration.

Ask: **How do noise, latency and dropout separately change the raw TTC warning outcomes on the same clean trajectories?** The warning is passive; it does not alter either vehicle. A warning cannot be credited with preventing contact.

Use four M3 scenarios: lead braking/contact, lead braking/non-contact, stop-and-go/contact and stop-and-go/non-contact. Preserve each complete configuration, time grid, horizon and independent reference explanation. Reuse the original M1 constant-speed fixture as a small test, rather than pretending it is the second required family. The names `stop_go_contact` and `stop_go_noncontact` below are proposed aliases: bind them to your actual M3 fixtures, including their exact parameters and references.

Here is a bounded teaching design. The fault magnitudes and seeds are experimental choices, not validated sensor specifications or safety limits.

| Profile | Exact fault settings | Seeds per scenario | Cases per scenario |
| --- | --- | --- | ---: |
| clean | No perturbation/delay/dropout | `null` | 1 |
| noise_low | Independent zero-mean Gaussian gap SD 0.25 m; closing-speed SD 0.10 m/s | 11, 29, 47 | 3 |
| noise_strong | Same distributions; SD 2.0 m and 1.0 m/s | 11, 29, 47 | 3 |
| latency_low | Fixed delay 0.10 s | `null` | 1 |
| latency_strong | Fixed delay 0.60 s | `null` | 1 |
| dropout_low | Independent per-sample dropout probability 0.05 | 11, 29, 47 | 3 |
| dropout_strong | Same mechanism, probability 0.30 | 11, 29, 47 | 3 |

There are `1 + 3 + 3 + 1 + 1 + 3 + 3 = 15` cases per scenario, hence **60 planned cases**, comprising **30 reference-contact and 30 non-contact episodes**. These are inventory counts, not measured results. There are seven profiles and three stochastic seeds; deterministic profiles are not repeated under three meaningless seed labels. Rows sharing the same scenario are not independent samples from real traffic.

If M3 uses a different documented distribution or dropout pattern, preserve that mechanism and write its complete parameters here. A burst dropout and independent Bernoulli dropout are different experiments. Do not silently call both `dropout_strong`. Similarly, preserve M3's treatment of negative noisy gaps: if clipping is chosen, record it because clipping changes the distribution.

Create a proposed `configs/m4-release.json`. This is an experiment schema to implement, not a file that already exists:

```json
{
  "schema_version": "drivecheck.experiment.v1",
  "scenario_catalog": "configs/m3-fixtures.json",
  "scenario_ids": [
    "lead_braking_contact", "lead_braking_noncontact",
    "stop_go_contact", "stop_go_noncontact"
  ],
  "decision_timestep_s": 0.1,
  "decision_clock": "base_times_union_arrivals_within_horizon",
  "warning_policy": {"ttc_threshold_s": 2.0, "max_age_s": 0.5},
  "evaluation_policy": {"window_s": 3.0, "min_useful_lead_s": 0.5},
  "fault_profiles": [
    {"profile_id": "clean", "kind": "clean", "parameters": {}, "seeds": [null]},
    {"profile_id": "noise_low", "kind": "noise", "parameters": {"gap_std_m": 0.25, "closing_std_mps": 0.1}, "seeds": [11, 29, 47]},
    {"profile_id": "noise_strong", "kind": "noise", "parameters": {"gap_std_m": 2.0, "closing_std_mps": 1.0}, "seeds": [11, 29, 47]},
    {"profile_id": "latency_low", "kind": "latency", "parameters": {"delay_s": 0.1}, "seeds": [null]},
    {"profile_id": "latency_strong", "kind": "latency", "parameters": {"delay_s": 0.6}, "seeds": [null]},
    {"profile_id": "dropout_low", "kind": "dropout", "parameters": {"probability": 0.05}, "seeds": [11, 29, 47]},
    {"profile_id": "dropout_strong", "kind": "dropout", "parameters": {"probability": 0.3}, "seeds": [11, 29, 47]}
  ]
}
```

Resolve `scenario_catalog` relative to the project root, rather than accidentally relative to the `configs` directory twice. The alias/catalog loader is your adapter task: M1's existing loader understands its M1 schema; do not feed it a new stop-and-go configuration and assume it works. Implement or reuse the M3 loader and return a common record with `scenario_id`, `family`, `horizon_s`, clean samples, independent contact time, full configuration and reference basis. One contact event per episode is the bounded scoring assumption; extend the schema explicitly before supporting several events.

The decision grid is distinct from the sensor sample grid. Retain M3's source sampling; a 0.1 s decision interval does not manufacture ten new observations from a 1 s source interval. Build base times by integer index, include zero/the horizon once, then use M2's `make_decision_times` to include arrivals within the horizon. This retains the union-arrival convention rather than rounding an arrival back to an earlier tick. Define and test a final shorter base interval if the horizon is not divisible by the decision step. Preserve full precision and record the actual grid: errors remain decision-weighted, and additional arrival instants can change that weighting.

In `experiments.py`, start with this small enumeration function after input validation:

```python
def enumerate_cases(config):
    cases = []
    for scenario_id in config["scenario_ids"]:
        for profile in config["fault_profiles"]:
            for seed in profile["seeds"]:
                suffix = "none" if seed is None else str(seed)
                cases.append({
                    "case_id": f"{scenario_id}__{profile['profile_id']}__s{suffix}",
                    "scenario_id": scenario_id,
                    "profile_id": profile["profile_id"],
                    "kind": profile["kind"],
                    "parameters": dict(profile["parameters"]),
                    "seed": seed,
                })
    return cases
```

Your tasks are to validate the input before this function, reject duplicate IDs/seeds and check that the expanded case IDs are unique. Reject unknown root/profile/parameter keys, non-finite numbers, booleans masquerading as numbers, invalid probabilities, non-positive decision intervals and an empty scenario/profile list. Require nonnegative integer seeds for stochastic profiles and `[null]` for deterministic ones. Validate all scenarios/references before creating a run folder.

M2's lesson uses threshold 3 s, age 1.25 s, window 4 s and useful lead 1 s. This M4 worked release config uses an explicitly different, frozen parameter set; retain the original M2 config and tests. The warning branches and event-scoring semantics stay the same. Do not mix parameter sets when checking predictions. You may instead retain M2's parameters for your release, but then recalculate this lesson's parameter-specific fixtures, particularly the all-stale delay example, before interpreting outcomes. Neither choice should be made by tuning against favourable results.

### A worked adapter to M3's four-stream fault configuration

The experiment file above uses presentation names `gap_std_m`, `closing_std_mps`, `delay_s` and `probability`. M3's proposed `faults.FaultConfig` uses **`gap_sigma_m`, `closing_sigma_mps`, `latency_s`, `dropout_probability`** and four explicit integer seeds. A case seed alone is insufficient for that constructor. Write the following boundary adapter in `experiments.py` after M3 is implemented:

```python
from dataclasses import asdict
from faults import FaultConfig


def fault_config_for_case(case):
    seed = case["seed"]  # Already validated: nonnegative int or None.
    # Derivation version: four-streams-v1. Avoid process-randomized hash().
    # A deterministic profile still receives valid, unused stream seeds.
    base = 0 if seed is None else 4 * seed
    settings = {
        "mode": case["kind"],
        "gap_seed": base,
        "closing_seed": base + 1,
        "latency_seed": base + 2,
        "dropout_seed": base + 3,
    }
    parameters = case["parameters"]
    if case["kind"] == "noise":
        settings["gap_sigma_m"] = parameters["gap_std_m"]
        settings["closing_sigma_mps"] = parameters["closing_std_mps"]
    elif case["kind"] == "latency":
        settings["latency_s"] = parameters["delay_s"]
    elif case["kind"] == "dropout":
        settings["dropout_probability"] = parameters["probability"]
    # The validated kind may also be clean; all inactive magnitudes default to 0.
    # latency_jitter_s stays 0 for these fixed-delay experiments.
    return FaultConfig(**settings)
```

For case seed **11**, the stored stream seeds are **44, 45, 46, 47**; for 29 they are 116, 117, 118, 119; for 47 they are 188, 189, 190, 191. For clean/fixed-latency `seed: null`, use **0, 1, 2, 3**, with `seed_role: "unused deterministic placeholders"`. M3 may draw all four streams per source row for audit consistency, but zero sigmas/jitter and dropout probability zero mean those draws cannot affect clean/fixed-delay observations. Test that changing the placeholder bundle leaves the observation values, arrivals and retained IDs unchanged.

Save `asdict(fault_config_for_case(case))`, the case seed and `seed_derivation_version: "four-streams-v1"` in each case's resolved configuration. Do not reconstruct that information later from a label. Gap and closing generators must use their distinct seeds: initializing both with 11 would produce identical standardized Gaussian sequences, contradicting the intended independently varied noise. Distinct generator state is an engineering separation, not proof of statistical independence of every finite sequence.

Follow M3's fixed draw order for every source row, before dropout filtering, and preserve its separate offline audit. Matching case seeds across low/strong profiles intentionally matches their underlying standardized draws, and matching seeds across scenarios can correlate diagnostic streams. Explain this controlled pairing rather than claiming all 60 cases are independent replications. Add adapter tests for all seven profiles, exact derived bundles, inactive magnitudes staying zero and saved resolved settings. The existing catalog adapter does not replace this fault adapter.

**Check your work:** predict the count before running enumeration. Assert 60 distinct IDs and 30 positive references after joining the catalog. Change only the stochastic seed lists to four distinct seeds: each scenario then has `1+4+4+1+1+4+4 = 19` cases, so the expected count becomes **76**, not 80 or 84. Restore the frozen release config afterward. This transfer check catches an accidental full Cartesian product over deterministic seeds.

### Make the scenario catalog concrete

M3 constructs `StopGoScenario` records in its study driver; it does not require a finished shared catalog loader. M4 therefore supplies that missing dispatch boundary. Create proposed `configs/m3-fixtures.json` with this **new catalog schema**, keeping the existing M1 file unchanged:

```json
{
  "schema_version": "drivecheck.catalog.v1",
  "m1_fixtures_path": "configs/m1-fixtures.json",
  "stop_go_fixtures": [
    {
      "configuration": {
        "scenario_id": "stop_go_contact", "initial_gap_m": 15.0,
        "ego_speed_mps": 4.0, "lead_speed_mps": 4.0,
        "lead_deceleration_mps2": 2.0, "hold_s": 2.0,
        "lead_acceleration_mps2": 2.0, "restart_speed_mps": 6.0,
        "timestep_s": 1.0, "sample_count": 9
      },
      "reference": {
        "contact_time_s": 5.0, "final_gap_m": 2.0,
        "basis": "During restart u=t-4, gap=3-4u+u^2=(u-1)(u-3); first zero at u=1, t=5. At t=8: 15+19-32=2 m."
      }
    },
    {
      "configuration": {
        "scenario_id": "stop_go_noncontact", "initial_gap_m": 18.0,
        "ego_speed_mps": 4.0, "lead_speed_mps": 4.0,
        "lead_deceleration_mps2": 2.0, "hold_s": 2.0,
        "lead_acceleration_mps2": 2.0, "restart_speed_mps": 6.0,
        "timestep_s": 1.0, "sample_count": 9
      },
      "reference": {
        "contact_time_s": null, "final_gap_m": 5.0,
        "basis": "During restart gap=(u-2)^2+2 has minimum 2 m; earlier/later phases stay positive. At t=8: 18+19-32=5 m."
      }
    }
  ]
}
```

These are M3's hand-derived schedule and answers, now serialized for reuse. The final positive gap of the contact case does not erase its earlier contact. A sampled-endpoint-only detector would get this wrong. Inspect the M3 derivation before implementing the loader.

Implement proposed `load_catalog(path)` in `experiments.py` as a version dispatch: `drivecheck.truth.v1` uses the existing M1 loader; `drivecheck.catalog.v1` loads the named M1 fixtures then constructs M3 `StopGoScenario` entries with their separate sampler/continuous evaluator. Reject unknown schemas/keys, duplicate IDs across both lists, invalid references and mismatched declared horizon. Bind M1 records to `sample_truth`/`truth_at`; bind stop-and-go records to `sample_stop_go_truth`/`stop_go_truth_at`. Return one common internal record shape; keep constructors family-specific. Use stored independent reference answers for scoring, and test the continuous contact solver against them as a separate validation step. Do not regenerate the labels from the solver under test.

For the warning/scoring boundary, map M4 `ttc_threshold_s` to M2's `warning_threshold_s` argument, `window_s` to `pre_event_window_s` and `min_useful_lead_s` to `minimum_useful_lead_s`. Pass `max_age_s` unchanged. The shared `score_case` returns M2's canonical fields. These name translations belong in orchestration, not hidden in the physics or policy functions. Snapshot/hash both the catalog and included M1 file; copying only the outer filename is insufficient provenance.

## Block 2 — Define what every result means

Your outcome is one unambiguous result row per planned case, including software failures. A contact scenario with no useful warning is an **algorithm outcome**. A crash before it can be evaluated is a **failed execution**. Mixing those meanings makes rates misleading.

Freeze the M2 evaluator's convention in the saved configuration. For the worked convention here, contact at `T` has a useful interval `[max(0, T-window_s), T-min_useful_lead_s]` and a late interval `(T-min_useful_lead_s, T]`. Endpoints are deliberate. If the useful interval is empty, no warning can satisfy it. Warnings after contact cannot rescue the event. For a negative episode, any warning within `[0, horizon_s]` makes that episode a false-warning episode.

Use eligible warning decision instants from the causal policy. Repeated `True` ticks can supply the earliest match, but they still count as **one event/episode outcome**, not dozens of detections. Store the first actual warning in the whole episode as well as the earliest matched warning. A warning already active when the useful window starts must not be presented as newly issued there: show its original onset separately. If your M2 policy scores alert onsets rather than active decisions, retain that policy, label it explicitly and adjust the expected fixture consistently before freezing M4; do not change scoring to make a failure disappear.

Preserve M2's mutually exclusive positive-event `outcome` values: **`useful`, `late`, `missed`**. A `late` result has a match within the window, so it is not also a `missed` event under M2's definition. Add the explicitly different diagnostic `without_useful_warning = outcome != "useful"` for positives. This includes late and missed events. Also retain `has_late_warning`, since an episode may have both a useful warning and later warning ticks. Do not add overlapping diagnostic counts to the exclusive outcome counts.

Work through this invented **metric fixture**, which is an arithmetic check, not an experimental result. All contact events occur at 5 s, with a 3 s window and 0.5 s minimum lead time. The useful interval is `[2, 4.5]`, and the late interval is `(4.5, 5]`.

| Case | Reference | Warning times | Expected classification |
| --- | --- | --- | --- |
| A | Contact at 5 s | 2.0, 2.1, 2.2 | Useful; earliest matched lead is 3.0 s |
| B | Contact at 5 s | 4.8 | `late`; without a useful warning |
| C | Contact at 5 s | None | `missed`; without a useful warning |
| D | No contact during 6 s | 1, 2, 3 | One false-warning episode |
| E | No contact during 6 s | None | No false-warning episode |
| F | No contact during 6 s | Execution fails | Unevaluated; retain error, no algorithm metric |

There are 6 planned cases, 5 evaluated, 1 failed. Planned references are 3 positive and 3 negative; evaluated references are 3 positive and 2 negative. M2's **missed-event rate is 1/3**, the **late rate is 1/3**, and the separately labelled **fraction without a useful warning is 2/3**. The negative false-warning episode rate is **1/2**. The third planned negative episode is unevaluated, so **1/3 is not a measured false-warning rate**. Display coverage `2/3 planned negative episodes evaluated` alongside `1/2 evaluated negatives warned`. Matched lead times are **3.0 s (useful)** and **0.2 s (late)**, with support **2/3 evaluated positives matched**. Useful matched lead is 3.0 s with support **1/3**. Reporting only an average of matched leads hides the unmatched event and may hide lateness.

Implement `summarize(results)` in `evaluation.py` or reuse its M2 equivalent. Return numerator and denominator together, not only a rounded percentage. For zero denominators, return `null` and display “not applicable (0 eligible episodes)”; zero percent would imply evidence that does not exist. Keep counts of failed, partial and not-run cases and their known reference classes outside algorithm rates. A partial trace is useful for debugging, but do not evaluate it as though the full horizon completed.

Each completed row should contain at least:

```text
case_id, scenario_id, family, horizon_s, reference_contact_time_s,
profile_id, fault_kind, fault_parameters, seed, resolved_fault_config,
seed_derivation_version, execution_status, outcome,
without_useful_warning, false_warning_episode,
first_warning_time_s, first_matched_warning_time_s,
matched_lead_s, has_late_warning,
gap_mae_m, closing_mae_mps, gap_rmse_m, closing_rmse_mps,
mae_support, rmse_support, error_message
```

Use `null` for metrics that do not apply: for example a negative episode has no missed contact event or matched contact lead. Keep `execution_status` values such as `complete`, `failed`, `partial`, `not_run` distinct from `event_outcome`. Boolean false and numeric zero are valid values and must not be replaced with blank text by `value or "N/A"`.

Use M2's `score_case` return keys directly where available: `outcome`, `first_matched_warning_time_s`, `matched_lead_s`, `first_warning_time_s` and warning diagnostics. Negative outcomes are `false_warning` or `clear_negative`. M4 adds status/coverage/provenance and derived summary fields; it does not replace the scorer with a competing definition. Top-level `results.json` is proposed as `{"schema_version": "drivecheck.results.v1", "cases": [...], "summary": {...}}`. Keep nested resolved settings in JSON; flatten only scalar fields into CSV or encode nested settings as a clearly named JSON-text column.

Give **each** of `mae_support` and `rmse_support` its own `start_time_s`, `end_time_s`, `weighting`, `eligible_steps`, `total_steps`, `missing_steps`, `stale_steps` and `coverage`. Use `weighting: "decision_instants"` and make `coverage` null when total steps are zero. Flatten these with `mae_`/`rmse_` prefixes in CSV if desired. The gap and closing metrics share a support bundle only because each accepted observation must contain both finite values. Do not put MAE and RMSE over different intervals under one shared denominator.

**Learner task:** write literal expected assertions for A–F. Then add a warning exactly at 4.5 s, one just later, one after 5 s, a repeated sequence, an event at time zero and a group with no negatives. Explain each expected outcome before inspecting the implementation. Check the identities `evaluated + failed + partial + not_run == planned` and `useful + late + missed == evaluated_positives`. For each subgroup, compute rates from its own eligible denominator.

Do not compare profile quality using a pooled rate alone: stochastic profiles have three seed repetitions while clean/fixed-latency profiles have one. Show counts per family/profile and the individual seed results. With three seeds, list the observed values and perhaps their range; do not claim statistical significance or generalisation to traffic.

## Block 3 — Align errors in time and keep the runner honest

Your outcome is an experiment runner whose evidence can be traced back to a causal decision. Sensor measurement error and current-state error answer different questions. Retain M2's decision-weighted mean absolute errors (MAEs) and their original documented interval. Add RMSE as a separately labelled diagnostic, with the explicit pre-contact interval below; never silently rename MAE as RMSE or compare aggregates over different intervals as if they were identical.

Consider a constant-speed truth with gaps 30, 25 and 20 m at times 0, 1 and 2 s. A noise-free sensor is delayed by 1 s. At decision time 1 s, the newest arrived reading describes time 0 and says 30 m; current truth is 25 m. At decision time 2 s, the newest reading describes time 1 and says 25 m; current truth is 20 m.

The sensor's measurement-time gap errors are zero, but the raw held current-gap errors are +5 m and +5 m. Their root-mean-square error (RMSE) is `sqrt((25+25)/2) = 5 m`. If closing speed is a constant 5 m/s, its current-state RMSE is 0 m/s. At time zero no reading has arrived, so coverage is **2/3 decision instants**, not 3/3. This isolated arithmetic fixture uses `max_age_s = 1.0`, inclusive, to make both arrived readings eligible; it is deliberately separate from the release example's 0.5 s policy. Under a 0.5 s freshness limit all these delayed readings are stale and current-state RMSE is unavailable with **0/3 eligible steps**.

For the raw baseline, make its current-state estimate explicit: the most recent accepted observation's gap/closing speed is held at the decision time, without secretly extrapolating it. An extrapolator would be a different method, reserved for a separately evaluated comparison. Evaluate error only where the reading passes the same missing/stale eligibility rule as the warning input. Count every excluded missing/stale step. State the error interval: use decision instants from zero through the earlier of contact and horizon, inclusive; virtual post-contact overlap is excluded from this metric.

Implement or extend these proposed interfaces in `evaluation.py`:

```python
import math


def rmse(errors):
    if not errors:
        return None
    return math.sqrt(math.fsum(e * e for e in errors) / len(errors))


def aligned_errors(decisions, truth_at_time, end_time_s):
    """Offline only. truth_at_time(t) returns the clean state at t.

    Return RMSEs, eligible/total step counts and missing/stale counts.
    Implement using the selected causal input saved with each decision.
    """
    # Task: count all decisions at t <= end_time_s.
    # Task: exclude and count unavailable/stale inputs, without zero filling.
    # Task: compare accepted held inputs to truth_at_time(decision_time_s).
    # Task: return both RMSEs and coverage; return None when none are eligible.
    raise NotImplementedError("Complete the time-alignment exercise")
```

The comments define your implementation exercise. This helper supplies the pre-contact `rmse_support`; retain or adapt M2's MAE helper with its own interval and `mae_support`. Test that a contact before the horizon gives different total support counts when MAE includes later decision instants, and that each reported coverage uses its corresponding count. Use the A–F fixture from Block 2 for event scoring and this delay fixture for error scoring; they test separate responsibilities. An empty error list should return `None`, while a nonempty list of exact zeros should return `0.0`. Reject non-finite data upstream instead of allowing NaN to pass through a JSON file.

Extend the proposed decision trace with the accepted observation's source sample ID, `gap_m`, `closing_speed_mps` and eligibility reason, or retain a stable reference to that observation in a separate trace. The shared suggested decision fields alone do not carry enough numeric values to reconstruct errors. Record this addition explicitly. Only the evaluator receives `truth_at_time` or reference events; replay/warning functions must receive observations/current time, never clean truth. For stop-and-go, use M3's continuous truth evaluator, or an explicitly documented interpolation policy checked at acceleration boundaries. Do not linearly interpolate through a stop or braking transition without checking what it means.

Now wire one case through `experiments.py` using the following proposed contract:

```text
run_case(case_spec, scenario_record, warning_policy, evaluation_policy)
    -> {result, truth_rows, audit_rows, observation_rows, decision_rows}

scenario_record contains clean configuration, family, horizon,
independent event/reference basis and the clean trajectory evaluator.
```

Write this function as a short composition of your existing M1–M3 functions. Its order should be: generate/read truth; create one configured observation stream and its per-source audit using local seeded generators; replay it at the declared decision times; run the warning policy; evaluate offline; return rows. Reset all replay/warning/RNG state for each case. A previous case must not influence the next. Do not reseed inside the per-sample loop. Record whether you used the standard-library RNG or NumPy's generator and which algorithm/version; a seed alone does not describe the random stream across changing implementations.

Use these proposed run artifacts:

```text
outputs/m4-release-01/
    config.json                 exact validated/resolved configuration
    case-plan.json              every planned case and reference summary
    results.json                all per-case rows and grouped summaries
    results.csv                 stable scalar columns, all case statuses
    manifest.json               run status, versions, hashes, artifact index
    report.html                 readable offline entry point
    cases/<safe-case-id>/
        truth.csv
        fault-audit.csv
        observations.csv
        decisions.csv
        metrics.json
        timeline.png
```

`fault-audit.csv` retains M3's one audit row for **every source sample**, including sample ID, measurement time, noise draws/errors, delay, computed arrival and dropped flag. Preserve the audit for clean cases too. Compare it with observations to distinguish a dropped sample from a retained sample whose arrival is beyond the horizon. Neither belongs in the policy's future knowledge: give replay only observations and keep the audit offline. If a case fails before audit generation completes, retain any available diagnostic rows with the failed/partial status; never fabricate the missing audit.

Copy complete scenario and fault settings into `config.json` or referenced immutable artifacts, not only scenario names and paths to files that may later change. Hash the actual config, catalog, source, lock files and generated traces. Record the exact runtime, OS/architecture, algorithm/policy versions and a source-file SHA-256 inventory. A Git commit can be recorded if you have one; it is not required to reproduce an unpublished local snapshot. Keep creation time, absolute paths and environment metadata separate from deterministic case metrics so they do not defeat semantic result comparisons.

Preflight every input and output path before the run. Choose a new output directory for each run; refuse an existing directory rather than mixing yesterday's CSV with today's error. Check safe IDs and prevent path traversal. Never allow an output path to overwrite source or configuration. The copied resolved configuration should describe effective settings, including defaults, rather than merely the original file text.

First save the complete case plan and a `running` manifest. Execute each case. A case exception should produce a failed result with case ID and useful error text, then permit the runner to attempt the remaining cases. Do not catch exceptions and append a fake all-zero success row. Save completed/failed rows incrementally; if the process is interrupted, a finalised run is absent and the manifest remains `running`/`partial`. A reader must not treat that as complete. Derive the final run status from planned/result IDs, case execution status **and** successful report/artifact generation. A rendering failure makes the release run partial/failed even if algorithm cases completed. Exit nonzero whenever the run is incomplete.

**Learner checks:** run a case alone and after another case; its causal observations and metrics must agree. Repeat the full frozen matrix in another new folder. Hash the truth of the same scenario under all profiles: it must be identical. Check that a complete case's audit count equals its truth count; all retained source IDs appear once in observations, including pending arrivals, while dropped IDs appear only in the audit. Reorder case execution and check that stochastic case results remain unchanged. Force one controlled case error in a test through an injected runner callable; expect all planned IDs retained, one failure, remaining cases attempted and a nonzero run result. Remove the injection afterward; do not add a public “pretend success” option.

## Block 4 — Make the CLI usable and the report readable offline

Your outcome is one documented command that a reader can use without editing Python source. A command-line interface (CLI) takes explicit arguments, validates them and describes problems clearly. Use standard-library `argparse`; it provides help/usage text and argument errors. [Python argparse documentation](https://docs.python.org/3.14/library/argparse.html)

Here is the proposed command surface. Implement it in `drivecheck.py`, adapting existing M2 entry-point code where sensible:

```powershell
Set-Location 'E:\DriveCheck'
.\.venv\Scripts\python.exe .\drivecheck.py --help
.\.venv\Scripts\python.exe .\drivecheck.py --config .\configs\m4-release.json --output-dir .\outputs\m4-release-01
```

Keep M2's `--config`, `--output-dir` and an optional `--debug` initially. Avoid dozens of overrides that make the saved file disagree with the effective experiment. This starting shape separates command parsing from execution:

```python
import argparse
from pathlib import Path


def build_parser():
    parser = argparse.ArgumentParser(
        description="Replay the configured CPU experiment and write an offline report.",
        allow_abbrev=False,
    )
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--debug", action="store_true")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    # Task: load/strictly validate JSON, catalog and policy before writing files.
    # Task: convert expected input/config/path errors to parser.error(message).
    # Task: run all cases, save artifacts and render the report.
    # Return 0 only for a complete run; return 1 for execution/report failures.
    raise NotImplementedError("Connect the experiment and report functions")


if __name__ == "__main__":
    raise SystemExit(main())
```

Build the omitted work from the Block 3 contract; these are the learner-owned integration steps. Connect the parsed paths to `experiments.run(args.config, args.output_dir)` after preflight. Use `parser.error` for invalid arguments/configuration, which gives exit code 2. Use exit 1 for runtime/incomplete-run failures and exit 0 for successful `--help` or a complete run. Expected errors should identify file, field and remedy: `configs/m4-release.json: fault_profiles[4].parameters.delay_s must be >= 0` is useful. A bare `invalid configuration` is not. In debug mode retain the traceback for unexpected failures; normal mode should still preserve the underlying error type/message and failed case in results.

Use `json.loads` with a duplicate-key hook like the existing M1 loader. Reject JSON NaN/Infinity and use `json.dump(..., allow_nan=False, indent=2)` for outputs. Validate decoded numeric values with `math.isfinite`, too: an overflowing exponent can become infinity. Reject unknown keys so a misspelling such as `max_age_seconds` cannot silently fall back to a default.

**Your error exercise:** make a separate invalid config copy, set dropout probability to 1.2 and run it into a new output name. Expect exit 2, a field-specific message and no run directory. Try a missing catalog, an unknown scenario, duplicate seed, unknown CLI flag, negative delay and an already existing output directory. Each should fail explicitly. On PowerShell, inspect `$LASTEXITCODE` immediately after the Python command; do not treat the presence of old output files as success.

In `reporting.py`, build a small HTML document from saved results. Use inline CSS and relative local PNG paths; no CDN, external font, web request or JavaScript framework is needed. Escape table cells and JSON text using `html.escape`, including error messages. Generate filenames only from validated IDs. Use a real HTML table with column headings and a text caption; plot colour should not be the only way to identify clean/fault/reference lines.

For example, this cell formatter preserves meaningful zero/false values:

```python
from html import escape


def cell(value):
    return "N/A" if value is None else escape(str(value))
```

Render these parts in this order:

1. Run completeness: planned/evaluated/failed/partial/not-run counts and a conspicuous incomplete status when relevant.
2. Question, model limits, scenario families/horizons and the frozen warning/scoring convention.
3. Counts/rates by family and profile, with numerator/denominator and coverage; list seed outcomes.
4. The full 60-row case table, including failed cases and their errors. Link to per-case evidence.
5. Representative plots chosen by a documented rule, such as all four clean cases and the investigated failure. Every case still has its trace/metrics and a navigable plot link.
6. The failure study and limitations, effective configurations, seed/RNG information, versions, source/lock hashes and reproduction command.

Do not choose representative plots by dropping failures from the table. Make an explicit `plot_selection` description if you do not embed all 60 images. For a warning timeline plot, use shared time axes: clean gap versus held observed gap in metres; clean/observed closing speed in m/s; warning state/availability and age with stale limit. Mark independent contact time, useful-window boundaries and the horizon. Show observation measurement time and arrival time distinctly in a trace or second panel. Use a stepped line for a held observation; a smooth joining line can falsely imply continuous knowledge.

Do not plot `None` as zero. Leave missing/stale regions blank or mark them separately. Use consistent units/scales for a clean-versus-fault comparison, and explain any zoom. Close Matplotlib figures after saving and use its non-interactive `Agg` backend before importing `pyplot`, following the existing M1 pattern, so generating the report does not require a desktop display.

After you implement it, inspect your actual output:

```powershell
Get-Content -LiteralPath .\outputs\m4-release-01\manifest.json
Get-Content -LiteralPath .\outputs\m4-release-01\results.csv -TotalCount 8
Start-Process -FilePath (Resolve-Path .\outputs\m4-release-01\report.html).Path
```

The final command intentionally opens a visible report for you to review. Expected checks: the manifest says complete only when all cases/report succeeded; the case table has exactly the planned IDs; denominators match the JSON; local images load; an incomplete test run has a visible failure message. Disconnect networking or use browser offline mode and reopen the report. Move/copy the **whole run folder**, not just HTML, into another local location under `outputs/` and check links again. This verifies relative assets rather than a hidden dependency on your original absolute path.

**Completion for this block:** write down one CLI error you diagnosed and one report defect you checked visually. A screenshot or successful file-open alone does not establish that the results are correct.

## Block 5 — Write a failure investigation with a testable explanation

Your outcome is an investigation of an observed result, supported by a trace, an independent calculation and a regression test. A failure study is more than “latency is bad”. It asks what changed, identifies the mechanism and states what the evidence can and cannot establish.

Start with a real failing or surprising case from your frozen results. Candidate categories are a missed useful warning, a false-warning negative episode, an implausible error metric or a failed execution. Treat a software defect differently from a documented algorithm limitation. Keep the original result/configuration before changing anything. If every evaluated warning outcome happens to satisfy your policy, investigate a real limitation such as stale gaps or a challenging negative warning; do not invent a measured failure.

Here is a fully worked **prediction to test**, grounded in the preserved M1 braking fixture. It is not an observed M4 result. Initial gap is 30 m, ego speed 20 m/s, lead speed 15 m/s; lead braking begins at 1 s with magnitude 5 m/s² and stops the lead at 4 s. During braking:

```text
ego front = 20t
lead rear = 30 + 15t - 2.5(t-1)^2
gap       = 30 - 5t - 2.5(t-1)^2
```

Equality of bumper positions gives `t² = 11`, so independent contact is `sqrt(11) ≈ 3.3166247904 s`. This follows from the two positions, not from the TTC threshold. Keep the source sampling at 1 s for this small regression fixture. At 1 s, gap is 25 m and closing speed 5 m/s, giving TTC 5 s. At 2 s, ego is at 40 m, lead rear at 57.5 m, gap 17.5 m and closing speed 10 m/s, giving TTC **1.75 s**. A clean 2 s threshold therefore first warns at 2 s; earliest matched lead is `sqrt(11) - 2 ≈ 1.3166247904 s` under a 3 s matching window and 0.5 s minimum useful lead.

Now apply fixed latency 0.6 s with a maximum accepted observation age of 0.5 s. The source reading from 2 s arrives at 2.6 s, already too old. Indeed, every reading is at least 0.6 s old when it becomes available. The prediction is a complete run with **no eligible reading**, a missed useful warning and error coverage zero; it is not a program crash or a measured RMSE of zero.

| Quantity | Clean prediction | 0.6 s latency prediction |
| --- | --- | --- |
| Independent contact | `sqrt(11)` s | Identical |
| First warning | 2.0 s | None |
| Useful matched lead | `sqrt(11)-2` s | Not available |
| Useful-event result | Useful | Missed useful warning |
| Cause to inspect | Gap/closing makes TTC 1.75 s | Arrival age exceeds 0.5 s limit |

With low latency 0.1 s, the same 2 s reading can first warn at its 2.1 s arrival, giving predicted lead `sqrt(11)-2.1 ≈ 1.2166247904 s`. The union-arrival clock includes that stored arrival time. This supplies a useful second boundary check. Keep exact inclusive availability comparisons on stored timestamps; never use a tolerance to admit a future observation early. Use a small explicit tolerance only when asserting independently calculated numerical answers such as the matched lead.

The 0.6 s profile is intentionally above the 0.5 s freshness policy, so this is a sensitivity example, not evidence that all practical latency is harmful or that an estimator will fix it. Increasing the age limit would admit data, but would also allow older gaps. That change needs its own controlled evaluation; it is not a free correction. Keep it out of the frozen baseline and consider it only as a later explicitly labelled comparison if the evidence supports that question.

Your investigation tasks:

1. Find the actual matrix row and inspect its truth, observations, decisions and metrics. If this exact result is absent, use your real result; the arithmetic above remains a regression fixture.
2. Make a short timeline table: decision time, source sample ID, measurement time, arrival time, age, measured gap/closing speed, TTC, warning and reason. Include the first clean warning and the corresponding delayed reading.
3. Check the reference event independently. Check whether the warning failure is due to the policy, replay timing, unavailable observations or the evaluator. A missing arrival must not be diagnosed by looking at a value that was never available.
4. Save a plot linking the warning/no-warning to timing and age. Inspect its labels and scales. Confirm truth hashes agree between clean and fault conditions.
5. Add a regression test asserting the mechanism: the delayed reading is unavailable before arrival, stale on arrival under this age limit and excluded from error coverage; the clean case retains the independently predicted warning/event values. Avoid asserting only a screenshot filename.
6. Write `docs/failure-study.md` when you later implement M4, linking the exact case ID/configuration and local evidence. This lesson does not create that file for you.

Use these paragraphs in your own technical explanation: **Question and frozen setup**; **Independent expected behaviour**; **Observed values with artifact locations**; **Diagnosis tied to specific trace rows**; **Regression check**; **Limits and the next question**. Populate the observed paragraph only from your run. If it was a bug, record before/after and rerun every original case after the fix. A fix that improves one case may change a negative episode elsewhere. Preserve both summaries and explain the change.

“Original” here means your investigation of your own constructed experiment with your own evidence and explanation. Cite outside ideas and AI assistance honestly. It does not mean inventing TTC or proving production ADAS safety.

## Block 6 — Pin what ran, then reproduce it in a fresh environment

Your outcome is an exact, reviewable environment description and an actual second run. A requirements file is an input. Successful reproduction is evidence obtained by using it. A virtual environment isolates Python packages but uses the installed base interpreter; it does not install a different Python version or establish a fresh-machine result. [Python venv documentation](https://docs.python.org/3.14/library/venv.html)

The preserved M1 reference records **CPython 3.14.7, Windows x64**, `requirements-m1-lock.txt` with exact wheel hashes and `docs/m1-dependencies.json` with license evidence. Those are historical inspected files, not a fresh M4 installation result. Recheck your actual environment and retain it; do not recreate `.venv` to hide problems.

```powershell
Set-Location 'E:\DriveCheck'
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip --version
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pip list --format=json
```

For the proposed release, keep using standard-library `unittest`. M2/M3 should not need a new dependency merely for JSON, random numbers or CLI parsing. If they did add packages for a justified reason, include their exact transitive dependencies, artifacts, compatibility and license information. Do not pretend the M1 lock covers them.

Create a release runtime lock from the actual runtime dependency set. If it is unchanged from M1, a proposed `requirements-lock.txt` can simply contain:

```text
# Windows x64 / CPython 3.14.7; runtime artifacts inherited from M1.
-r requirements-m1-lock.txt
```

This inclusion is valid only while the referenced file is retained and the dependency set is unchanged. Preserve/hash both. For linting, this lesson selects **Ruff 0.14.0** as a fixed teaching tool version, not as a claim that it is latest. Its published Windows x64 wheel and checksum are available; actual execution on your environment still needs to be checked. The published SHA-256 for `ruff-0.14.0-py3-none-win_amd64.whl` is `ea95da28cd874c4d9c922b39381cbd69cb7e7b49c21b8152b014bd4f52acddc2`. [Ruff 0.14.0 release artifacts](https://pypi.org/project/ruff/0.14.0/)

Proposed `requirements-ci-lock.txt`:

```text
-r requirements-lock.txt
ruff==0.14.0 --hash=sha256:ea95da28cd874c4d9c922b39381cbd69cb7e7b49c21b8152b014bd4f52acddc2
```

Keep tooling separate from runtime dependencies. Review the selected Ruff release's license files/metadata and extend the dependency notes when you install it. If a future change requires a newer linter, review its version and wheel hash explicitly rather than deleting hash checking. These artifact hashes are platform-specific. They do not establish Linux/macOS or Windows ARM support.

Install only when you reach this learner block:

```powershell
.\.venv\Scripts\python.exe -m pip install --only-binary=:all: --require-hashes -r .\requirements-ci-lock.txt --report .\outputs\m4-install-report.json
if ($LASTEXITCODE -ne 0) { throw 'Locked installation failed; inspect the error.' }
.\.venv\Scripts\python.exe -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Dependency consistency check failed.' }
```

Ensure `outputs/` exists before using `--report`. `--require-hashes` needs every resolved dependency pinned and hashed; `--only-binary=:all:` rejects source distributions instead of attempting an unplanned compiler build. A hash proves that the artifact matches the selected bytes; it does not establish that a dependency is defect-free. [pip secure installation guidance](https://pip.pypa.io/en/stable/topics/secure-installs/)

`pip freeze` alone does not supply artifact hashes, prove a clean install or select only project dependencies from an untidy environment. The installation report is supporting evidence, not a lock file that pip can install directly. [pip installation report format](https://pip.pypa.io/en/stable/reference/installation-report/)

If packages changed since M1, resolve in a new isolated environment under `outputs/` after checking supported Python/platform versions. Use `pip install --only-binary=:all: --report <local-file> <exact-reviewed-requirements>` there, inspect the report's names, versions, artifact URLs and SHA-256 values, and construct the full lock. The angle-bracket fields in this sentence are instructions for your reviewed package list, not a paste-ready command. Install that lock into a second fresh environment to validate it. Do not copy whatever happens to be installed globally.

### Reproduce from an explicit source snapshot

A second environment that accidentally imports code from your working folder can pass for the wrong reason. Use a small allowlisted source copy under `outputs/`, with a new environment, new output folder and no old artifacts. This does not need Git publication. Keep the original `.venv` and runs intact.

First finish the modules/tests in the other blocks and make sure these proposed paths exist. Adjust the explicit list for your actual test filenames; do not replace it with a whole-drive or whole-folder copy. Include every needed source/config/lock file, including the M3 catalog, while excluding `.private`, local secrets, environments and old generated runs.

```powershell
Set-Location 'E:\DriveCheck'
$m4ReproRoot = Join-Path (Get-Location) 'outputs\m4-repro-01'
if (Test-Path -LiteralPath $m4ReproRoot) {
    throw 'Choose a new reproduction directory; preserve the previous run.'
}
$m4ReproProject = Join-Path $m4ReproRoot 'project'
New-Item -ItemType Directory -Path $m4ReproProject | Out-Null

$m4Sources = @(
    'motion.py', 'scenarios.py', 'm1.py', 'faults.py', 'stop_and_go.py',
    'observations.py', 'replay.py',
    'warning_policy.py', 'evaluation.py', 'experiments.py',
    'reporting.py', 'drivecheck.py',
    'test_motion.py', 'test_m1.py', 'test_m2.py',
    'test_m3_faults.py', 'test_m3_scenarios.py',
    'test_m3_boundaries.py', 'test_m3_regression.py',
    'test_m4.py', 'test_m4_e2e.py',
    'requirements-m1-lock.txt', 'requirements-lock.txt',
    'requirements-ci-lock.txt', 'ruff.toml'
)
foreach ($m4Source in $m4Sources) {
    if (-not (Test-Path -LiteralPath $m4Source -PathType Leaf)) {
        throw "Required source missing: $m4Source"
    }
    Copy-Item -LiteralPath $m4Source -Destination $m4ReproProject
}
# Inspect configs/ first; it should contain only the project's small synthetic configs.
Copy-Item -LiteralPath '.\configs' -Destination $m4ReproProject -Recurse

py -3.14 -c "import sys; assert sys.version_info[:3] == (3, 14, 7), sys.version"
if ($LASTEXITCODE -ne 0) { throw 'Exact recorded Python version is unavailable.' }
py -3.14 -m venv (Join-Path $m4ReproProject '.venv')
if ($LASTEXITCODE -ne 0) { throw 'Fresh environment creation failed.' }
$m4ReproPython = Join-Path $m4ReproProject '.venv\Scripts\python.exe'

Push-Location $m4ReproProject
try {
    & $m4ReproPython -m pip install --only-binary=:all: --require-hashes -r .\requirements-ci-lock.txt
    if ($LASTEXITCODE -ne 0) { throw 'Fresh locked install failed.' }
    & $m4ReproPython -m pip check
    if ($LASTEXITCODE -ne 0) { throw 'Fresh dependency check failed.' }
    & $m4ReproPython -m ruff check .
    if ($LASTEXITCODE -ne 0) { throw 'Fresh lint failed.' }
    & $m4ReproPython -m unittest discover -v
    if ($LASTEXITCODE -ne 0) { throw 'Fresh tests failed.' }
    & $m4ReproPython .\drivecheck.py --config .\configs\m4-release.json --output-dir .\outputs\release
    if ($LASTEXITCODE -ne 0) { throw 'Fresh experiment/report failed.' }
}
finally {
    Pop-Location
}
```

These are future learner commands, not an observed clean run. If the source list is incomplete, the error is evidence to correct the documentation before claiming reproduction. Do not “fix” the source copy by importing modules from the original folder. Use a catalog made from configuration, not an ignored generated file outside the copy. Record the source hashes before/after copying; the snapshots used for comparison must match.

Compare the original complete run's deterministic `results.csv` with the fresh run:

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath .\outputs\m4-release-01\results.csv
Get-FileHash -Algorithm SHA256 -LiteralPath .\outputs\m4-repro-01\project\outputs\release\results.csv
```

Expected on the same pinned source/runtime/settings: equal case IDs, statuses, outcomes, counts and numeric results. If you chose stable field ordering/number formatting and excluded volatile fields, the CSV hashes should match. Compare semantic numeric values with a documented tight tolerance if serialization differs; explain exactly what differed instead of declaring “close enough”. PNG metadata, absolute paths or creation times need not be bit-identical; do not compare a whole manifest hash and call a timestamp difference a numerical failure.

Record actual commands, versions, install outcome, case completeness, comparison and visual offline report check in a proposed `docs/reproduction.md`. A successful same-machine clean-environment run is strong bounded evidence; it is not a tested second OS, fresh machine or remote CI. Setup may need network to obtain pinned wheels. Tests/replay/report should run offline once dependencies are installed.

**Debugging prompts:** “No matching distribution” can mean a mismatched Python/architecture/platform, not a reason to remove pins. A hash mismatch requires checking the selected artifact and lock provenance. A missing package in the fresh run often reveals an undeclared dependency. A result difference requires comparing source/config/RNG/runtime before changing the algorithm.

## Block 7 — Test the assembled product and prepare CI

Your outcome is a useful local release check and a workflow configuration that will run after you choose to publish. Continuous integration (CI) means a service executes checks for a particular code revision. A YAML file on your disk and a green local test suite are not an actual remote CI result.

Keep the M1–M3 tests. Add `test_m4.py` for configuration, expansion, seed adapter, summaries and failure accounting. Add `test_m4_e2e.py` for the command-to-artifact path. Do not invent a target test count or coverage percentage. A useful test fails when an important property breaks.

| Layer | Independent check to add |
| --- | --- |
| Enumeration | 60 distinct planned IDs, 30 positives/30 negatives; four-seed variant gives 76 |
| Fault adapter | Case 11 maps to seeds 44/45/46/47, correct M3 field names; deterministic placeholder changes have no observational effect |
| Scoring/summary | A–F: 5/6 evaluated; missed 1/3, late 1/3, without useful 2/3, false warnings 1/2; all status rows retained |
| Error alignment | Noise-free 1 s delay fixture: current gap RMSE 5 m and coverage 2/3 with age limit 1 s; measurement-time error zero |
| Metric support | Contact before horizon: MAE/RMSE retain separate intervals and eligible/total/missing/stale counts |
| Fault audit | One audit row per truth sample; dropped and retained-but-pending observations remain distinguishable |
| Empty denominators | No positives/negatives or no eligible estimates produces null plus support count, not a made-up zero |
| CLI | Help exits 0; invalid config/unknown flag exits 2 before output; incomplete execution exits nonzero |
| Execution failure | Inject one exception; all planned IDs remain, later cases run, failed case not assigned algorithm metrics |
| Report failure | Inject render error; machine-readable evidence survives and run is incomplete/nonzero |
| Artifact integrity | Reopen JSON/CSV; validate counts, IDs, numeric fields and relative local assets; reject NaN/Infinity |
| Repeatability | Fresh state/case order does not change case results; truth hashes unchanged by faults |

Preserve M2's previous schema/CLI behaviour or dispatch its schema through a normalizer into the new internal representation; do not silently invalidate its six-case reproduction command. `--output-dir` is the shared spelling. If M2 produced `cases.csv`, keep it for that schema or provide a documented identical alias; M4's proposed stable table is `results.csv`. Regression tests should tell you when a release refactor changes established behaviour.

### A small end-to-end fixture with known answers

Create proposed `configs/m4-smoke.json` by copying the M4 experiment schema, selecting just the two existing M1 braking fixtures and keeping only the clean and 0.6 s latency profiles. Set `scenario_catalog` to `configs/m1-fixtures.json`. Keep threshold 2 s, age 0.5 s, window 3 s and useful lead 0.5 s. Both profiles have `[null]` as the case-seed list, mapped to the explicit unused stream bundle. Keep original 1 s source sampling and the 0.1 s decision base grid.

Expected **four** case rows:

| Scenario/profile | Expected M2 outcome | First warning |
| --- | --- | ---: |
| braking contact / clean | `useful` | 2.0 s |
| braking contact / strong latency | `missed` | None |
| braking non-contact / clean | `false_warning` | 8.0 s |
| braking non-contact / strong latency | `clear_negative` | None |

The non-contact clean answer has an independent check: after stopping, the lead rear stays at 100 m; ego is at 80 m at the 8 s horizon. Gap is 20 m and closing speed is 10 m/s, giving TTC exactly 2 s at the inclusive threshold. At 7 s its gap is 30 m, giving 3 s; the held 7 s reading cannot warn under a 2 s threshold. Contact would occur at 10 s if the horizon were extended. This false-warning label is a finite-horizon convention, not evidence that a warning about an approaching stopped vehicle is irrational. Put this limitation beside the table.

The smoke summary is 2 evaluated positives, 2 evaluated negatives, useful 1, missed 1, late 0 and false-warning episodes 1/2. Earliest matched contact lead is `sqrt(11)-2`. Do not use these synthetic fixture expectations as the measured 60-case release results.

Here is a guided end-to-end test core. It exercises the real CLI using the active interpreter and reads the saved data. Expand it with CSV checks, offline asset validation and truth preservation. Adapt only the proposed artifact key names consistently with your documented output schema.

```python
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent


class TestReleaseCLI(unittest.TestCase):
    def test_four_case_smoke(self):
        (ROOT / "outputs").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as tmp:
            run_dir = Path(tmp) / "run"  # Must not exist before CLI preflight.
            completed = subprocess.run(
                [sys.executable, str(ROOT / "drivecheck.py"),
                 "--config", str(ROOT / "configs" / "m4-smoke.json"),
                 "--output-dir", str(run_dir)],
                cwd=ROOT, capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(
                completed.returncode, 0, completed.stdout + completed.stderr
            )
            manifest = json.loads((run_dir / "manifest.json").read_text("utf-8"))
            data = json.loads((run_dir / "results.json").read_text("utf-8"))
            self.assertEqual(manifest["status"], "complete")
            cases = data["cases"]
            self.assertEqual(len(cases), 4)
            self.assertEqual(len({row["case_id"] for row in cases}), 4)
            by_pair = {(row["scenario_id"], row["profile_id"]): row for row in cases}
            expected = {
                ("lead_braking_contact", "clean"): "useful",
                ("lead_braking_contact", "latency_strong"): "missed",
                ("lead_braking_noncontact", "clean"): "false_warning",
                ("lead_braking_noncontact", "latency_strong"): "clear_negative",
            }
            for pair, outcome in expected.items():
                self.assertEqual(by_pair[pair]["execution_status"], "complete")
                self.assertEqual(by_pair[pair]["outcome"], outcome)
            self.assertAlmostEqual(
                by_pair[("lead_braking_contact", "clean")]["matched_lead_s"],
                1.3166247903554, places=9,
            )
            self.assertTrue((run_dir / "report.html").is_file())
```

Do not stop at `report.html` existence. Read `results.csv` with `csv.DictReader`, assert four rows and the same IDs/outcomes as JSON. Parse the generated HTML with standard-library `html.parser.HTMLParser` or inspect its asset references: images/styles/scripts must be local and their resolved targets must remain inside the run folder and exist. Ordinary reference hyperlinks can point to primary-source websites; they should not be fetched merely by opening the report. Broken local images are a defect even when tests of the evaluator pass.

For the injected failure test, give `experiments.run` an optional `case_runner` callable, defaulting to `run_case`, or use `unittest.mock.patch` on that boundary. Raise only for one known case and delegate the others to the real runner. Verify exact failed ID, preserved error, nonzero/partial run, expected remaining cases and eligible summary denominators. Test the CLI's exit path too, using a controlled failure fixture or a mocked call to `main`; do not infer CLI behaviour only from the helper's return value.

### Add a small linter configuration

Proposed `ruff.toml`:

```toml
extend-exclude = ["outputs"]

[lint]
select = ["E4", "E7", "E9", "F"]
```

This small rule set checks problems such as undefined names, unused imports and syntax-related issues; it does not prove correct contact maths or causal evaluation. `ruff check` reports findings; do not add automatic fixes to CI. Read each finding and correct the source deliberately. [Ruff linter and rule selection](https://docs.astral.sh/ruff/linter/)

Run your local release check after installing the reviewed CI lock:

```powershell
Set-Location 'E:\DriveCheck'
.\.venv\Scripts\python.exe -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Dependency check failed.' }
.\.venv\Scripts\python.exe -m ruff check .
if ($LASTEXITCODE -ne 0) { throw 'Lint failed.' }
.\.venv\Scripts\python.exe -m unittest discover -v
if ($LASTEXITCODE -ne 0) { throw 'Tests failed.' }
.\.venv\Scripts\python.exe .\drivecheck.py --config .\configs\m4-release.json --output-dir .\outputs\m4-release-02
if ($LASTEXITCODE -ne 0) { throw 'Release run failed.' }
```

Use a fresh suffix if `m4-release-02` already exists. Record observed results only after these commands complete and you inspect the full table/report. The four-case smoke test is a fast regression; the full matrix is still needed for acceptance.

### Prepare a Windows CI workflow

Create proposed `.github/workflows/ci.yml` when you reach this learner block. GitHub supports Python setup and check commands in a workflow. The example deliberately selects Windows because the inspected runtime wheels are Windows-specific, and requests the recorded Python patch version rather than silently testing whichever Python is installed. Availability and success on the service remain unverified until your actual remote run. [GitHub Python CI guidance](https://docs.github.com/en/actions/tutorials/build-and-test-code/python)

```yaml
name: CPU checks

on:
  push:
  pull_request:
  workflow_dispatch:

permissions:
  contents: read

jobs:
  cpu:
    runs-on: windows-latest
    defaults:
      run:
        shell: pwsh
    steps:
      - uses: actions/checkout@v6
        with:
          persist-credentials: false
      - uses: actions/setup-python@v6
        with:
          python-version: '3.14.7'
          architecture: 'x64'
      - name: Display runtime
        run: python --version
      - name: Install reviewed dependencies
        run: python -m pip install --only-binary=:all: --require-hashes -r requirements-ci-lock.txt
      - name: Check dependencies
        run: python -m pip check
      - name: Lint
        run: python -m ruff check .
      - name: Unit and end-to-end tests
        run: python -m unittest discover -v
      - name: Complete configured CPU experiment
        run: python drivecheck.py --config configs/m4-release.json --output-dir outputs/ci-release
```

`checkout` retrieves the revision into the runner, and `setup-python` selects the requested interpreter. The selected v6 major references are examples supported by the official action repositories, not immutable action pins. Before publication you can replace each with its reviewed full commit SHA and keep the release/version comment. Do not invent a SHA. The `windows-latest` OS image also moves; this workflow does not promise a byte-identical entire machine. [actions/checkout](https://github.com/actions/checkout), [actions/setup-python](https://github.com/actions/setup-python)

Each step uses one native command so a failing exit is visible to the runner. No deployment, project upload or artifact-publishing step is required. Installation on the service may access package servers; the CPU experiment itself should not access the network. Do not add Linux to the matrix until its wheel lock/install is separately reviewed and reproduced.

Check the workflow indentation and names, then run the same install/lint/test/experiment commands locally, including the fresh-environment block. You may record “workflow configured and local equivalent checks passed” if that actually happened. Record **“remote CI pending user publication and an actual run”** until the service has run the selected revision. A workflow file cannot demonstrate runner availability, action compatibility or remote success by inspection alone. Remote CI being pending does not prevent the remaining local lessons.

### A bounded user-run Git practice block

Git is your decision and responsibility. If your repository is not initialized, learn initialization and the meaning of a local snapshot before remote publication; this lesson does not perform it. In an existing repository, these read-only commands help you inspect the proposed release:

```powershell
git status --short
git diff --stat
git diff -- .gitignore README.md
git status --short --untracked-files=all
```

`git diff` excludes untracked file contents, so open new source/config/lesson/workflow files explicitly. Check that `.private/`, `AGENTS.md`, `docs/progress.md`, environments, generated runs and local secrets stay ignored. You choose the specific files to stage; the index is the next commit's selected content, and the commit is a local snapshot. A push transfers your chosen commits to a remote and may trigger CI. Those are distinct actions, and none has happened because this lesson mentions them.

After you personally choose to stage a release, inspect `git diff --cached --name-only` and `git diff --cached` before your own commit/publication. There is no need to upload private teaching records or generated output folders to demonstrate reproducibility. A small curated synthetic fixture/table can be selected separately after review. Record an actual remote result only for the revision that was checked; a green run of an older commit does not verify later edits.

## Block 8 — Close M4 with evidence and hand off to C1

Your release is technically ready when the following statements are backed by your actual saved files/commands. Mark unchecked items pending; the list is not an assertion that they already happened.

- [ ] Both scenario families have complete configurations, independent contact/non-contact references and declared horizons.
- [ ] The frozen matrix expands to its declared 60 IDs, or a documented revised count, with no omitted failures or silent exclusions.
- [ ] Fault inputs, resolved M3 names, RNG/draw-order version and all four stream seeds are saved; truth is unchanged.
- [ ] Replay/warning are causal; missing, stale, non-closing and contact cases retain their explicit policies.
- [ ] Event categories preserve M2 semantics. Missed, late, without-useful and false-warning counts/rates have eligible denominators and execution coverage.
- [ ] Matched lead values include late matches and support counts; unmatched events stay visible. Current-time MAE/RMSE declare their interval, weighting, units and eligibility.
- [ ] One CLI command writes machine-readable results and an offline report; invalid input and incomplete execution have useful nonzero error behaviour.
- [ ] The report contains all case rows, inspected plots, effective settings, versions/hashes, limits and a real failure investigation with a regression check.
- [ ] Meaningful unit/integration/end-to-end checks and lint pass locally. The full matrix is run, not just the four-case smoke fixture.
- [ ] A new isolated environment/source snapshot reproduces the complete case results; actual commands and comparison are recorded.
- [ ] CI configuration and local equivalent checks are recorded accurately; the actual remote CI state is separately pending or linked to its real checked revision.

Then update the technical README/setup/failure-study/reproduction notes from what you actually observed, with your coach's help if useful. Do not turn this lesson's predictions into a results table. Record exact command summaries, source/config hashes, one report path, any unresolved issue and the next bounded question. Your coach can maintain the private progress/skill/checkpoint/handoff records from your supplied work; they should not infer mastery from generated tests or invent focused time.

Check your understanding through one small independent task: predict what changes if the useful-lead requirement rises from 0.5 s to 2 s while observations and warning decisions stay fixed. In A–E, A's 3 s lead stays useful, B stays late and C stays missed. A valid setting need not change an outcome. Add a separate positive fixture with contact at 5 s and one warning at 3.5 s: its 1.5 s lead changes from useful to late, while its decision trace stays identical. The missed-event rate does not change, but the fraction without a useful warning does. As a validation check, a 3.1 s requirement with a 3 s matching window must be rejected before a run.

Your C1 handoff should contain the frozen baseline config/result IDs, selected failure trace/plot and regression, exact reproducible environment, the unchanged warning/scoring contract and a clear new comparison question. Reserve separate development/tuning and final evaluation cases/seeds before choosing or tuning an alternative. C1 can compare one bounded method on the same causal streams and policy; it does not require a Kalman filter, a measured improvement or CARLA. A losing or mixed comparison can still be a sound investigation.

**Lesson completion:** this study material is ready to follow. **Learner/project completion:** implementation, observed runs, clean reproduction, explanation and remote CI evidence remain pending until you perform and review them. Git/publication choices remain entirely yours.
