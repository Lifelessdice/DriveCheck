"""Causal estimator replay with original-source and used-state evidence."""

from dataclasses import dataclass, replace

from c1_estimators import METHODS, StateEstimate, estimate_state
from observations import Observation
from replay import ReplayResult, replay
from warning_policy import Decision, prepare_decision, ttc_from_state


@dataclass(frozen=True)
class DecisionRecord:
    """Retain the original input separately from estimated/used state."""
    source: Observation | None
    estimate: StateEstimate | None
    decision: Decision


@dataclass
class EstimatedReplayResult:
    replay: ReplayResult
    records: list[DecisionRecord]


def decide_with_estimator(
    observation, now_s, warning_threshold_s=3.0, max_age_s=1.25,
    *, method="raw",
):
    """Apply common source gates before estimating and applying common TTC."""
    if method not in METHODS:
        raise ValueError(f"unknown estimation method: {method!r}")
    base = prepare_decision(observation, now_s, warning_threshold_s, max_age_s)
    if base.reason != "pending":
        return DecisionRecord(observation, None, base)

    estimate = estimate_state(observation, now_s, method)
    ttc_s, warning, reason = ttc_from_state(
        estimate.gap_m, estimate.closing_speed_mps, warning_threshold_s
    )
    decision = replace(
        base,
        gap_m=estimate.gap_m,
        closing_speed_mps=estimate.closing_speed_mps,
        ttc_s=ttc_s,
        is_warning=warning,
        reason=reason,
    )
    return DecisionRecord(observation, estimate, decision)


def replay_with_estimator(
    observations, decision_times_s, warning_threshold_s=3.0, max_age_s=1.25,
    *, scenario_id, horizon_s, method="raw",
):
    """Reuse the validated arrival queue; collect one evidence record per tick."""
    if method not in METHODS:
        raise ValueError(f"unknown estimation method: {method!r}")
    records = []

    def decision_function(observation, now_s, threshold_s, age_limit_s):
        record = decide_with_estimator(
            observation, now_s, threshold_s, age_limit_s, method=method
        )
        records.append(record)
        return record.decision

    result = replay(
        observations, decision_times_s, warning_threshold_s, max_age_s,
        scenario_id=scenario_id,
        horizon_s=horizon_s,
        decision_function=decision_function,
    )
    return EstimatedReplayResult(result, records)
