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