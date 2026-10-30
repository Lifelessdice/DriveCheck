"""Offline warning scoring against independent, horizon-bounded contacts."""

import math
from motion import require_finite
from warning_policy import Decision

POSITIVE_OUTCOMES = ("useful", "late", "missed")
NEGATIVE_OUTCOMES = ("false_warning", "clear_negative")
STATUSES = ("complete", "failed", "partial", "pending")


def _check_reference(reference_contact_time_s, horizon_s):
    """Validate the horizon and optional contact; None means no contact."""

    require_finite("horizon_s", horizon_s, minimum=0)

    if reference_contact_time_s is not None:
        require_finite("reference_contact_time_s", reference_contact_time_s, minimum=0)

        # Only a numeric contact time can be compared with the horizon.
        if reference_contact_time_s > horizon_s:
            raise ValueError("reference contact exceeds horizon_s")


def _check_policy(pre_event_window_s, minimum_useful_lead_s):
    """Require a positive matching window and useful-lead minimum."""

    require_finite(
        "pre_event_window_s",
        pre_event_window_s,
        positive=True,
    )
    require_finite(
        "minimum_useful_lead_s",
        minimum_useful_lead_s,
        positive=True,
    )

    if minimum_useful_lead_s > pre_event_window_s:
        raise ValueError("minimum useful lead exceeds matching window")


def score_case(
    decisions,
    reference_contact_time_s,
    horizon_s,
    pre_event_window_s=4.0,
    minimum_useful_lead_s=1.0,
):
    """Score decision timestamps without recalculating the warning policy."""

    _check_reference(reference_contact_time_s, horizon_s)
    _check_policy(pre_event_window_s, minimum_useful_lead_s)

    timeline = list(decisions)
    previous_time_s = None

    for decision in timeline:
        if not isinstance(decision, Decision):
            raise ValueError("every decision must be a Decision")

        time_s = decision.decision_time_s
        require_finite("decision_time_s", time_s, minimum=0)

        if time_s > horizon_s:
            raise ValueError("decision exceeds horizon_s")

        if previous_time_s is not None and time_s <= previous_time_s:
            raise ValueError("decision times must strictly increase")

        # Do not coerce numeric values such as 1 into valid warning flags.
        if type(decision.is_warning) is not bool:
            raise ValueError("is_warning must be a boolean")

        previous_time_s = time_s

    warning_times = [
        decision.decision_time_s for decision in timeline if decision.is_warning
    ]

    # Consecutive true decisions belong to one warning activation.
    activation_count = sum(
        decision.is_warning and (index == 0 or not timeline[index - 1].is_warning)
        for index, decision in enumerate(timeline)
    )

    window_start_s = None
    matched_time_s = None
    matched_lead_s = None
    early_count = 0
    post_contact_count = 0

    # None is a negative episode; numeric zero is contact at the initial time.
    if reference_contact_time_s is None:
        outcome = "false_warning" if warning_times else "clear_negative"

    else:
        event_s = reference_contact_time_s
        window_start_s = max(0.0, event_s - pre_event_window_s)

        # Match the earliest true decision inside the inclusive window,
        # including an activation that started before the window.
        matched_time_s = next(
            (time_s for time_s in warning_times if window_start_s <= time_s <= event_s),
            None,
        )

        early_count = sum(time_s < window_start_s for time_s in warning_times)
        post_contact_count = sum(time_s > event_s for time_s in warning_times)

        # A matched time of zero is valid; only None denotes no match.
        if matched_time_s is None:
            outcome = "missed"
        else:
            matched_lead_s = event_s - matched_time_s
            # Late is a matched outcome, distinct from a missed event.
            outcome = "useful" if matched_lead_s >= minimum_useful_lead_s else "late"

    # The first warning anywhere can differ from the first qualifying warning.
    return {
        "outcome": outcome,
        "reference_contact_time_s": reference_contact_time_s,
        "horizon_s": horizon_s,
        "pre_event_window_s": pre_event_window_s,
        "minimum_useful_lead_s": minimum_useful_lead_s,
        "window_start_s": window_start_s,
        "first_warning_time_s": (warning_times[0] if warning_times else None),
        "first_matched_warning_time_s": matched_time_s,
        "matched_lead_s": matched_lead_s,
        "warning_decision_count": len(warning_times),
        "warning_activation_count": activation_count,
        "early_warning_decision_count": early_count,
        "post_contact_warning_decision_count": post_contact_count,
    }


def _check_complete_score(score, reference_contact_time_s, horizon_s):
    """Reject contradictory completed results before counting outcomes."""

    required = {
        "outcome",
        "reference_contact_time_s",
        "horizon_s",
        "pre_event_window_s",
        "minimum_useful_lead_s",
        "first_matched_warning_time_s",
        "matched_lead_s",
    }

    if not isinstance(score, dict) or not required.issubset(score):
        raise ValueError("complete case requires a complete score")

    _check_reference(
        score["reference_contact_time_s"],
        score["horizon_s"],
    )
    _check_policy(
        score["pre_event_window_s"],
        score["minimum_useful_lead_s"],
    )

    if (
        score["reference_contact_time_s"] != reference_contact_time_s
        or score["horizon_s"] != horizon_s
    ):
        raise ValueError("score disagrees with case reference or horizon")

    # Outcome categories must agree with the independent contact label.
    allowed = (
        NEGATIVE_OUTCOMES if reference_contact_time_s is None else POSITIVE_OUTCOMES
    )
    outcome = score["outcome"]

    if outcome not in allowed:
        raise ValueError("outcome disagrees with reference contact")

    matched_time_s = score["first_matched_warning_time_s"]
    lead_s = score["matched_lead_s"]

    if outcome in ("useful", "late"):
        require_finite("matched warning time", matched_time_s, minimum=0)
        require_finite("matched lead", lead_s, minimum=0)

        start_s = max(
            0.0,
            reference_contact_time_s - score["pre_event_window_s"],
        )

        if not start_s <= matched_time_s <= reference_contact_time_s:
            raise ValueError("matched warning lies outside its window")

        expected_lead_s = reference_contact_time_s - matched_time_s

        # Tolerance checks stored arithmetic, not event/window membership.
        if not math.isclose(
            lead_s,
            expected_lead_s,
            rel_tol=0,
            abs_tol=1e-9,
        ):
            raise ValueError("matched lead disagrees with event minus warning")

        expected_outcome = (
            "useful" if expected_lead_s >= score["minimum_useful_lead_s"] else "late"
        )

        if outcome != expected_outcome:
            raise ValueError("outcome disagrees with useful-lead minimum")

    elif matched_time_s is not None or lead_s is not None:
        raise ValueError("unmatched cases must have null matched fields")

    return outcome


def _rate(numerator, denominator):
    """Keep the count and eligible denominator beside every rate."""

    # No eligible episodes means unavailable rate, not measured zero percent.
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": numerator / denominator if denominator else None,
    }


def summarize(case_results):
    """Group outcomes by condition while retaining unsuccessful cases."""

    groups = {}
    seen_ids = set()
    required = {
        "case_id",
        "condition_id",
        "status",
        "reference_contact_time_s",
        "horizon_s",
    }

    for case in case_results:
        if not isinstance(case, dict) or not required.issubset(case):
            raise ValueError("case metadata is incomplete")

        for name in ("case_id", "condition_id", "status"):
            if not isinstance(case[name], str) or not case[name]:
                raise ValueError(f"{name} must be nonempty text")

        if case["case_id"] in seen_ids:
            raise ValueError("duplicate case_id")

        seen_ids.add(case["case_id"])

        status = case["status"]

        if status not in STATUSES:
            raise ValueError("unknown case status")

        reference = case["reference_contact_time_s"]
        horizon_s = case["horizon_s"]
        # Failed cases still need valid labels for planned/unscored counts.
        _check_reference(reference, horizon_s)

        condition = case["condition_id"]
        label = "positive" if reference is not None else "negative"

        if condition not in groups:
            groups[condition] = {
                "condition_id": condition,
                "planned": {"positive": 0, "negative": 0},
                "scored": {"positive": 0, "negative": 0},
                "status_counts": {name: 0 for name in STATUSES},
                "outcomes": {name: 0 for name in POSITIVE_OUTCOMES + NEGATIVE_OUTCOMES},
                "unscored_case_ids": [],
            }

        group = groups[condition]
        group["planned"][label] += 1
        group["status_counts"][status] += 1

        # Execution failures remain visible; they are not algorithm misses.
        if status != "complete":
            group["unscored_case_ids"].append(case["case_id"])
            continue

        outcome = _check_complete_score(
            case.get("score"),
            reference,
            horizon_s,
        )

        group["scored"][label] += 1
        group["outcomes"][outcome] += 1

    summaries = []

    for condition in sorted(groups):
        group = groups[condition]
        counts = group["outcomes"]
        positives = group["scored"]["positive"]
        negatives = group["scored"]["negative"]

        group["unscored"] = {
            label: group["planned"][label] - group["scored"][label]
            for label in ("positive", "negative")
        }

        # Denominators are scored positives/negatives, shown beside planned
        # and unscored counts rather than silently hiding incomplete runs.
        group["rates"] = {
            "useful": _rate(counts["useful"], positives),
            "late": _rate(counts["late"], positives),
            "missed": _rate(counts["missed"], positives),
            "without_useful_warning": _rate(
                counts["late"] + counts["missed"],
                positives,
            ),
            "false_warning_episode": _rate(
                counts["false_warning"],
                negatives,
            ),
        }

        summaries.append(group)

    return summaries
