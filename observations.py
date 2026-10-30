"""Exact synthetic sensor readings with separate sampling and delivery times."""

from dataclasses import dataclass
from motion import TruthSample, require_finite


@dataclass(frozen=True)
class Observation:
    """Immutable SI reading; arrival is its earliest availability time."""

    scenario_id: str
    sample_id: int
    measurement_time_s: float
    arrival_time_s: float
    gap_m: float
    closing_speed_mps: float

    def __post_init__(self):
        """Reject invalid metadata, non-finite values and impossible delivery."""
        if not isinstance(self.scenario_id, str) or not self.scenario_id:
            raise ValueError("scenario_id must be nonempty text")

        # Booleans are int subclasses but are not valid sample identifiers.
        if (
            isinstance(self.sample_id, bool)
            or not isinstance(self.sample_id, int)
            or self.sample_id < 0
        ):
            raise ValueError("sample_id must be an integer >= 0")

        for name in ("measurement_time_s", "arrival_time_s"):
            require_finite(
                f"{name} for sample {self.sample_id}",
                getattr(self, name),
                minimum=0,
            )

        # Signed values retain overlap and opening-motion information.
        for name in ("gap_m", "closing_speed_mps"):
            require_finite(
                f"{name} for sample {self.sample_id}",
                getattr(self, name),
            )

        if self.arrival_time_s < self.measurement_time_s:
            raise ValueError(
                f"sample {self.sample_id}: arrival cannot precede measurement"
            )


def validate_observations(observations, scenario_id, horizon_s):
    """Check stream identity, uniqueness and measurement bounds without sorting."""

    if not isinstance(scenario_id, str) or not scenario_id:
        raise ValueError("scenario_id must be a nonempty text")

    # Context remains meaningful even when the stream contains no readings.
    require_finite("horizon_s", horizon_s, minimum=0)

    seen_ids = set()
    seen_times = set()

    for observation in observations:
        if not isinstance(observation, Observation):
            raise ValueError("every reading myst be an Observation")

        if observation.scenario_id != scenario_id:
            raise ValueError(f"sample {observation.sample_id}: wrong scenario_id")

        # Delivery after H is valid; only measurement time is bounded here.
        if observation.measurement_time_s > horizon_s:
            raise ValueError(
                f"sample {observation.sample_id}: measurement exceeds horizon"
            )

        # Missing IDs/order are allowed, but IDs and times must each be unique.
        if observation.sample_id in seen_ids:
            raise ValueError(f"duplicate sample_id: {observation.sample_id}")

        if observation.measurement_time_s in seen_times:
            raise ValueError(
                "duplicate measurement_time_s: " f"{observation.measurement_time_s}"
            )

        seen_ids.add(observation.sample_id)
        seen_times.add(observation.measurement_time_s)


def make_observations(truth_samples, latency_s=0.0):
    """Copy truth into new records, changing arrival time only by fixed delay."""

    # Validate the delay before accepting even an empty source iterable.
    require_finite("latency_s", latency_s, minimum=0)

    # Materialize once so iterators work without modifying the supplied list.
    samples = list(truth_samples)
    observations = []

    for sample in samples:
        if not isinstance(sample, TruthSample):
            raise ValueError("every source smaple must be a TruthSample")

        # Retain acquisition time/values; constructor checks arrival overflow.
        observations.append(
            Observation(
                scenario_id=sample.scenario_id,
                sample_id=sample.sample_id,
                measurement_time_s=sample.time_s,
                arrival_time_s=sample.time_s + latency_s,
                gap_m=sample.gap_m,
                closing_speed_mps=sample.closing_speed_mps,
            )
        )

    if observations:
        # This is the supplied data's extent, not a new scenario horizon.
        input_extent_s = max(
            observation.measurement_time_s for observation in observations
        )

        validate_observations(
            observations,
            scenario_id=observations[0].scenario_id,
            horizon_s=input_extent_s,
        )
    # Preserve source order; causal release and sorting belong to replay.
    return observations
