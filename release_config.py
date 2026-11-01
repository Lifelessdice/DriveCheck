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
    "mode",
    "gap_sigma_m",
    "closing_sigma_mps",
    "latency_s",
    "latency_jitter_s",
    "dropout_probability",
}


def _keys(value, expected, label):
    """Require the exact supported fields."""
    if not isinstance(value, dict) or set(value) != set(expected):
        raise ValueError(f"invalid fields in {label}")


def _unique_keys(pairs):
    """Reject duplicate JSON keys instead of keeping the last value."""
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
            "lead_braking_contact",
            "lead_braking_noncontact",
        }:
            registry[fixture.scenario.scenario_id] = (
                "lead_braking",
                fixture,
            )

    for fixture in stop_go_fixtures():
        name = fixture.scenario.scenario_id

        if name in registry:
            raise ValueError(f"duplicate fixture ID: {name}")

        registry[name] = ("stop_and_go", fixture)

    expected = {
        "lead_braking_contact",
        "lead_braking_noncontact",
        "stop_and_go_contact",
        "stop_and_go_noncontact",
    }

    if set(registry) != expected:
        raise ValueError(
            "release fixture registry does not match the four accepted IDs"
        )

    return registry


def _fault_template(value, label):
    """Validate native fault settings before resolving stream seeds."""
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

    if any(
        isinstance(value, bool) or not isinstance(value, int) or value < 0
        for value in values
    ):
        raise ValueError(f"{label}: stochastic observations require integer bases >= 0")

    if len(set(values)) != len(values):
        raise ValueError(f"{label}: duplicate seed base")


def validate_configuration(config):
    """Return a validated copy without changing the caller's settings."""
    _keys(
        config,
        {
            "schema_version",
            "fixture_set",
            "scenario_ids",
            "conditions",
            "warning",
            "scoring",
            "decision_clock",
        },
        "configuration",
    )

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

    _keys(
        config["warning"],
        {"threshold_s", "max_age_s"},
        "warning",
    )

    validate_warning_settings(
        config["warning"]["threshold_s"],
        config["warning"]["max_age_s"],
    )

    _keys(
        config["scoring"],
        {
            "pre_event_window_s",
            "minimum_useful_lead_s",
        },
        "scoring",
    )

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

        _keys(
            condition,
            {"condition_id", "fault", "seed_bases"},
            label,
        )

        name = condition["condition_id"]

        if (
            not isinstance(name, str)
            or not name
            or any(character not in allowed for character in name)
        ):
            raise ValueError(
                f"{label}.condition_id must use " "lowercase letters, digits, _ or -"
            )

        if name in seen:
            raise ValueError(f"duplicate condition_id: {name}")

        seen.add(name)

        fault = _fault_template(
            condition["fault"],
            f"{label}.fault",
        )

        _check_seed_bases(
            condition["seed_bases"],
            fault,
            f"{label}.seed_bases",
        )

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
    # Deterministic placeholders match M3's existing default stream seeds.
    base = 100 if seed_base is None else seed_base

    return replace(
        template,
        gap_seed=base + 1,
        closing_seed=base + 2,
        latency_seed=base + 3,
        dropout_seed=base + 4,
    )


def build_plan(config):
    """Expand settings into pending rows without replay or output writes."""
    config = validate_configuration(config)
    registry = fixture_registry()

    policy = {
        "warning_threshold_s": config["warning"]["threshold_s"],
        "max_age_s": config["warning"]["max_age_s"],
        **config["scoring"],
        # Equivalent spelling used by the accepted M3 computation layer.
        "decision_clock": "source schedule plus in-horizon arrivals",
    }

    plan = []

    for scenario_id in config["scenario_ids"]:
        family, fixture = registry[scenario_id]
        scenario = fixture.scenario

        for condition in config["conditions"]:
            template = _fault_template(
                condition["fault"],
                "fault",
            )

            for seed_base in condition["seed_bases"]:
                fault = _resolved_fault(template, seed_base)

                plan.append(
                    {
                        "schema": "drivecheck.m4.case.v1",
                        "section": "matrix",
                        "case_id": f"case-{len(plan) + 1:03d}",
                        "condition_id": condition["condition_id"],
                        "scenario_id": scenario_id,
                        "family": family,
                        "status": "pending",
                        "seed_base": seed_base,
                        "stream_mapping": STREAM_MAPPING,
                        "seed_role": (
                            "stochastic"
                            if seed_base is not None
                            else "unused placeholders"
                        ),
                        "horizon_s": scenario.horizon_s,
                        "reference_contact_time_s": (fixture.reference_contact_time_s),
                        "reference_final_gap_m": (fixture.reference_final_gap_m),
                        "reference_basis": fixture.reference_basis,
                        "configuration": asdict(scenario),
                        "fault": asdict(fault),
                        "policy": dict(policy),
                        "score": None,
                        "errors": None,
                        "counts": None,
                        "error": None,
                    }
                )

    return plan


def describe_plan(plan):
    """Report inventory counts without inferring algorithm results."""
    positives = sum(row["reference_contact_time_s"] is not None for row in plan)

    return {
        "expected_case_count": len(plan),
        "positive_case_count": positives,
        "negative_case_count": len(plan) - positives,
        "case_count_by_condition": dict(
            sorted(Counter(row["condition_id"] for row in plan).items())
        ),
    }
