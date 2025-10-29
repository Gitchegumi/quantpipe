"""
Unit tests for reproducibility tracker.

Tests hash stability, event accumulation, and verification logic.
"""

from datetime import datetime

from src.backtest.reproducibility import ReproducibilityTracker


class TestReproducibilityTracker:
    """Test suite for reproducibility tracking."""

    def test_initialization(self):
        """Test tracker initialization."""
        tracker = ReproducibilityTracker(
            parameters_hash="abc123",
            manifest_ref="data/manifest.json",
            version="0.1.0",
        )

        assert tracker.parameters_hash == "abc123"
        assert tracker.manifest_ref == "data/manifest.json"
        assert tracker.version == "0.1.0"
        assert tracker.candle_count == 0

    def test_update_candle_count(self):
        """Test candle count updates."""
        tracker = ReproducibilityTracker(
            parameters_hash="abc123",
            manifest_ref="data/manifest.json",
        )

        tracker.update_candle_count(100)
        assert tracker.candle_count == 100

        tracker.update_candle_count(250)
        assert tracker.candle_count == 250

    def test_deterministic_hash(self):
        """Test that identical trackers produce identical hashes."""
        tracker1 = ReproducibilityTracker(
            parameters_hash="abc123",
            manifest_ref="data/manifest.json",
            version="0.1.0",
        )
        tracker1.update_candle_count(100)

        tracker2 = ReproducibilityTracker(
            parameters_hash="abc123",
            manifest_ref="data/manifest.json",
            version="0.1.0",
        )
        tracker2.update_candle_count(100)

        hash1 = tracker1.finalize()
        hash2 = tracker2.finalize()

        assert hash1 == hash2

    def test_different_parameters_different_hash(self):
        """Test that different parameters produce different hashes."""
        tracker1 = ReproducibilityTracker(
            parameters_hash="abc123",
            manifest_ref="data/manifest.json",
        )
        tracker1.update_candle_count(100)

        tracker2 = ReproducibilityTracker(
            parameters_hash="xyz789",  # Different hash
            manifest_ref="data/manifest.json",
        )
        tracker2.update_candle_count(100)

        hash1 = tracker1.finalize()
        hash2 = tracker2.finalize()

        assert hash1 != hash2

    def test_different_manifest_different_hash(self):
        """Test that different manifests produce different hashes."""
        tracker1 = ReproducibilityTracker(
            parameters_hash="abc123",
            manifest_ref="data/manifest1.json",
        )
        tracker1.update_candle_count(100)

        tracker2 = ReproducibilityTracker(
            parameters_hash="abc123",
            manifest_ref="data/manifest2.json",  # Different manifest
        )
        tracker2.update_candle_count(100)

        hash1 = tracker1.finalize()
        hash2 = tracker2.finalize()

        assert hash1 != hash2

    def test_different_version_different_hash(self):
        """Test that different versions produce different hashes."""
        tracker1 = ReproducibilityTracker(
            parameters_hash="abc123",
            manifest_ref="data/manifest.json",
            version="0.1.0",
        )
        tracker1.update_candle_count(100)

        tracker2 = ReproducibilityTracker(
            parameters_hash="abc123",
            manifest_ref="data/manifest.json",
            version="0.2.0",  # Different version
        )
        tracker2.update_candle_count(100)

        hash1 = tracker1.finalize()
        hash2 = tracker2.finalize()

        assert hash1 != hash2

    def test_different_candle_count_different_hash(self):
        """Test that different candle counts produce different hashes."""
        tracker1 = ReproducibilityTracker(
            parameters_hash="abc123",
            manifest_ref="data/manifest.json",
        )
        tracker1.update_candle_count(100)

        tracker2 = ReproducibilityTracker(
            parameters_hash="abc123",
            manifest_ref="data/manifest.json",
        )
        tracker2.update_candle_count(200)  # Different count

        hash1 = tracker1.finalize()
        hash2 = tracker2.finalize()

        assert hash1 != hash2

    def test_add_event(self):
        """Test event recording affects hash."""
        tracker1 = ReproducibilityTracker(
            parameters_hash="abc123",
            manifest_ref="data/manifest.json",
        )
        tracker1.update_candle_count(100)

        tracker2 = ReproducibilityTracker(
            parameters_hash="abc123",
            manifest_ref="data/manifest.json",
        )
        tracker2.update_candle_count(100)
        tracker2.add_event("SIGNAL_GENERATED", "signal_id_12345")

        hash1 = tracker1.finalize()
        hash2 = tracker2.finalize()

        # Event should change hash
        assert hash1 != hash2

    def test_event_order_matters(self):
        """Test that event order affects hash."""
        tracker1 = ReproducibilityTracker(
            parameters_hash="abc123",
            manifest_ref="data/manifest.json",
        )
        tracker1.add_event("SIGNAL_GENERATED", "signal1")
        tracker1.add_event("TRADE_CLOSED", "execution1")
        tracker1.update_candle_count(100)

        tracker2 = ReproducibilityTracker(
            parameters_hash="abc123",
            manifest_ref="data/manifest.json",
        )
        tracker2.add_event("TRADE_CLOSED", "execution1")  # Reversed order
        tracker2.add_event("SIGNAL_GENERATED", "signal1")
        tracker2.update_candle_count(100)

        hash1 = tracker1.finalize()
        hash2 = tracker2.finalize()

        # Different order should produce different hash
        assert hash1 != hash2

    def test_verify_correct_hash(self):
        """Test verification succeeds with correct hash."""
        tracker = ReproducibilityTracker(
            parameters_hash="abc123",
            manifest_ref="data/manifest.json",
        )
        tracker.update_candle_count(100)

        expected_hash = tracker.finalize()

        # Create new tracker with same inputs
        tracker2 = ReproducibilityTracker(
            parameters_hash="abc123",
            manifest_ref="data/manifest.json",
        )
        tracker2.update_candle_count(100)

        assert tracker2.verify(expected_hash) is True

    def test_verify_incorrect_hash(self):
        """Test verification fails with incorrect hash."""
        tracker = ReproducibilityTracker(
            parameters_hash="abc123",
            manifest_ref="data/manifest.json",
        )
        tracker.update_candle_count(100)

        wrong_hash = "0" * 64  # Invalid hash

        assert tracker.verify(wrong_hash) is False

    def test_hash_length(self):
        """Test that finalized hash has correct SHA-256 length."""
        tracker = ReproducibilityTracker(
            parameters_hash="abc123",
            manifest_ref="data/manifest.json",
        )
        tracker.update_candle_count(100)

        final_hash = tracker.finalize()

        # SHA-256 hex string is 64 characters
        assert len(final_hash) == 64

    def test_multiple_finalizations(self):
        """Test that multiple finalize() calls produce same result."""
        tracker = ReproducibilityTracker(
            parameters_hash="abc123",
            manifest_ref="data/manifest.json",
        )
        tracker.update_candle_count(100)

        hash1 = tracker.finalize()
        hash2 = tracker.finalize()

        assert hash1 == hash2

    def test_start_time_recorded(self):
        """Test that start time is recorded."""
        before = datetime.utcnow()

        tracker = ReproducibilityTracker(
            parameters_hash="abc123",
            manifest_ref="data/manifest.json",
        )

        after = datetime.utcnow()

        assert before <= tracker.start_time <= after
