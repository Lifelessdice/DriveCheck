# M4 block 1 — Freeze the release configuration and enumerate the cases

Prepared 1 November 2026 against the actual M3 implementation at `3ebd668`. **This is learner implementation material.** The code/configuration/tests below are supplied for you to save and run; the lesson author has not installed packages, written these product files or executed them.

The assistant created and switched to `feature/m4-reproducible-release` at your explicit request. It starts at the integrated M3 commit. Existing untracked editor/practice files were preserved. Keep this branch throughout M4; staging, commits, pushes and the final merge remain your actions unless explicitly delegated.

Observed acceptance, 1 November 2026: the learner saved the three supplied files. Assistant review found no required source fix; 14 focused tests passed in 0.057 s and the full 145-test suite passed in 25.752 s, both exit 0. These are test durations, not learner focused time. The assistant explicitly pushed the existing branch and verified its remote ref at `3ebd668`; the new files remain uncommitted. [Block 2 is supplied for learner implementation](m4-block2-machine-results.md), not an executed release.

## What this block achieves

M3 has a working study with 28 main cases and five separate latency diagnostics. M4 makes that work configurable, reproducible from a fresh environment and ready for a reader to inspect. We will reuse the accepted physics, faults, causal replay, scorer and MAE definitions. We do not need another warning algorithm.

This first block creates only a **validated experiment specification and a complete pending case plan**. It does not execute the experiments or render another report. That separation lets us find a missing case, misspelled setting or wrong seed before producing misleading results.

Create these three files yourself:

| File | Purpose |
| --- | --- |
| `configs/m4-release.json` | The selected fixtures, explicit fault magnitudes, stream seed bases and frozen policy |
| `release_config.py` | Strict loading/validation and expansion into fully resolved pending cases |
| `test_m4_config.py` | Independent inventory, mapping, validation and non-mutation checks |

Leave `experiments.py`, `drivecheck.py`, the existing tests and the M3 study intact for now. Later blocks connect the release plan to the accepted computation/report functions and preserve the M2 CLI schema. Installing anything is unnecessary for this block.

## The theory: a case is one fully specified question

A scenario describes the clean world. A fault profile describes how observations differ from that world. A seed base selects the four private pseudo-random streams. One combination is an evaluated episode once it actually runs.

Your accepted main policy stays:

- TTC threshold 3 s; maximum measurement age 1.25 s, inclusive.
- Pre-event matching window 4 s; minimum useful lead 1 s.
- Decision times are the source schedule plus observation arrivals within the horizon.
- Offline errors are full-horizon, fresh-decision-row-weighted MAEs. Missing/stale rows are excluded with their counts visible; virtual post-contact rows remain included under that existing definition.

Changing the decision clock or excluding post-contact rows would change the quantity being measured. We retain these definitions rather than quietly changing them during release work. Additional diagnostics can be introduced later with separate labels/support counts.

### Why this matrix has 76 main cases

Preserve M3's four actual IDs: `lead_braking_contact`, `lead_braking_noncontact`, `stop_and_go_contact`, `stop_and_go_noncontact`.

| Profile | Accepted M3 magnitudes | Repetitions per scenario |
| --- | --- | ---: |
| clean | All fault magnitudes zero | 1 |
| noise_low | Gap sigma 0.2 m; closing-speed sigma 0.1 m/s | 3 seed bases |
| noise_strong | Gap sigma 1.0 m; closing-speed sigma 0.5 m/s | 3 seed bases |
| latency_low | `0.25 + 0.1*u` seconds, `0 <= u < 1` | 3 seed bases |
| latency_strong | `0.5 + 1.5*u` seconds | 3 seed bases |
| dropout_low | Per-source-sample dropout probability 0.1 | 3 seed bases |
| dropout_strong | Dropout probability 0.4 | 3 seed bases |

Both latency profiles contain **random jitter**. Treating them as deterministic would undercount the selected replications. Use bases **100, 200, 300**, chosen before seeing their release results. Each scenario has `1 + 6*3 = 19` cases; four scenarios give **76**. Two contact scenarios give **38 positive episodes**; two non-contact scenarios give **38 negative episodes**. Clean contributes four cases; each other profile contributes twelve, split six positive/six negative.

These are planned counts, not measured outcomes or 76 independent traffic worlds. Conditions share truth, and profiles intentionally reuse corresponding streams. Show per-condition/per-seed results later. Do not pool all rows as independent evidence of real-world performance.

M3's five fixed-delay diagnostics have different policy/clock settings. Preserve their tests/evidence, and keep their report section separate when carrying them into the release. If all five are also stored, that is 81 stored rows comprising **76 matrix + 5 diagnostic**, not one scientific denominator of 81. This block enumerates only the 76 main cases.

### The seed base is a mapping, not the entire configuration

Keep M3's exact mapping: base 100 gives gap/closing/latency/dropout seeds **101/102/103/104**. Bases 200 and 300 give **201–204** and **301–304**. The four generators retain separate state and M3's fixed per-source draw order. Do not replace this with the older lesson's `4*seed` mapping.

Clean has `seed_base: null` because no random magnitude affects its observations. `FaultConfig` still needs integer stream seeds, so store its existing **101/102/103/104** defaults as explicitly unused placeholders. Drawing values for an audit does not make clean observations stochastic when all their coefficients are zero. Fixed latency without jitter, zero-noise settings, and dropout probability 0 or 1 are also deterministic in their observational effect.

## 1. Save the frozen configuration

Create `configs/m4-release.json`:

```json
{
  "schema_version": "drivecheck.m4.v1",
  "fixture_set": "m1_braking_and_m3_stop_go",
  "scenario_ids": [
    "lead_braking_contact",
    "lead_braking_noncontact",
    "stop_and_go_contact",
    "stop_and_go_noncontact"
  ],
  "conditions": [
    {
      "condition_id": "clean",
      "fault": {"mode": "clean"},
      "seed_bases": [null]
    },
    {
      "condition_id": "noise_low",
      "fault": {"mode": "noise", "gap_sigma_m": 0.2, "closing_sigma_mps": 0.1},
      "seed_bases": [100, 200, 300]
    },
    {
      "condition_id": "noise_strong",
      "fault": {"mode": "noise", "gap_sigma_m": 1.0, "closing_sigma_mps": 0.5},
      "seed_bases": [100, 200, 300]
    },
    {
      "condition_id": "latency_low",
      "fault": {"mode": "latency", "latency_s": 0.25, "latency_jitter_s": 0.1},
      "seed_bases": [100, 200, 300]
    },
    {
      "condition_id": "latency_strong",
      "fault": {"mode": "latency", "latency_s": 0.5, "latency_jitter_s": 1.5},
      "seed_bases": [100, 200, 300]
    },
    {
      "condition_id": "dropout_low",
      "fault": {"mode": "dropout", "dropout_probability": 0.1},
      "seed_bases": [100, 200, 300]
    },
    {
      "condition_id": "dropout_strong",
      "fault": {"mode": "dropout", "dropout_probability": 0.4},
      "seed_bases": [100, 200, 300]
    }
  ],
  "warning": {"threshold_s": 3.0, "max_age_s": 1.25},
  "scoring": {"pre_event_window_s": 4.0, "minimum_useful_lead_s": 1.0},
  "decision_clock": "sample_times_union_arrivals_within_horizon"
}
```

The fixture definitions remain in your tested `m1_fixtures()` and `stop_go_fixtures()`. Their complete parameters and independent references are copied into each resolved plan row. A new JSON trajectory catalog would duplicate existing accepted data and is unnecessary here.

## 2. Implement strict configuration and plan expansion

Create `release_config.py` with the following teaching implementation. Read the function explanations below before running it:

```python
"""Validate M4 release settings and enumerate pending main-matrix cases."""

from collections import Counter
from copy import deepcopy
from dataclasses import asdict, replace
import json
from pathlib import Path

from faults import FaultConfig
from motion import require_finite
from scenarios import m1_fixtures
from stop_and_go import stop_go_fixtures
from warning_policy import validate_warning_settings

ROOT = Path(__file__).resolve().parent
SCHEMA = "drivecheck.m4.v1"
CLOCK = "sample_times_union_arrivals_within_horizon"
FIXTURE_SET = "m1_braking_and_m3_stop_go"
STREAM_MAPPING = "m3.seed-base-plus-1-to-4.v1"
FAULT_FIELDS = {
    "mode", "gap_sigma_m", "closing_sigma_mps", "latency_s",
    "latency_jitter_s", "dropout_probability",
}


def _keys(value, expected, label):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise ValueError(f"invalid fields in {label}")


def _unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError(f"nonstandard JSON number: {value}")


def fixture_registry():
    """Resolve the four accepted fixture IDs without executing a study."""
    registry = {}
    for fixture in m1_fixtures():
        if fixture.scenario.scenario_id in {
            "lead_braking_contact", "lead_braking_noncontact",
        }:
            registry[fixture.scenario.scenario_id] = ("lead_braking", fixture)
    for fixture in stop_go_fixtures():
        name = fixture.scenario.scenario_id
        if name in registry:
            raise ValueError(f"duplicate fixture ID: {name}")
        registry[name] = ("stop_and_go", fixture)
    expected = {
        "lead_braking_contact", "lead_braking_noncontact",
        "stop_and_go_contact", "stop_and_go_noncontact",
    }
    if set(registry) != expected:
        raise ValueError("release fixture registry does not match the four accepted IDs")
    return registry


def _fault_template(value, label):
    if (
        not isinstance(value, dict)
        or "mode" not in value
        or not set(value).issubset(FAULT_FIELDS)
    ):
        raise ValueError(f"invalid fault fields in {label}")
    try:
        return FaultConfig(**value)
    except ValueError as error:
        raise ValueError(f"{label}: {error}") from error


def is_stochastic(fault):
    """Whether generated observations can depend on the random draws."""
    return (
        fault.gap_sigma_m > 0
        or fault.closing_sigma_mps > 0
        or fault.latency_jitter_s > 0
        or 0 < fault.dropout_probability < 1
    )


def _check_seed_bases(values, fault, label):
    if not isinstance(values, list) or not values:
        raise ValueError(f"{label} must be a nonempty list")
    if not is_stochastic(fault):
        if values != [None]:
            raise ValueError(f"{label}: deterministic observations require [null]")
        return
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 0
           for value in values):
        raise ValueError(f"{label}: stochastic observations require integer bases >= 0")
    if len(set(values)) != len(values):
        raise ValueError(f"{label}: duplicate seed base")


def validate_configuration(config):
    """Return an independent validated copy; never change the caller's settings."""
    _keys(config, {
        "schema_version", "fixture_set", "scenario_ids", "conditions",
        "warning", "scoring", "decision_clock",
    }, "configuration")
    if config["schema_version"] != SCHEMA:
        raise ValueError("unsupported release schema")
    if config["fixture_set"] != FIXTURE_SET:
        raise ValueError("unsupported release fixture_set")
    if config["decision_clock"] != CLOCK:
        raise ValueError("unsupported release decision_clock")

    registry = fixture_registry()
    identifiers = config["scenario_ids"]
    if not isinstance(identifiers, list) or not identifiers:
        raise ValueError("scenario_ids must be a nonempty list")
    if any(not isinstance(name, str) or name not in registry for name in identifiers):
        raise ValueError("unknown release scenario_id")
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("duplicate scenario_id")

    _keys(config["warning"], {"threshold_s", "max_age_s"}, "warning")
    validate_warning_settings(
        config["warning"]["threshold_s"], config["warning"]["max_age_s"],
    )
    _keys(config["scoring"], {
        "pre_event_window_s", "minimum_useful_lead_s",
    }, "scoring")
    window = config["scoring"]["pre_event_window_s"]
    useful = config["scoring"]["minimum_useful_lead_s"]
    require_finite("pre_event_window_s", window, positive=True)
    require_finite("minimum_useful_lead_s", useful, positive=True)
    if useful > window:
        raise ValueError("minimum useful lead exceeds matching window")

    conditions = config["conditions"]
    if not isinstance(conditions, list) or not conditions:
        raise ValueError("conditions must be a nonempty list")
    seen = set()
    allowed = "abcdefghijklmnopqrstuvwxyz0123456789_-"
    for index, condition in enumerate(conditions):
        label = f"conditions[{index}]"
        _keys(condition, {"condition_id", "fault", "seed_bases"}, label)
        name = condition["condition_id"]
        if (not isinstance(name, str) or not name
                or any(character not in allowed for character in name)):
            raise ValueError(f"{label}.condition_id must use lowercase letters, digits, _ or -")
        if name in seen:
            raise ValueError(f"duplicate condition_id: {name}")
        seen.add(name)
        fault = _fault_template(condition["fault"], f"{label}.fault")
        _check_seed_bases(condition["seed_bases"], fault, f"{label}.seed_bases")
    return deepcopy(config)


def load_configuration(path):
    """Load project-contained JSON with strict key and numeric handling."""
    path = Path(path)
    path = (path if path.is_absolute() else ROOT / path).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError("configuration path must remain inside the project")
    config = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_unique_keys,
        parse_constant=_reject_constant,
    )
    return validate_configuration(config)


def _resolved_fault(template, seed_base):
    # The clean/deterministic stream placeholders match M3's existing defaults.
    base = 100 if seed_base is None else seed_base
    return replace(
        template, gap_seed=base + 1, closing_seed=base + 2,
        latency_seed=base + 3, dropout_seed=base + 4,
    )


def build_plan(config):
    """Expand settings into complete pending rows without replay or output writes."""
    config = validate_configuration(config)
    registry = fixture_registry()
    policy = {
        "warning_threshold_s": config["warning"]["threshold_s"],
        "max_age_s": config["warning"]["max_age_s"],
        **config["scoring"],
        # Equivalent clock spelling used by the accepted M3 computation layer.
        "decision_clock": "source schedule plus in-horizon arrivals",
    }
    plan = []
    for scenario_id in config["scenario_ids"]:
        family, fixture = registry[scenario_id]
        scenario = fixture.scenario
        for condition in config["conditions"]:
            template = _fault_template(condition["fault"], "fault")
            for seed_base in condition["seed_bases"]:
                fault = _resolved_fault(template, seed_base)
                plan.append({
                    "schema": "drivecheck.m4.case.v1",
                    "section": "matrix",
                    "case_id": f"case-{len(plan) + 1:03d}",
                    "condition_id": condition["condition_id"],
                    "scenario_id": scenario_id,
                    "family": family,
                    "status": "pending",
                    "seed_base": seed_base,
                    "stream_mapping": STREAM_MAPPING,
                    "seed_role": "stochastic" if seed_base is not None else "unused placeholders",
                    "horizon_s": scenario.horizon_s,
                    "reference_contact_time_s": fixture.reference_contact_time_s,
                    "reference_final_gap_m": fixture.reference_final_gap_m,
                    "reference_basis": fixture.reference_basis,
                    "configuration": asdict(scenario),
                    "fault": asdict(fault),
                    "policy": dict(policy),
                    "score": None,
                    "errors": None,
                    "counts": None,
                    "error": None,
                })
    return plan


def describe_plan(plan):
    """Report inventory counts; no algorithm result is inferred from a plan."""
    positives = sum(row["reference_contact_time_s"] is not None for row in plan)
    return {
        "expected_case_count": len(plan),
        "positive_case_count": positives,
        "negative_case_count": len(plan) - positives,
        "case_count_by_condition": dict(sorted(Counter(
            row["condition_id"] for row in plan
        ).items())),
    }
```

### Read the implementation as a pipeline

`load_configuration` reads bytes and rejects ambiguous duplicate JSON keys and nonstandard numbers. `validate_configuration` checks the shape, semantics and native `FaultConfig` rules before returning a copy. `build_plan` resolves every selected scenario/profile/base combination and records complete settings. `describe_plan` counts inventory only.

Use `is not None` for the reference event: a contact at time zero is still positive. A truth test such as `if event_time` would wrongly call it negative. Boolean seeds are rejected because Python otherwise treats `True` as an integer. An unknown numeric setting is an error rather than silently falling back to a default.

Scenario IDs select the accepted source definitions. `fixture_registry` intentionally does not call `m3_study.prepare()`: that function also computes a diagnostic case, whereas this block should not run an experiment while planning one. In the execution block, we will bind the correct continuous evaluator, independently check references and freeze truth, using M3's existing context/computation boundary.

Sequential case IDs are unique within the saved plan and make safe local directory names. Their meaning is scoped by the full configuration/plan, so record the scenario, condition and base in every row rather than treating `case-010` alone as a global scientific identifier.

## 3. Add the independent plan checks

Create `test_m4_config.py`:

```python
"""Independent inventory and configuration guards for the release plan."""

from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
import tempfile
import unittest

from faults import FaultConfig
from release_config import (
    ROOT, build_plan, describe_plan, fixture_registry,
    is_stochastic, load_configuration, validate_configuration,
)


class TestReleaseConfiguration(unittest.TestCase):
    def setUp(self):
        self.config = load_configuration("configs/m4-release.json")

    def test_declared_inventory_has_76_unique_pending_cases(self):
        plan = build_plan(self.config)
        self.assertEqual(len(plan), 76)
        self.assertEqual(len({row["case_id"] for row in plan}), 76)
        self.assertEqual({row["status"] for row in plan}, {"pending"})
        self.assertTrue(all(row["score"] is None for row in plan))
        self.assertTrue(all(row["errors"] is None for row in plan))
        summary = describe_plan(plan)
        self.assertEqual(summary["positive_case_count"], 38)
        self.assertEqual(summary["negative_case_count"], 38)
        self.assertEqual(summary["case_count_by_condition"], {
            "clean": 4, "dropout_low": 12, "dropout_strong": 12,
            "latency_low": 12, "latency_strong": 12,
            "noise_low": 12, "noise_strong": 12,
        })

    def test_every_scenario_has_19_cases(self):
        plan = build_plan(self.config)
        for name in fixture_registry():
            with self.subTest(scenario_id=name):
                self.assertEqual(sum(row["scenario_id"] == name for row in plan), 19)

    def test_native_stream_mapping_and_deterministic_placeholders(self):
        plan = build_plan(self.config)
        for base, expected in ((100, (101, 102, 103, 104)),
                               (200, (201, 202, 203, 204)),
                               (300, (301, 302, 303, 304))):
            row = next(row for row in plan if row["seed_base"] == base)
            fault = row["fault"]
            self.assertEqual(tuple(fault[name] for name in (
                "gap_seed", "closing_seed", "latency_seed", "dropout_seed",
            )), expected)
        clean = [row for row in plan if row["condition_id"] == "clean"]
        self.assertEqual(len(clean), 4)
        self.assertTrue(all(row["seed_base"] is None for row in clean))
        self.assertTrue(all(row["fault"] == asdict(FaultConfig()) for row in clean))

    def test_m3_policy_parameters_are_preserved(self):
        for row in build_plan(self.config):
            self.assertEqual(row["policy"], {
                "warning_threshold_s": 3.0, "max_age_s": 1.25,
                "pre_event_window_s": 4.0, "minimum_useful_lead_s": 1.0,
                "decision_clock": "source schedule plus in-horizon arrivals",
            })

    def test_jitter_makes_latency_stochastic(self):
        self.assertFalse(is_stochastic(FaultConfig(mode="latency", latency_s=0.5)))
        self.assertTrue(is_stochastic(FaultConfig(
            mode="latency", latency_s=0.5, latency_jitter_s=1.5,
        )))
        self.assertFalse(is_stochastic(FaultConfig(
            mode="dropout", dropout_probability=1.0,
        )))

    def test_literal_reference_answers_are_retained(self):
        plan = build_plan(self.config)
        answers = {
            "lead_braking_contact": (3.3166247903554, -32.5, 5),
            "lead_braking_noncontact": (None, 20.0, 8),
            "stop_and_go_contact": (5.0, 2.0, 8),
            "stop_and_go_noncontact": (None, 5.0, 8),
        }
        for name, expected in answers.items():
            row = next(row for row in plan if row["scenario_id"] == name)
            self.assertEqual((row["reference_contact_time_s"],
                              row["reference_final_gap_m"], row["horizon_s"]), expected)

    def test_input_and_plan_rows_do_not_share_mutable_state(self):
        before = deepcopy(self.config)
        plan = build_plan(self.config)
        plan[0]["policy"]["max_age_s"] = 99
        plan[0]["configuration"]["initial_gap_m"] = 999
        plan[0]["fault"]["gap_seed"] = 999
        self.assertEqual(self.config, before)
        self.assertEqual(plan[1]["policy"]["max_age_s"], 1.25)
        self.assertEqual(plan[1]["configuration"]["initial_gap_m"], 30)
        self.assertEqual(plan[1]["fault"]["gap_seed"], 101)

    def test_four_seed_bases_give_100_cases(self):
        config = deepcopy(self.config)
        for condition in config["conditions"]:
            if condition["condition_id"] != "clean":
                condition["seed_bases"].append(400)
        # Four scenarios times (one clean plus six profiles times four bases).
        self.assertEqual(len(build_plan(config)), 100)

    def test_invalid_ids_and_empty_selections_are_rejected(self):
        for names in ([], ["unknown"], ["lead_braking_contact"] * 2, [True]):
            config = deepcopy(self.config)
            config["scenario_ids"] = names
            with self.subTest(names=names), self.assertRaises(ValueError):
                validate_configuration(config)
        for conditions in ([], [self.config["conditions"][0]] * 2):
            config = deepcopy(self.config)
            config["conditions"] = conditions
            with self.assertRaises(ValueError):
                validate_configuration(config)

    def test_unknown_fields_and_unsupported_versions_are_rejected(self):
        for field, value in (("schema_version", "drivecheck.m4.v999"),
                             ("fixture_set", "unknown"),
                             ("decision_clock", "fixed_0p1s"),
                             ("unexpected", 1)):
            config = deepcopy(self.config)
            config[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_configuration(config)
        config = deepcopy(self.config)
        config["conditions"][1]["fault"]["gap_std_m"] = 0.2
        with self.assertRaises(ValueError):
            validate_configuration(config)

    def test_invalid_seed_contracts_are_rejected(self):
        for bases in ([], [None], [True], [-1], [1.5], [100, 100]):
            config = deepcopy(self.config)
            config["conditions"][1]["seed_bases"] = bases
            with self.subTest(bases=bases), self.assertRaises(ValueError):
                validate_configuration(config)
        config = deepcopy(self.config)
        config["conditions"][0]["seed_bases"] = [100]
        with self.assertRaises(ValueError):
            validate_configuration(config)

    def test_invalid_faults_and_policy_are_rejected(self):
        faults = (
            {"mode": "noise", "gap_sigma_m": -0.2},
            {"mode": "noise", "gap_sigma_m": float("nan")},
            {"mode": "noise", "gap_sigma_m": 0.2, "latency_s": 1.0},
            {"mode": "noise", "gap_sigma_m": 0.2, "gap_seed": 101},
            {"mode": "dropout", "dropout_probability": 1.2},
        )
        for fault in faults:
            config = deepcopy(self.config)
            config["conditions"][1]["fault"] = fault
            with self.subTest(fault=fault), self.assertRaises(ValueError):
                validate_configuration(config)
        config = deepcopy(self.config)
        config["scoring"]["minimum_useful_lead_s"] = 5
        with self.assertRaises(ValueError):
            validate_configuration(config)
        config = deepcopy(self.config)
        config["warning"]["threshold_s"] = float("inf")
        with self.assertRaises(ValueError):
            validate_configuration(config)

    def test_json_loader_rejects_duplicate_and_nonstandard_numbers(self):
        (ROOT / "outputs").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            path = Path(directory) / "invalid.json"
            path.write_text('{"schema_version": 1, "schema_version": 2}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
                load_configuration(path)
            path.write_text('{"value": NaN}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "nonstandard JSON number"):
                load_configuration(path)
            overflow = deepcopy(self.config)
            overflow["warning"]["threshold_s"] = "__overflow__"
            text = json.dumps(overflow).replace('"__overflow__"', '1e400')
            path.write_text(text, encoding="utf-8")
            with self.assertRaises(ValueError):
                load_configuration(path)

    def test_plan_is_repeatable_and_contains_no_diagnostic_rows(self):
        first = build_plan(self.config)
        self.assertEqual(first, build_plan(self.config))
        self.assertEqual({row["section"] for row in first}, {"matrix"})


if __name__ == "__main__":
    unittest.main()
```

These tests do not ask whether another seed must change a warning. A configuration/plan test cannot establish a warning result. It checks the inventory, native mapping and validation boundaries before the execution layer is connected.

## 4. Run and inspect the block

After saving all three files, run these commands yourself from PowerShell:

```powershell
Set-Location 'E:\DriveCheck'
git branch --show-current
.\.venv\Scripts\python.exe -m unittest -v test_m4_config
.\.venv\Scripts\python.exe -m unittest -v
.\.venv\Scripts\python.exe -c "import json; from release_config import load_configuration, build_plan, describe_plan; print(json.dumps(describe_plan(build_plan(load_configuration('configs/m4-release.json'))), indent=2))"
```

Expected branch: `feature/m4-reproducible-release`. The focused and full suites should finish with `OK`; that remains an expectation until your run is reviewed. The previously accepted full suite had 131 tests. Do not replace that evidence with an unrun new total.

Expected inventory output, independently counted above:

```json
{
  "expected_case_count": 76,
  "positive_case_count": 38,
  "negative_case_count": 38,
  "case_count_by_condition": {
    "clean": 4,
    "dropout_low": 12,
    "dropout_strong": 12,
    "latency_low": 12,
    "latency_strong": 12,
    "noise_low": 12,
    "noise_strong": 12
  }
}
```

Inspect one resolved row without running any case:

```powershell
.\.venv\Scripts\python.exe -c "import json; from release_config import load_configuration, build_plan; plan=build_plan(load_configuration('configs/m4-release.json')); print(json.dumps(plan[1], indent=2))"
```

The second row should be the braking-contact `noise_low` case with base 100, stream seeds 101–104, horizon 5 s, contact reference approximately 3.3166247903554 s and status `pending`. Its `score`, `errors` and `counts` are null. Numeric reference values describe independent fixture expectations; they are not observations from a new replay.

Do not pass the M4 config to `drivecheck.py` yet: its current loader deliberately supports M2 only. That dispatch is a later block, rather than a reason to replace the accepted M2 runner now.

## 5. A meaningful change and common faults

Before looking at the included four-base test, predict the inventory if every stochastic condition adds base 400. It becomes `4 * (1 + 6*4) = 100`, split 50 positive/50 negative. Clean stays four cases. Make this change only in a copy or the test's in-memory object; preserve the frozen default file.

Explain why the two latency profiles need seed repetitions while a separate fixed-latency diagnostic does not. Then explain why the final gap of `stop_and_go_contact` can be positive even though its reference contact is 5 s: prescribed paths overlap and later separate, without impact dynamics. These explanations support learning review but are not reply gates.

| Symptom | What to inspect |
| --- | --- |
| 60 cases | Jittered latency was incorrectly treated as deterministic |
| 84 cases | Clean was repeated for all three bases |
| 76 complete cases before running anything | Planning status was confused with execution status |
| Unknown stop-go ID | Actual IDs contain `stop_and_go`, not the old proposed `stop_go` alias |
| A new base changes clean output | Nonzero fault magnitude or accidental dependency on audit draws |
| Gap and closing streams get the same seed | Preserve base + 1 versus base + 2 |
| JSON setting is ignored | Unknown-key rejection is missing or validation was bypassed |
| Existing M2 tests break | A tested runner/policy was changed even though this block only adds planning |

## Completion and next checkpoint

This block is ready for review when the three saved files match their responsibilities, the pending plan has the expected inventory/full resolved settings, focused/full tests actually pass and you can explain one seed/count decision. Keep the original M3 reports. No new release experiment, clean-environment reproduction, CI success or independent mastery is claimed by plan tests.

After review, the core learner-run checkpoint for these three files will be:

```powershell
git add -- release_config.py test_m4_config.py configs/m4-release.json
git diff --cached --stat
git diff --cached
git commit -m "Add validated M4 release configuration and case plan"
git push -u origin feature/m4-reproducible-release
```

Run that checkpoint after your work is verified and the reviewed public documentation list is finalized; the coach may add the exact reviewed lesson/README/research paths to the list then. Do not stage unrelated editor/practice/generated/private paths. The assistant has not staged, committed or pushed this block.

Next comes the execution adapter: independently validate/freeze the selected truth, reuse M3 computation, retain audit/observation/decision traces and all failures, and keep the five timing diagnostics separate. CLI/report integration, the evidence-backed failure write-up, pinned installation/actual clean reproduction and CI checks follow. M4 remains in progress until those have real evidence.
