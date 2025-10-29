"""
Unit tests for deterministic signal ID generation.

Tests SHA-256 hash generation, determinism, and parameter hash computation.
"""

from datetime import UTC, datetime

from src.strategy.id_factory import compute_parameters_hash, generate_signal_id


class TestGenerateSignalID:
    """Test suite for signal ID generation."""

    def test_deterministic_id(self):
        """Test that identical inputs produce identical IDs."""
        timestamp = datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC)

        id1 = generate_signal_id(
            pair="EURUSD",
            timestamp_utc=timestamp,
            direction="LONG",
            entry_price=1.10000,
            stop_price=1.09800,
            position_size=0.01,
            parameters_hash="abc123",
        )

        id2 = generate_signal_id(
            pair="EURUSD",
            timestamp_utc=timestamp,
            direction="LONG",
            entry_price=1.10000,
            stop_price=1.09800,
            position_size=0.01,
            parameters_hash="abc123",
        )

        assert id1 == id2

    def test_different_pair_different_id(self):
        """Test that different pairs produce different IDs."""
        timestamp = datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC)

        id1 = generate_signal_id(
            pair="EURUSD",
            timestamp_utc=timestamp,
            direction="LONG",
            entry_price=1.10000,
            stop_price=1.09800,
            position_size=0.01,
            parameters_hash="abc123",
        )

        id2 = generate_signal_id(
            pair="GBPUSD",
            timestamp_utc=timestamp,
            direction="LONG",
            entry_price=1.10000,
            stop_price=1.09800,
            position_size=0.01,
            parameters_hash="abc123",
        )

        assert id1 != id2

    def test_different_timestamp_different_id(self):
        """Test that different timestamps produce different IDs."""
        timestamp1 = datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC)
        timestamp2 = datetime(
            2025, 1, 15, 12, 0, 1, tzinfo=UTC
        )  # 1 second later

        id1 = generate_signal_id(
            pair="EURUSD",
            timestamp_utc=timestamp1,
            direction="LONG",
            entry_price=1.10000,
            stop_price=1.09800,
            position_size=0.01,
            parameters_hash="abc123",
        )

        id2 = generate_signal_id(
            pair="EURUSD",
            timestamp_utc=timestamp2,
            direction="LONG",
            entry_price=1.10000,
            stop_price=1.09800,
            position_size=0.01,
            parameters_hash="abc123",
        )

        assert id1 != id2

    def test_different_direction_different_id(self):
        """Test that different directions produce different IDs."""
        timestamp = datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC)

        id1 = generate_signal_id(
            pair="EURUSD",
            timestamp_utc=timestamp,
            direction="LONG",
            entry_price=1.10000,
            stop_price=1.09800,
            position_size=0.01,
            parameters_hash="abc123",
        )

        id2 = generate_signal_id(
            pair="EURUSD",
            timestamp_utc=timestamp,
            direction="SHORT",
            entry_price=1.10000,
            stop_price=1.10200,
            position_size=0.01,
            parameters_hash="abc123",
        )

        assert id1 != id2

    def test_different_price_different_id(self):
        """Test that different prices produce different IDs."""
        timestamp = datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC)

        id1 = generate_signal_id(
            pair="EURUSD",
            timestamp_utc=timestamp,
            direction="LONG",
            entry_price=1.10000,
            stop_price=1.09800,
            position_size=0.01,
            parameters_hash="abc123",
        )

        id2 = generate_signal_id(
            pair="EURUSD",
            timestamp_utc=timestamp,
            direction="LONG",
            entry_price=1.10500,  # Different entry
            stop_price=1.09800,
            position_size=0.01,
            parameters_hash="abc123",
        )

        assert id1 != id2

    def test_different_parameters_hash_different_id(self):
        """Test that different parameter hashes produce different IDs."""
        timestamp = datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC)

        id1 = generate_signal_id(
            pair="EURUSD",
            timestamp_utc=timestamp,
            direction="LONG",
            entry_price=1.10000,
            stop_price=1.09800,
            position_size=0.01,
            parameters_hash="abc123",
        )

        id2 = generate_signal_id(
            pair="EURUSD",
            timestamp_utc=timestamp,
            direction="LONG",
            entry_price=1.10000,
            stop_price=1.09800,
            position_size=0.01,
            parameters_hash="xyz789",  # Different hash
        )

        assert id1 != id2

    def test_id_length(self):
        """Test that signal ID has correct SHA-256 length."""
        timestamp = datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC)

        signal_id = generate_signal_id(
            pair="EURUSD",
            timestamp_utc=timestamp,
            direction="LONG",
            entry_price=1.10000,
            stop_price=1.09800,
            position_size=0.01,
            parameters_hash="abc123",
        )

        # SHA-256 hex string is 64 characters
        assert len(signal_id) == 64

    def test_price_precision(self):
        """Test that price precision affects ID."""
        timestamp = datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC)

        # Prices differing only in 7th decimal place
        id1 = generate_signal_id(
            pair="EURUSD",
            timestamp_utc=timestamp,
            direction="LONG",
            entry_price=1.100000,
            stop_price=1.098000,
            position_size=0.01,
            parameters_hash="abc123",
        )

        id2 = generate_signal_id(
            pair="EURUSD",
            timestamp_utc=timestamp,
            direction="LONG",
            entry_price=1.1000001,  # 7th decimal different
            stop_price=1.098000,
            position_size=0.01,
            parameters_hash="abc123",
        )

        # Should be same (6 decimal precision)
        assert id1 == id2


class TestComputeParametersHash:
    """Test suite for parameters hash computation."""

    def test_deterministic_hash(self):
        """Test that identical parameters produce identical hash."""
        params1 = {
            "ema_fast": 20,
            "ema_slow": 50,
            "rsi_period": 14,
            "position_risk_pct": 0.25,
        }

        params2 = {
            "ema_fast": 20,
            "ema_slow": 50,
            "rsi_period": 14,
            "position_risk_pct": 0.25,
        }

        hash1 = compute_parameters_hash(params1)
        hash2 = compute_parameters_hash(params2)

        assert hash1 == hash2

    def test_order_independent(self):
        """Test that parameter order doesn't affect hash."""
        params1 = {
            "ema_fast": 20,
            "ema_slow": 50,
            "rsi_period": 14,
        }

        params2 = {
            "rsi_period": 14,
            "ema_slow": 50,
            "ema_fast": 20,
        }

        hash1 = compute_parameters_hash(params1)
        hash2 = compute_parameters_hash(params2)

        assert hash1 == hash2

    def test_different_values_different_hash(self):
        """Test that different parameter values produce different hash."""
        params1 = {
            "ema_fast": 20,
            "ema_slow": 50,
        }

        params2 = {
            "ema_fast": 30,  # Different value
            "ema_slow": 50,
        }

        hash1 = compute_parameters_hash(params1)
        hash2 = compute_parameters_hash(params2)

        assert hash1 != hash2

    def test_different_keys_different_hash(self):
        """Test that different parameter names produce different hash."""
        params1 = {
            "ema_fast": 20,
            "ema_slow": 50,
        }

        params2 = {
            "ema_fast": 20,
            "ema_very_slow": 50,  # Different key
        }

        hash1 = compute_parameters_hash(params1)
        hash2 = compute_parameters_hash(params2)

        assert hash1 != hash2

    def test_hash_length(self):
        """Test that parameters hash has correct SHA-256 length."""
        params = {
            "ema_fast": 20,
            "ema_slow": 50,
        }

        params_hash = compute_parameters_hash(params)

        # SHA-256 hex string is 64 characters
        assert len(params_hash) == 64

    def test_empty_parameters(self):
        """Test hash computation with empty parameters."""
        params = {}

        params_hash = compute_parameters_hash(params)

        # Should still produce valid hash
        assert len(params_hash) == 64

    def test_nested_values(self):
        """Test hash computation with various value types."""
        params = {
            "int_val": 42,
            "float_val": 3.14159,
            "str_val": "test",
            "bool_val": True,
        }

        params_hash = compute_parameters_hash(params)

        # Should handle different types
        assert len(params_hash) == 64
