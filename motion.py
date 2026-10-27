import csv
import json
import math
from pathlib import Path


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
