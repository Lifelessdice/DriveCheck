"""Fault configuration and random-stream reproducibility checks."""

from dataclasses import FrozenInstanceError, replace
import random
import unittest

from faults import FaultConfig, make_rngs


class FaultConfigTests(unittest.TestCase):
    """Check accepted settings and independently invalid inputs."""

    def test_valid_settings(self):
        examples = [
            {},
            {
                "mode": "noise",
                "gap_sigma_m": 0.5,
                "closing_sigma_mps": 0.1,
            },
            {
                "mode": "latency",
                "latency_s": 0.25,
                "latency_jitter_s": 0.5,
            },
            {
                "mode": "dropout",
                "dropout_probability": 0.2,
            },
            {
                "mode": "dropout",
                "dropout_probability": 1.0,
            },
            {
                "mode": "noise",
            },
            {
                "gap_seed": 0,
                "closing_seed": 0,
                "latency_seed": 0,
                "dropout_seed": 0,
            },
        ]

        for settings in examples:
            with self.subTest(settings=settings):
                config = FaultConfig(**settings)
                self.assertEqual(
                    config.mode,
                    settings.get("mode", "clean"),
                )

    def test_settings_are_frozen(self):
        config = FaultConfig()

        with self.assertRaises(FrozenInstanceError):
            config.gap_seed = 999

    def test_rejects_invalid_modes(self):
        for mode in (None, True, 1, [], {}, "", "Noise", "combined"):
            with self.subTest(mode=mode):
                with self.assertRaises(ValueError):
                    FaultConfig(mode=mode)

    def test_rejects_invalid_numeric_values(self):
        field_modes = {
            "gap_sigma_m": "noise",
            "closing_sigma_mps": "noise",
            "latency_s": "latency",
            "latency_jitter_s": "latency",
            "dropout_probability": "dropout",
        }

        invalid_values = (
            True,
            False,
            None,
            "0.1",
            -0.1,
            float("nan"),
            float("inf"),
            float("-inf"),
            10**400,
        )

        for field, mode in field_modes.items():
            for value in invalid_values:
                with self.subTest(field=field, value=value):
                    with self.assertRaises(ValueError):
                        FaultConfig(mode=mode, **{field: value})

    def test_rejects_probability_above_one(self):
        with self.assertRaises(ValueError):
            FaultConfig(
                mode="dropout",
                dropout_probability=1.01,
            )

    def test_rejects_invalid_seeds(self):
        fields = (
            "gap_seed",
            "closing_seed",
            "latency_seed",
            "dropout_seed",
        )

        for field in fields:
            for value in (-1, 1.5, True, "101", None):
                with self.subTest(field=field, value=value):
                    with self.assertRaises(ValueError):
                        FaultConfig(**{field: value})

    def test_rejects_inactive_nonzero_fields(self):
        examples = [
            {"mode": "clean", "gap_sigma_m": 0.1},
            {"mode": "clean", "latency_s": 0.1},
            {"mode": "clean", "dropout_probability": 0.1},
            {"mode": "noise", "latency_s": 0.1},
            {"mode": "noise", "dropout_probability": 0.1},
            {"mode": "latency", "gap_sigma_m": 0.1},
            {"mode": "latency", "dropout_probability": 0.1},
            {"mode": "dropout", "closing_sigma_mps": 0.1},
            {"mode": "dropout", "latency_jitter_s": 0.1},
        ]

        for settings in examples:
            with self.subTest(settings=settings):
                with self.assertRaises(ValueError):
                    FaultConfig(**settings)


class RandomStreamTests(unittest.TestCase):
    """Check reproducibility without relying on particular random values."""

    def test_fresh_bundles_reproduce_sequences(self):
        config = FaultConfig()
        first = make_rngs(config)
        second = make_rngs(config)

        self.assertEqual(
            set(first),
            {"gap", "closing", "latency", "dropout"},
        )

        # Each stream owns a distinct generator object.
        self.assertEqual(
            len({id(generator) for generator in first.values()}),
            4,
        )

        for name in first:
            with self.subTest(stream=name):
                self.assertIsNot(first[name], second[name])

                first_values = [first[name].random() for _ in range(5)]
                second_values = [second[name].random() for _ in range(5)]

                self.assertEqual(first_values, second_values)

    def test_advancing_gap_leaves_other_streams_unchanged(self):
        advanced = make_rngs(FaultConfig())
        reference = make_rngs(FaultConfig())

        # Extra gap draws must not consume another stream's state.
        for _ in range(20):
            advanced["gap"].random()

        for name in ("closing", "latency", "dropout"):
            with self.subTest(stream=name):
                actual = [advanced[name].random() for _ in range(5)]
                expected = [reference[name].random() for _ in range(5)]

                self.assertEqual(actual, expected)

    def test_changing_gap_seed_preserves_other_streams(self):
        original = FaultConfig()
        changed = replace(original, gap_seed=999)

        first = make_rngs(original)
        second = make_rngs(changed)

        for name in ("closing", "latency", "dropout"):
            with self.subTest(stream=name):
                actual = [first[name].random() for _ in range(5)]
                expected = [second[name].random() for _ in range(5)]

                self.assertEqual(actual, expected)

    def test_global_random_state_is_unchanged(self):
        before = random.getstate()

        streams = make_rngs(FaultConfig())

        for generator in streams.values():
            for _ in range(5):
                generator.random()

        self.assertEqual(random.getstate(), before)


if __name__ == "__main__":
    unittest.main()
