# Longitudinal motion uses metres, seconds, m/s and m/s^2.
# Positive x points forward; bumper gap is lead rear minus ego front.
import csv
import json
import math
from pathlib import Path
from dataclasses import dataclass


def gap_after_seconds(initial_gap_m, ego_speed_mps, lead_speed_mps, elapsed_s):
    """Return the signed bumper gap under constant forward speeds."""
    # Positive closing speed means the bumper gap is shrinking.
    closing_speed_mps = ego_speed_mps - lead_speed_mps

    return initial_gap_m - (closing_speed_mps * elapsed_s)


def require_finite(name, value, *, minimum=None, positive=None):
    """Validate numeric type, finiteness and any requested range limits."""
    # bool is an int subclass, but is not a valid physical input.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")

    try:
        finite = math.isfinite(value)

    except OverflowError:
        finite = False

    if not finite:
        raise ValueError(f"{name} must be finite")

    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")

    if positive and value <= 0:
        raise ValueError(f"{name} must be positive")


def sample_constant_speed(
    initial_gap_m, ego_speed_mps, lead_speed_mps, timestep_s, sample_count
):
    """Return constant-speed gap samples, starting at elapsed time zero."""

    require_finite("initial_gap_m", initial_gap_m)
    require_finite("ego_speed_mps", ego_speed_mps, minimum=0)
    require_finite("lead_speed_mps", lead_speed_mps, minimum=0)
    require_finite("timestep_s", timestep_s, positive=True)

    if (
        isinstance(sample_count, bool)
        or not isinstance(sample_count, int)
        or sample_count < 1
    ):
        raise ValueError("sample_count must be an integer >= 1")

    samples = []

    for sample_id in range(sample_count):

        # Multiplication avoids rounding accumulated by repeated timestep addition.
        elapsed_s = sample_id * timestep_s

        # Evaluate from the initial state rather than updating the previous gap.
        gap_m = gap_after_seconds(
            initial_gap_m, ego_speed_mps, lead_speed_mps, elapsed_s
        )

        samples.append({"sample_id": sample_id, "time_s": elapsed_s, "gap_m": gap_m})

    return samples


# Immutable settings shared by every sample in a scenario.
@dataclass(frozen=True)
class Scenario:
    """Validated inputs for a one-dimensional longitudinal scenario."""

    scenario_id: str
    initial_gap_m: float
    ego_speed_mps: float
    lead_speed_mps: float
    timestep_s: float
    sample_count: int
    brake_start_s: float = 0.0
    # Nonnegative braking magnitude; signed acceleration is its negative.
    lead_deceleration_mps2: float = 0.0

    def __post_init__(self):
        if not isinstance(self.scenario_id, str) or not self.scenario_id:
            raise ValueError("scenario_id myst be nonempty text")

        allowed = "abcdefghijklmnopqrstuvwxyz0123456789_-"

        if any(character not in allowed for character in self.scenario_id):
            raise ValueError("scenario_id must use lowercase letters, digits, _ or -")

        # Reserve Windows device names and the run-manifest filename.
        reversed = {"manifest", "con", "prn", "aux", "nul"}
        reversed.update(f"com{i}" for i in range(1, 10))
        reversed.update(f"lpt{i}" for i in range(1, 10))

        if self.scenario_id in reversed:
            raise ValueError("scenario_id is a reserved filename")

        # Negative gap denotes virtual overlap and is preserved as a signed value.
        require_finite("initial_gap_m", self.initial_gap_m)

        for name in (
            "ego_speed_mps",
            "lead_speed_mps",
            "brake_start_s",
            "lead_deceleration_mps2",
        ):
            require_finite(name, getattr(self, name), minimum=0)

        require_finite("timestep_s", self.timestep_s, positive=True)

        if (
            isinstance(self.sample_count, bool)
            or not isinstance(self.sample_count, int)
            or self.sample_count < 1
        ):
            raise ValueError("sample_count must be an integer >= 1")

        require_finite("horizon_s", self.horizon_s)

        if self.stop_time_s is not None:
            require_finite("stop_time_s", self.stop_time_s)

    @property
    def horizon_s(self):
        # N samples including t=0 span N-1 time intervals.
        try:
            return (self.sample_count - 1) * self.timestep_s
        except OverflowError as error:
            raise ValueError("horizon_s exceeds the finite numeric range") from error

    @property
    def stop_time_s(self):
        # Zero deceleration disables braking and has no configured stop time.
        if self.lead_deceleration_mps2 == 0:
            return None

        # Stop time = brake start + initial speed / deceleration.
        return self.brake_start_s + self.lead_speed_mps / self.lead_deceleration_mps2


# Clean kinematic values are separate from configuration and sensor observations.
@dataclass(frozen=True)
class TruthSample:
    """Positions, speeds and signed gap at one clean-truth timestamp."""

    scenario_id: str
    sample_id: int
    time_s: float
    ego_front_x_m: float
    lead_rear_x_m: float
    ego_speed_mps: float
    lead_speed_mps: float
    gap_m: float
    closing_speed_mps: float


def truth_at(scenario, elapsed_s, sample_id=0):
    """Evaluate a clean kinematic state at a nonnegative elapsed time."""
    require_finite("elapsed_s", elapsed_s, minimum=0)

    if isinstance(sample_id, bool) or not isinstance(sample_id, int) or sample_id < 0:
        raise ValueError("sample_id must be an integer >= 0")

    # Ego motion remains constant-speed throughout the scenario.
    ego_front_x_m = scenario.ego_speed_mps * elapsed_s
    deceleration = scenario.lead_deceleration_mps2

    if deceleration == 0 or elapsed_s <= scenario.brake_start_s:
        lead_travel_m = scenario.lead_speed_mps * elapsed_s
        lead_speed_mps = scenario.lead_speed_mps

    else:
        # Cap braking duration at the time required to reach zero speed.
        braking_s = min(
            elapsed_s - scenario.brake_start_s,
            scenario.lead_speed_mps / deceleration,
        )

        # Total travel includes constant-speed motion before braking starts.
        lead_travel_m = (
            scenario.lead_speed_mps * scenario.brake_start_s
            + scenario.lead_speed_mps * braking_s
            - 0.5 * deceleration * braking_s * braking_s
        )

        lead_speed_mps = max(
            0.0,
            scenario.lead_speed_mps - deceleration * braking_s,
        )

    lead_rear_x_m = scenario.initial_gap_m + lead_travel_m
    gap_m = lead_rear_x_m - ego_front_x_m

    require_finite("ego_front_x_m", ego_front_x_m)
    require_finite("lead_rear_x_m", lead_rear_x_m)
    require_finite("gap_m", gap_m)

    return TruthSample(
        scenario_id=scenario.scenario_id,
        sample_id=sample_id,
        time_s=elapsed_s,
        ego_front_x_m=ego_front_x_m,
        lead_rear_x_m=lead_rear_x_m,
        ego_speed_mps=scenario.ego_speed_mps,
        lead_speed_mps=lead_speed_mps,
        gap_m=gap_m,
        closing_speed_mps=scenario.ego_speed_mps - lead_speed_mps,
    )


def sample_truth(scenario):
    """Evaluate truth at each configured sample ID and elapsed time."""
    samples = []

    for sample_id in range(scenario.sample_count):
        elapsed_s = sample_id * scenario.timestep_s

        # Reject time grids that stop increasing after floating-point rounding.
        if samples and elapsed_s <= samples[-1].time_s:
            raise ValueError("sample times must strictly increase")

        samples.append(
            truth_at(
                scenario,
                elapsed_s,
                sample_id=sample_id,
            )
        )

    return samples


def contact_delay(gap_m, closing_speed_mps, deceleration_mps2):
    """Return contact delay for one extended motion phase, or None."""

    require_finite("gap_m", gap_m)
    require_finite("closing_speed_mps", closing_speed_mps)
    require_finite("deceleration_mps2", deceleration_mps2, minimum=0)

    if gap_m <= 0:
        return 0.0

    c = closing_speed_mps
    a = deceleration_mps2

    # Phase gap after u seconds: gap_m - c*u - 0.5*a*u**2.
    if a == 0:
        if c <= 0:
            return None

        delay_s = gap_m / c

    else:

        # Reject intermediate overflow rather than producing a false zero delay.
        discriminant = c * c + 2 * a * gap_m
        require_finite(
            "contact discriminant",
            discriminant,
            positive=True,
        )

        root_term = math.sqrt(discriminant)

        # Choose the root form that avoids subtracting nearly equal values.
        if c >= 0:
            delay_s = 2 * gap_m / (root_term + c)
        else:
            delay_s = (root_term - c) / a

    require_finite("contact_delay", delay_s, positive=True)
    return delay_s


def first_contact_time(scenario):
    """Return first contact within the inclusive horizon, or None."""
    # Initial touching or overlap is an event even with a zero-length horizon.
    if scenario.initial_gap_m <= 0:
        return 0.0

    horizon_s = scenario.horizon_s
    stop_time_s = scenario.stop_time_s
    boundaries = {0.0, horizon_s}

    # The gap equation changes at braking onset and when the lead stops.
    if stop_time_s is not None:
        for boundary_s in (scenario.brake_start_s, stop_time_s):
            if 0 < boundary_s < horizon_s:
                boundaries.add(boundary_s)

    ordered = sorted(boundaries)

    # Search phases in chronological order; candidate delays start at left_s.
    for left_s, right_s in zip(ordered, ordered[1:]):
        state = truth_at(scenario, left_s)

        if state.gap_m <= 0:
            return left_s

        # Lead deceleration applies only between brake start and stop.
        barking = (
            stop_time_s is not None and scenario.brake_start_s <= left_s < stop_time_s
        )

        phase_deceleraiton = scenario.lead_deceleration_mps2 if barking else 0.0

        delay_s = contact_delay(
            state.gap_m, state.closing_speed_mps, phase_deceleraiton
        )

        if delay_s is None:
            continue

        width_s = right_s - left_s

        # Endpoint rounding allowance uses the actual time scale, not a 1 s floor.
        tolerance_s = 32 * math.ulp(max(abs(left_s), abs(right_s)))

        if 0 <= delay_s <= width_s + tolerance_s:
            # Convert phase-relative delay to absolute time and clamp roundoff.
            return left_s + min(delay_s, width_s)


# Run the console example only when this file is executed directly.
if __name__ == "__main__":
    initial_gap_m = 30.0
    ego_speed_mps = 20.0
    lead_speed_mps = 15.0
    timestep_s = 1.0

    print("time_s,gap_m")

    for sample_index in range(5):
        elapsed_s = sample_index * timestep_s

        gap_m = gap_after_seconds(
            initial_gap_m, ego_speed_mps, lead_speed_mps, elapsed_s
        )

        print(f"{elapsed_s:.1f},{gap_m:.1f}")
