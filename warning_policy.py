"""TTC warnings from one arrived observation and its measurement age."""

from dataclasses import dataclass, replace

from motion import require_finite
from observations import Observation


@dataclass(frozen=True)
class Decision:
    """A warning decision and the reading that supported it."""

    decision_time_s: float
    sample_id: int | None = None
    measurement_time_s: float | None = None
    arrival_time_s: float | None = None
    observation_age_s: float | None = None
    gap_m: float | None = None
    closing_speed_mps: float | None = None
    ttc_s: float | None = None
    is_warning: bool = False
    reason: str = "unavailable"


def validate_warning_settings(warning_threshold_s, max_age_s):
    """Validate the experimental TTC threshold and reading-age limit."""

    require_finite(
        "warning_threshold_s",
        warning_threshold_s,
        positive=True,
    )
    require_finite("max_age_s", max_age_s, minimum=0)


def decide(
    observation,
    now_s,
    warning_threshold_s=3.0,
    max_age_s=1.25,
):
    """Apply the TTC policy to an arrived reading without extrapolation."""

    require_finite("now_s", now_s, minimum=0)
    validate_warning_settings(warning_threshold_s, max_age_s)

    if observation is None:
        return Decision(decision_time_s=now_s)

    if not isinstance(observation, Observation):
        raise ValueError("observation must be an Observation or None")

    if observation.arrival_time_s > now_s or observation.measurement_time_s > now_s:
        raise ValueError("the observation is not available at now_s")

    age_s = now_s - observation.measurement_time_s

    # Preserve the selected reading for diagnosis, including when stale.
    base = Decision(
        decision_time_s=now_s,
        sample_id=observation.sample_id,
        measurement_time_s=observation.measurement_time_s,
        arrival_time_s=observation.arrival_time_s,
        observation_age_s=age_s,
        gap_m=observation.gap_m,
        closing_speed_mps=observation.closing_speed_mps,
        reason="pending",
    )

    if age_s > max_age_s:
        return replace(base, reason="stale")

    if observation.gap_m <= 0:
        return replace(
            base,
            ttc_s=0.0,
            is_warning=True,
            reason="contact_or_overlap",
        )

    if observation.closing_speed_mps <= 0:
        return replace(base, reason="not_closing")

    ttc_s = observation.gap_m / observation.closing_speed_mps
    require_finite("computed ttc_s", ttc_s, minimum=0)

    warning = ttc_s <= warning_threshold_s

    return replace(
        base,
        ttc_s=ttc_s,
        is_warning=warning,
        reason="ttc_warning" if warning else "ttc_clear",
    )
