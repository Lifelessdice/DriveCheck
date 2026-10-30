"""Release observations by arrival time and retain the newest measurement."""

from dataclasses import dataclass


from motion import require_finite
from observations import validate_observations
from warning_policy import Decision, decide, validate_warning_settings


@dataclass
class ReplayResult:
    """Decision timeline with ignored-old and beyond-horizon arrival counts."""

    decisions: list[Decision]
    ignored_older_arrival_count: int
    beyond_horizon_arrival_count: int


def make_decision_times(
    base_times_s,
    observations,
    horizon_s,
    *,
    scenario_id,
):
    """Return the union of scheduled times, valid arrivals and endpoints."""

    readings = list(observations)
    validate_observations(readings, scenario_id, horizon_s)

    times = {0.0, horizon_s}

    for time_s in base_times_s:
        require_finite("base_time_s", time_s, minimum=0)

        if time_s > horizon_s:
            raise ValueError("base time exceeds horizon_s")

        times.add(time_s)

    for reading in readings:
        if reading.arrival_time_s <= horizon_s:
            times.add(reading.arrival_time_s)

    return sorted(times)


def replay(
    observations,
    decision_times_s,
    warning_threshold_s=3.0,
    max_age_s=1.25,
    *,
    scenario_id,
    horizon_s,
):
    """Process all arrived records before each strictly ordered decision."""

    readings = list(observations)
    validate_observations(readings, scenario_id, horizon_s)
    validate_warning_settings(warning_threshold_s, max_age_s)

    times = list(decision_times_s)

    if not times:
        raise ValueError("at least one decision time is required")

    for index, time_s in enumerate(times):
        require_finite("decision time_s", time_s, minimum=0)

        if time_s > horizon_s:
            raise ValueError("decision time exceeds horizon_s")

        if index > 0 and time_s <= times[index - 1]:
            raise ValueError("decision times must strictly increase")

    # The final time must match the declared horizon, not a previous sample.
    if times[0] != 0 or times[-1] != horizon_s:
        raise ValueError("decision time must begin at 0 and end at H")

    queue = sorted(
        readings,
        key=lambda reading: (
            reading.arrival_time_s,
            reading.sample_id,
        ),
    )

    next_index = 0
    # No reading is selected before the first arrival, including an empty stream.
    latest = None
    ignored_older = 0
    decisions = []

    for now_s in times:

        while next_index < len(queue) and queue[next_index].arrival_time_s <= now_s:
            arriving = queue[next_index]
            next_index += 1

            if (
                latest is None
                or arriving.measurement_time_s > latest.measurement_time_s
            ):
                latest = arriving
            else:
                ignored_older += 1

        decisions.append(
            decide(
                latest,
                now_s,
                warning_threshold_s,
                max_age_s,
            )
        )

    return ReplayResult(
        decisions=decisions,
        ignored_older_arrival_count=ignored_older,
        beyond_horizon_arrival_count=sum(
            reading.arrival_time_s > horizon_s for reading in readings
        ),
    )
