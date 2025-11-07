"""Unit tests for portfolio entity models."""

# pylint: disable=arguments-out-of-order

import pytest
from pydantic import ValidationError

from src.models.allocation import AllocationRequest, AllocationResponse
from src.models.correlation import CorrelationMatrix, CorrelationWindowState
from src.models.events import RuntimeFailureEvent
from src.models.portfolio import CurrencyPair, PortfolioConfig, SymbolConfig
from src.models.snapshots import PortfolioSnapshotRecord


class TestCurrencyPair:
    """Tests for CurrencyPair model."""

    def test_valid_currency_pair(self):
        """Test creating a valid currency pair."""
        pair = CurrencyPair(code="EURUSD")
        assert pair.code == "EURUSD"
        assert pair.base == "EUR"
        assert pair.quote == "USD"

    def test_invalid_length(self):
        """Test that invalid length raises ValidationError."""
        with pytest.raises(ValidationError):
            CurrencyPair(code="EUR")

    def test_lowercase_rejected(self):
        """Test that lowercase codes are rejected."""
        with pytest.raises(ValidationError):
            CurrencyPair(code="eurusd")

    def test_hashable(self):
        """Test that CurrencyPair is hashable."""
        pair1 = CurrencyPair(code="EURUSD")
        pair2 = CurrencyPair(code="EURUSD")
        assert hash(pair1) == hash(pair2)
        assert pair1 in {pair1, pair2}

    def test_str_representation(self):
        """Test string representation."""
        pair = CurrencyPair(code="GBPJPY")
        assert str(pair) == "GBPJPY"


class TestSymbolConfig:
    """Tests for SymbolConfig model."""

    def test_default_config(self):
        """Test creating config with defaults."""
        pair = CurrencyPair(code="EURUSD")
        config = SymbolConfig(pair=pair)
        assert config.enabled is True
        assert config.correlation_threshold_override is None
        assert config.base_weight is None

    def test_correlation_threshold_bounds(self):
        """Test correlation threshold validation."""
        pair = CurrencyPair(code="EURUSD")

        # Valid values
        SymbolConfig(pair=pair, correlation_threshold_override=0.0)
        SymbolConfig(pair=pair, correlation_threshold_override=0.5)
        SymbolConfig(pair=pair, correlation_threshold_override=1.0)

        # Invalid values
        with pytest.raises(ValidationError):
            SymbolConfig(pair=pair, correlation_threshold_override=-0.1)
        with pytest.raises(ValidationError):
            SymbolConfig(pair=pair, correlation_threshold_override=1.1)

    def test_negative_weight_rejected(self):
        """Test that negative weights are rejected."""
        pair = CurrencyPair(code="EURUSD")
        with pytest.raises(ValidationError):
            SymbolConfig(pair=pair, base_weight=-1.0)


class TestPortfolioConfig:
    """Tests for PortfolioConfig model."""

    def test_defaults(self):
        """Test default configuration values."""
        config = PortfolioConfig()
        assert config.correlation_threshold_default == 0.8
        assert config.snapshot_interval_candles == 50
        assert config.max_memory_growth_factor == 1.5
        assert config.abort_on_symbol_failure is False
        assert config.allocation_rounding_dp == 2

    def test_custom_values(self):
        """Test creating config with custom values."""
        config = PortfolioConfig(
            correlation_threshold_default=0.7,
            snapshot_interval_candles=100,
            abort_on_symbol_failure=True,
        )
        assert config.correlation_threshold_default == 0.7
        assert config.snapshot_interval_candles == 100
        assert config.abort_on_symbol_failure is True


class TestCorrelationWindowState:
    """Tests for CorrelationWindowState model."""

    def test_initialization(self):
        """Test creating a correlation window state."""
        pair_a = CurrencyPair(code="EURUSD")
        pair_b = CurrencyPair(code="GBPUSD")
        state = CorrelationWindowState(pair_a=pair_a, pair_b=pair_b)

        assert state.window == 100
        assert state.provisional_min == 20
        assert len(state.values_a) == 0
        assert len(state.values_b) == 0

    def test_update_before_provisional(self):
        """Test update returns None before provisional minimum."""
        pair_a = CurrencyPair(code="EURUSD")
        pair_b = CurrencyPair(code="GBPUSD")
        state = CorrelationWindowState(pair_a=pair_a, pair_b=pair_b)

        # Add 19 values (below provisional_min)
        for i in range(19):
            result = state.update(float(i), float(i))
            assert result is None

    def test_update_after_provisional(self):
        """Test update returns correlation after provisional minimum."""
        pair_a = CurrencyPair(code="EURUSD")
        pair_b = CurrencyPair(code="GBPUSD")
        state = CorrelationWindowState(pair_a=pair_a, pair_b=pair_b)

        # Add 20 perfectly correlated values
        for i in range(20):
            result = state.update(float(i), float(i))

        # Should return correlation now
        assert result is not None
        assert abs(result - 1.0) < 0.01  # Should be close to 1.0

    def test_is_ready(self):
        """Test is_ready method."""
        pair_a = CurrencyPair(code="EURUSD")
        pair_b = CurrencyPair(code="GBPUSD")
        state = CorrelationWindowState(pair_a=pair_a, pair_b=pair_b)

        assert not state.is_ready()

        for i in range(100):
            state.update(float(i), float(i))

        assert state.is_ready()


class TestCorrelationMatrix:
    """Tests for CorrelationMatrix model."""

    def test_make_key_ordering(self):
        """Test that make_key creates lexicographically ordered keys."""
        pair_a = CurrencyPair(code="EURUSD")
        pair_b = CurrencyPair(code="GBPUSD")

        key1 = CorrelationMatrix.make_key(pair_a, pair_b)
        key2 = CorrelationMatrix.make_key(pair_b, pair_a)

        assert key1 == key2
        assert key1 == "EURUSD:GBPUSD"

    def test_get_set_correlation(self):
        """Test getting and setting correlations."""
        matrix = CorrelationMatrix()
        pair_a = CurrencyPair(code="EURUSD")
        pair_b = CurrencyPair(code="GBPUSD")

        # Initially returns 0.0
        assert matrix.get_correlation(pair_a, pair_b) == 0.0

        # Set and retrieve
        matrix.set_correlation(pair_a, pair_b, 0.75)
        assert matrix.get_correlation(pair_a, pair_b) == 0.75

        # Symmetric access - intentionally reversed to test symmetry property
        # pylint: disable=arguments-out-of-order
        assert matrix.get_correlation(pair_b, pair_a) == 0.75


class TestAllocationRequest:
    """Tests for AllocationRequest model."""

    def test_valid_request(self):
        """Test creating a valid allocation request."""
        symbols = [CurrencyPair(code="EURUSD"), CurrencyPair(code="GBPUSD")]
        request = AllocationRequest(
            symbols=symbols,
            volatility={"EURUSD": 0.01, "GBPUSD": 0.015},
            capital=10000.0,
        )

        assert len(request.symbols) == 2
        assert request.capital == 10000.0

    def test_negative_volatility_rejected(self):
        """Test that negative volatility is rejected."""
        symbols = [CurrencyPair(code="EURUSD")]
        with pytest.raises(ValidationError):
            AllocationRequest(
                symbols=symbols, volatility={"EURUSD": -0.01}, capital=10000.0
            )

    def test_invalid_weights_sum(self):
        """Test that weights not summing to 1.0 are rejected."""
        symbols = [CurrencyPair(code="EURUSD"), CurrencyPair(code="GBPUSD")]
        with pytest.raises(ValidationError):
            AllocationRequest(
                symbols=symbols,
                volatility={"EURUSD": 0.01, "GBPUSD": 0.015},
                base_weights={"EURUSD": 0.3, "GBPUSD": 0.5},  # Sum = 0.8
                capital=10000.0,
            )


class TestAllocationResponse:
    """Tests for AllocationResponse model."""

    def test_valid_response(self):
        """Test creating a valid allocation response."""
        response = AllocationResponse(
            allocations={"EURUSD": 5000.0, "GBPUSD": 5000.0},
            diversification_ratio=0.85,
        )

        assert sum(response.allocations.values()) == 10000.0
        assert response.diversification_ratio == 0.85

    def test_negative_allocation_rejected(self):
        """Test that negative allocations are rejected."""
        with pytest.raises(ValidationError):
            AllocationResponse(
                allocations={"EURUSD": -100.0}, diversification_ratio=0.5
            )


class TestRuntimeFailureEvent:
    """Tests for RuntimeFailureEvent model."""

    def test_event_creation(self):
        """Test creating a runtime failure event."""
        pair = CurrencyPair(code="EURUSD")
        event = RuntimeFailureEvent(
            pair=pair, reason="Dataset read error: file not found"
        )

        assert event.pair.code == "EURUSD"
        assert "Dataset read error" in event.reason
        assert event.timestamp is not None

    def test_str_representation(self):
        """Test string representation."""
        pair = CurrencyPair(code="GBPJPY")
        event = RuntimeFailureEvent(pair=pair, reason="Test error")

        event_str = str(event)
        assert "GBPJPY" in event_str
        assert "Test error" in event_str


class TestPortfolioSnapshotRecord:
    """Tests for PortfolioSnapshotRecord model."""

    def test_snapshot_creation(self):
        """Test creating a portfolio snapshot."""
        from datetime import datetime

        snapshot = PortfolioSnapshotRecord(
            t=datetime.utcnow(),
            positions={"EURUSD": 1000.0, "GBPUSD": 1500.0},
            unrealized={"EURUSD": 50.0, "GBPUSD": -25.0},
            portfolio_pnl=125.0,
            exposure=0.45,
            diversification_ratio=0.78,
            corr_window=85,
        )

        assert len(snapshot.positions) == 2
        assert snapshot.portfolio_pnl == 125.0

    def test_to_json_dict(self):
        """Test JSON serialization."""
        from datetime import datetime

        now = datetime.utcnow()
        snapshot = PortfolioSnapshotRecord(
            t=now,
            positions={"EURUSD": 1000.0},
            portfolio_pnl=50.0,
        )

        json_dict = snapshot.to_json_dict()
        assert "t" in json_dict
        assert "positions" in json_dict
        assert "portfolio_pnl" in json_dict
        assert json_dict["portfolio_pnl"] == 50.0
