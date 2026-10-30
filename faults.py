from dataclasses import dataclass
import random
from motion import TruthSample, require_finite
from observations import Observation


@dataclass(frozen=True)
class FaultConfig:
    """Single-fault settings with explicit SI units and stream seeds."""

    mode: str = "clean"

    gap_sigma_m: float = 0.0
    closing_sigma_mps: float = 0.0
    latency_s: float = 0.0
    latency_jitter_s: float = 0.0
    dropout_probability: float = 0.0

    gap_seed: int = 101
    closing_seed: int = 102
    latency_seed: int = 103
    dropout_seed: int = 104

    def __post_init__(self):
        """Reject invalid values and accidentally combined fault settings."""

        allowed_fields = {
            "clean": (),
            "noise": (
                "gap_sigma_m",
                "closing_sigma_mps",
            ),
            "latency": (
                "latency_s",
                "latency_jitter_s",
            ),
            "dropout": ("dropout_probability",),
        }

        # Check type before dictionary membership, including unhashable inputs.
        if not isinstance(self.mode, str) or self.mode not in allowed_fields:
            raise ValueError("mode must be clean, noise, latency or dropout")

        numeric_fields = (
            "gap_sigma_m",
            "closing_sigma_mps",
            "latency_s",
            "latency_jitter_s",
            "dropout_probability",
        )

        for name in numeric_fields:
            require_finite(name, getattr(self, name), minimum=0)

        if self.dropout_probability > 1:
            raise ValueError("dropout_probability must be <= 1")

        seed_fields = (
            "gap_seed",
            "closing_seed",
            "latency_seed",
            "dropout_seed",
        )

        for name in seed_fields:
            value = getattr(self, name)

            # bool is an int subclass but is not a valid experiment seed.
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be an integer >= 0")

        # Only the selected fault group may contain nonzero magnitudes.
        for name in numeric_fields:
            if name not in allowed_fields[self.mode] and getattr(self, name) != 0:
                raise ValueError(f"{name} must be zero when mode is {self.mode}")


def make_rngs(config):
    """Create fresh generators without changing global random state."""

    if not isinstance(config, FaultConfig):
        raise ValueError("config must be a FaultConfig")

    return {
        "gap": random.Random(config.gap_seed),
        "closing": random.Random(config.closing_seed),
        "latency": random.Random(config.latency_seed),
        "dropout": random.Random(config.dropout_seed),
    }


def _validate_truth_samples(samples):
    """Validate source values and canonical generation order."""

    previous = None

    for sample in samples:
        if not isinstance(sample, TruthSample):
            raise ValueError("every source row must be a TruthSample")

        # Positions, gap and closing speed retain their signed meanings.
        for name in (
            "ego_front_x_m",
            "lead_rear_x_m",
            "gap_m",
            "closing_speed_mps",
        ):
            require_finite(name, getattr(sample, name))

        for name in ("ego_speed_mps", "lead_speed_mps"):
            require_finite(name, getattr(sample, name), minimum=0)

        # Reuse the existing metadata/time/value validation contract.
        Observation(
            scenario_id=sample.scenario_id,
            sample_id=sample.sample_id,
            measurement_time_s=sample.time_s,
            arrival_time_s=sample.time_s,
            gap_m=sample.gap_m,
            closing_speed_mps=sample.closing_speed_mps,
        )

        if previous is not None:
            if sample.scenario_id != previous.scenario_id:
                raise ValueError("source rows must share one scenario_id")

            if sample.sample_id <= previous.sample_id:
                raise ValueError("source sample IDs must strictly increase")

            if sample.time_s <= previous.time_s:
                raise ValueError("source times must strictly increase")

        previous = sample


def apply_draws(
    sample,
    config,
    *,
    z_gap,
    z_closing,
    u_latency,
    u_dropout,
):
    """Transform one source row using explicit, independently testable draws."""

    if not isinstance(config, FaultConfig):
        raise ValueError("config must be a FaultConfig")

    _validate_truth_samples([sample])

    for name, value in (
        ("z_gap", z_gap),
        ("z_closing", z_closing),
    ):
        require_finite(name, value)

    for name, value in (
        ("u_latency", u_latency),
        ("u_dropout", u_dropout),
    ):
        require_finite(name, value, minimum=0)

        if value >= 1:
            raise ValueError(f"{name} must be < 1")

    gap_error_m = config.gap_sigma_m * z_gap
    closing_error_mps = config.closing_sigma_mps * z_closing

    delay_s = config.latency_s + config.latency_jitter_s * u_latency
    arrival_time_s = sample.time_s + delay_s

    measured_gap_m = sample.gap_m + gap_error_m
    measured_closing_mps = sample.closing_speed_mps + closing_error_mps

    # Finite inputs can still overflow during arithmetic.
    for name, value in (
        ("gap_error_m", gap_error_m),
        ("closing_error_mps", closing_error_mps),
        ("delay_s", delay_s),
        ("arrival_time_s", arrival_time_s),
        ("measured_gap_m", measured_gap_m),
        ("measured_closing_mps", measured_closing_mps),
    ):
        require_finite(name, value)

    # Construct and validate before suppression so dropout hides no invalid data.
    candidate = Observation(
        scenario_id=sample.scenario_id,
        sample_id=sample.sample_id,
        measurement_time_s=sample.time_s,
        arrival_time_s=arrival_time_s,
        gap_m=measured_gap_m,
        closing_speed_mps=measured_closing_mps,
    )

    dropped = u_dropout < config.dropout_probability

    audit = {
        "scenario_id": sample.scenario_id,
        "sample_id": sample.sample_id,
        "measurement_time_s": sample.time_s,
        "z_gap": z_gap,
        "z_closing": z_closing,
        "u_latency": u_latency,
        "u_dropout": u_dropout,
        "gap_error_m": gap_error_m,
        "closing_error_mps": closing_error_mps,
        "delay_s": delay_s,
        "arrival_time_s": arrival_time_s,
        "dropped": dropped,
    }

    return (None if dropped else candidate), audit


def inject_faults(truth_samples, config):
    """Return retained observations and one audit row per source sample."""

    if not isinstance(config, FaultConfig):
        raise ValueError("config must be a FaultConfig")

    samples = list(truth_samples)

    # Check the entire source before consuming any random state.
    _validate_truth_samples(samples)

    if not samples:
        return [], []

    rngs = make_rngs(config)
    observations = []
    audit_rows = []

    for sample in samples:
        # Reserve all four draws before deciding whether to omit the reading.
        z_gap = rngs["gap"].gauss(0.0, 1.0)
        z_closing = rngs["closing"].gauss(0.0, 1.0)
        u_latency = rngs["latency"].random()
        u_dropout = rngs["dropout"].random()

        observation, audit = apply_draws(
            sample,
            config,
            z_gap=z_gap,
            z_closing=z_closing,
            u_latency=u_latency,
            u_dropout=u_dropout,
        )

        audit_rows.append(audit)

        if observation is not None:
            observations.append(observation)

    return observations, audit_rows
