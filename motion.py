import csv
import json
import math
from pathlib import Path
from dataclasses import dataclass


def gap_after_seconds(initial_gap_m, ego_speed_mps, lead_speed_mps, elapsed_s):
    """Return bumper gap for two vehicles moving at constatn speed."""
    closing_speed_mps = ego_speed_mps - lead_speed_mps

    return initial_gap_m - (closing_speed_mps * elapsed_s)


def require_finite(name, value, *, minimum=None, positive=None):
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

        elapsed_s = sample_id * timestep_s

        gap_m = gap_after_seconds(
            initial_gap_m, ego_speed_mps, lead_speed_mps, elapsed_s
        )

        samples.append({"sample_id": sample_id, "time_s": elapsed_s, "gap_m": gap_m})

    return samples


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    initial_gap_m: float
    ego_speed_mps: float
    lead_speed_mps: float
    timestep_s: float
    sample_count: int
    brake_start_s: float = 0.0
    lead_deceleration_mps2: float = 0.0

    def __post_init__(self):
        if not isinstance(self.scenario_id, str) or not self.scenario_id:
            raise ValueError("scenario_id myst be nonempty text")

        allowed = "abcdefghijklmnopqrstuvwxyz0123456789_-"

        if any(character not in allowed for character in self.scenario_id):
            raise ValueError("scenario_id must use lowercase letters, digits, _ or -")

        reversed = {"manifest", "con", "prn", "aux", "nul"}
        reversed.update(f"com{i}" for i in range(1, 10))
        reversed.update(f"lpt{i}" for i in range(1, 10))

        if self.scenario_id in reversed:
            raise ValueError("scenario_id is a reserved filename")

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
        try:
            return (self.sample_count - 1) * self.timestep_s
        except OverflowError as error:
            raise ValueError("horizon_s exceeds the finite numeric range") from error

    @property
    def stop_time_s(self):
        if self.lead_deceleration_mps2 == 0:
            return None

        return self.brake_start_s + self.lead_speed_mps / self.lead_deceleration_mps2


@dataclass(frozen=True)
class TruthSample:
    scenario_id: str
    sample_id: int
    time_s: float
    ego_front_x_m: float
    lead_rear_x_m: float
    ego_speed_mps: float
    lead_speed_mps: float
    gap_m: float
    closing_speed_mps: float


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
