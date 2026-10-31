"""Continuous stop, hold, restart and cruise trajectories."""

from dataclasses import dataclass
import math

from motion import Scenario, TruthSample, require_finite


@dataclass(frozen=True)
class StopGoScenario:
    """SI settings for a lead vehicle that stops and restarts."""

    scenario_id: str
    initial_gap_m: float

    ego_speed_mps: float = 4.0
    lead_speed_mps: float = 4.0
    lead_deceleration_mps2: float = 2.0
    hold_s: float = 2.0
    lead_acceleration_mps2: float = 2.0
    restart_speed_mps: float = 6.0
    timestep_s: float = 1.0
    sample_count: int = 9

    def __post_init__(self):
        # Reuse M1's common ID, gap, speed and sampling guards.
        # This temporary record is not used to generate the new motion.
        Scenario(
            scenario_id=self.scenario_id,
            initial_gap_m=self.initial_gap_m,
            ego_speed_mps=self.ego_speed_mps,
            lead_speed_mps=self.lead_speed_mps,
            timestep_s=self.timestep_s,
            sample_count=self.sample_count,
        )

        for name in (
            "lead_deceleration_mps2",
            "lead_acceleration_mps2",
        ):
            require_finite(
                name,
                getattr(self, name),
                positive=True,
            )

        for name in ("hold_s", "restart_speed_mps"):
            require_finite(
                name,
                getattr(self, name),
                minimum=0,
            )

        for name in (
            "stop_time_s",
            "restart_time_s",
            "acceleration_duration_s",
            "cruise_time_s",
            "stop_distance_m",
            "cruise_distance_m",
        ):
            require_finite(
                name,
                getattr(self, name),
                minimum=0,
            )

        # Reject positive phases erased by floating-point resolution.
        if self.lead_speed_mps > 0 and self.stop_time_s == 0:
            raise ValueError("braking duration rounded to zero")

        if self.hold_s > 0 and self.restart_time_s <= self.stop_time_s:
            raise ValueError("hold duration is not representable")

        if self.restart_speed_mps > 0 and self.cruise_time_s <= self.restart_time_s:
            raise ValueError("restart duration is not representable")

    @property
    def family(self):
        return "stop_and_go"

    @property
    def horizon_s(self):
        try:
            return (self.sample_count - 1) * self.timestep_s
        except OverflowError as error:
            raise ValueError("horizon exceeds finite range") from error

    @property
    def stop_time_s(self):
        return self.lead_speed_mps / self.lead_deceleration_mps2

    @property
    def restart_time_s(self):
        return self.stop_time_s + self.hold_s

    @property
    def acceleration_duration_s(self):
        return self.restart_speed_mps / self.lead_acceleration_mps2

    @property
    def cruise_time_s(self):
        return self.restart_time_s + self.acceleration_duration_s

    @property
    def stop_distance_m(self):
        return 0.5 * self.lead_speed_mps * self.stop_time_s

    @property
    def cruise_distance_m(self):
        return (
            self.stop_distance_m
            + 0.5 * self.restart_speed_mps * self.acceleration_duration_s
        )


def _require_stop_go(scenario):
    if not isinstance(scenario, StopGoScenario):
        raise ValueError("scenario must be a StopGoScenario")


def stop_go_truth_at(scenario, elapsed_s, sample_id=0):
    """Evaluate continuous truth inside the inclusive scenario horizon."""

    _require_stop_go(scenario)
    require_finite("elapsed_s", elapsed_s, minimum=0)

    if elapsed_s > scenario.horizon_s:
        raise ValueError("elapsed_s exceeds the scenario horizon")

    if isinstance(sample_id, bool) or not isinstance(sample_id, int) or sample_id < 0:
        raise ValueError("sample_id must be an integer >= 0")

    if elapsed_s < scenario.stop_time_s:
        lead_speed = max(
            0.0,
            scenario.lead_speed_mps - scenario.lead_deceleration_mps2 * elapsed_s,
        )
        # Constant-acceleration travel = average speed × elapsed time.
        lead_distance = (0.5 * scenario.lead_speed_mps + 0.5 * lead_speed) * elapsed_s

    elif elapsed_s < scenario.restart_time_s:
        lead_speed = 0.0
        lead_distance = scenario.stop_distance_m

    elif elapsed_s < scenario.cruise_time_s:
        restarting_s = elapsed_s - scenario.restart_time_s
        lead_speed = min(
            scenario.restart_speed_mps,
            scenario.lead_acceleration_mps2 * restarting_s,
        )
        lead_distance = scenario.stop_distance_m + 0.5 * lead_speed * restarting_s

    else:
        cruising_s = elapsed_s - scenario.cruise_time_s
        lead_speed = scenario.restart_speed_mps
        lead_distance = scenario.cruise_distance_m + lead_speed * cruising_s

    ego_x = scenario.ego_speed_mps * elapsed_s
    lead_x = scenario.initial_gap_m + lead_distance
    gap = lead_x - ego_x
    closing = scenario.ego_speed_mps - lead_speed

    for name, value in (
        ("ego_front_x_m", ego_x),
        ("lead_rear_x_m", lead_x),
        ("lead_speed_mps", lead_speed),
        ("gap_m", gap),
        ("closing_speed_mps", closing),
    ):
        require_finite(name, value)

    return TruthSample(
        scenario_id=scenario.scenario_id,
        sample_id=sample_id,
        time_s=elapsed_s,
        ego_front_x_m=ego_x,
        lead_rear_x_m=lead_x,
        ego_speed_mps=scenario.ego_speed_mps,
        lead_speed_mps=lead_speed,
        gap_m=gap,
        closing_speed_mps=closing,
    )


def sample_stop_go_truth(scenario):
    """Include zero and horizon without accumulating timestep additions."""

    _require_stop_go(scenario)
    samples = []

    for sample_id in range(scenario.sample_count):
        elapsed_s = sample_id * scenario.timestep_s

        if samples and elapsed_s <= samples[-1].time_s:
            raise ValueError("sample times must strictly increase")

        samples.append(
            stop_go_truth_at(
                scenario,
                elapsed_s,
                sample_id=sample_id,
            )
        )

    return samples


def _lead_acceleration_at(scenario, time_s):
    """Select acceleration on half-open motion phases."""

    if time_s < scenario.stop_time_s:
        return -scenario.lead_deceleration_mps2

    if time_s < scenario.restart_time_s:
        return 0.0

    if time_s < scenario.cruise_time_s:
        return scenario.lead_acceleration_mps2

    return 0.0


def _phase_roots(gap_m, closing_speed_mps, lead_acceleration_mps2):
    """Solve positive-starting-gap motion using signed acceleration."""

    # Local phase equation: gap + b*u + a*u**2 = 0.
    a = 0.5 * lead_acceleration_mps2
    b = -closing_speed_mps
    c = gap_m

    if lead_acceleration_mps2 != 0 and a == 0:
        raise ValueError("quadratic coefficient rounded to zero")

    if a == 0:
        if b == 0:
            return ()

        root = -c / b
        require_finite("linear contact root", root)

        if root == 0:
            raise ValueError("contact root rounded to zero")

        return (root,)

    discriminant = b * b - 4 * a * c
    require_finite("contact discriminant", discriminant)

    if discriminant < 0:
        return ()

    root_term = math.sqrt(discriminant)

    # Avoid subtracting nearly equal terms when forming the small root.
    q = -0.5 * b - 0.5 * math.copysign(root_term, b)
    require_finite("quadratic q", q)

    if q == 0:
        raise ValueError("contact equation lost numeric precision")

    roots = (q / a, c / q)

    for root in roots:
        require_finite("quadratic contact root", root)

        if root == 0:
            raise ValueError("contact root rounded to zero")

    return roots


def first_stop_go_contact_time(scenario):
    """Return first continuous contact inside the inclusive horizon."""

    _require_stop_go(scenario)

    if scenario.initial_gap_m <= 0:
        return 0.0

    horizon_s = scenario.horizon_s
    boundaries = {0.0, horizon_s}

    for boundary in (
        scenario.stop_time_s,
        scenario.restart_time_s,
        scenario.cruise_time_s,
    ):
        if 0 < boundary < horizon_s:
            boundaries.add(boundary)

    ordered = sorted(boundaries)

    for left_s, right_s in zip(ordered, ordered[1:]):
        state = stop_go_truth_at(scenario, left_s)

        if state.gap_m <= 0:
            return left_s

        roots = _phase_roots(
            state.gap_m,
            state.closing_speed_mps,
            _lead_acceleration_at(scenario, left_s),
        )

        width_s = right_s - left_s
        tolerance_s = 32 * math.ulp(max(abs(left_s), abs(right_s)))

        for root in sorted(roots):
            if 0 <= root <= width_s + tolerance_s:
                return left_s + min(root, width_s)

    return None


@dataclass(frozen=True)
class StopGoFixture:
    """A scenario with reference answers derived independently."""

    scenario: StopGoScenario
    reference_contact_time_s: float | None
    reference_final_gap_m: float
    reference_basis: str


def stop_go_fixtures():
    """Return literal contact/non-contact study references."""

    return [
        StopGoFixture(
            scenario=StopGoScenario(
                scenario_id="stop_and_go_contact",
                initial_gap_m=15.0,
            ),
            reference_contact_time_s=5.0,
            reference_final_gap_m=2.0,
            reference_basis=(
                "Restart gap=3-4u+u^2=(u-1)(u-3), u=t-4. "
                "First contact is t=5 s. At 8 s lead travel is "
                "19 m and ego travel 32 m: gap=15+19-32=2 m."
            ),
        ),
        StopGoFixture(
            scenario=StopGoScenario(
                scenario_id="stop_and_go_noncontact",
                initial_gap_m=18.0,
            ),
            reference_contact_time_s=None,
            reference_final_gap_m=5.0,
            reference_basis=(
                "Restart gap=(u-2)^2+2 has minimum 2 m at t=6 s. "
                "Earlier phases have larger gaps and cruise opens "
                "the gap. At 8 s gap=18+19-32=5 m."
            ),
        ),
    ]
