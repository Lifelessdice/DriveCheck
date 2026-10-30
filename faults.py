from dataclasses import dataclass
import random
from motion import require_finite


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
