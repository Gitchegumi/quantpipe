"""Unit tests for reproducibility utilities (set_deterministic_seed)."""

# pylint: disable=unused-import

import os
import random
import pytest
import numpy as np
from src.backtest.reproducibility import set_deterministic_seed


class TestSetDeterministicSeed:
    """Tests for deterministic seed configuration."""

    def test_sets_python_random_seed(self):
        """Should set Python's built-in random seed."""
        set_deterministic_seed(42)
        value1 = random.random()

        set_deterministic_seed(42)
        value2 = random.random()

        assert value1 == value2, "Same seed should produce same random values"

    def test_sets_numpy_random_seed(self):
        """Should set NumPy's random seed."""
        set_deterministic_seed(42)
        array1 = np.random.rand(5)

        set_deterministic_seed(42)
        array2 = np.random.rand(5)

        assert np.array_equal(array1, array2), "Same seed should produce same arrays"

    def test_sets_pythonhashseed_env_var(self):
        """Should set PYTHONHASHSEED environment variable."""
        set_deterministic_seed(42)
        assert os.environ.get("PYTHONHASHSEED") == "42"

    def test_different_seeds_produce_different_sequences(self):
        """Different seeds should produce different random sequences."""
        set_deterministic_seed(42)
        value1 = random.random()

        set_deterministic_seed(123)
        value2 = random.random()

        assert value1 != value2, "Different seeds should produce different values"

    def test_resetting_same_seed_resets_sequence(self):
        """Calling set_deterministic_seed again should reset the sequence."""
        set_deterministic_seed(42)
        random.random()  # Advance the sequence
        random.random()  # Advance again
        value1 = random.random()

        set_deterministic_seed(42)
        random.random()  # Advance the sequence
        random.random()  # Advance again
        value2 = random.random()

        assert value1 == value2, "Resetting seed should reset sequence"

    def test_numpy_sequence_reset(self):
        """NumPy random sequence should reset with same seed."""
        set_deterministic_seed(42)
        np.random.rand(10)  # Advance sequence
        array1 = np.random.rand(5)

        set_deterministic_seed(42)
        np.random.rand(10)  # Advance sequence
        array2 = np.random.rand(5)

        assert np.array_equal(array1, array2), "NumPy sequence should reset"

    def test_accepts_different_seed_types(self):
        """Should accept different integer seed values."""
        for seed in [0, 1, 42, 12345, 999999]:
            set_deterministic_seed(seed)
            value = random.random()
            assert isinstance(value, float), f"Seed {seed} should work"
