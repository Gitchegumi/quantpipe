"""Contract tests for indicator mapping in performance reports.

This module validates that PerformanceReport indicator_names[] field
accurately reflects the strategy's declared indicators per FR-013.

Test Coverage:
- PerformanceReport.indicator_names matches IndicatorRegistry
- Indicator order preserved in report
- Empty indicator list handled correctly
- Multiple indicators validated
"""
# pylint: disable=redefined-outer-name,unused-argument
# Justification:
# - redefined-outer-name: pytest fixtures intentionally shadow fixture names
# - unused-argument: parameters in mock strategy required for interface compliance

import pytest

from src.models.performance_report import PerformanceReport
from src.strategy.indicator_registry import IndicatorRegistry


@pytest.fixture()
def mock_strategy_with_indicators():
    """Create mock strategy with declared indicators."""

    class MockMetadata:
        """Mock strategy metadata."""

        name = "test_strategy"
        version = "1.0.0"
        required_indicators = ["ema20", "ema50", "atr14"]

    class MockStrategy:
        """Mock strategy with indicators."""

        @property
        def metadata(self):
            """Return mock metadata."""
            return MockMetadata()

    return MockStrategy()


@pytest.fixture()
def mock_strategy_zero_indicators():
    """Create mock strategy with no indicators."""

    class MockMetadata:
        """Mock strategy metadata."""

        name = "zero_indicator_strategy"
        version = "1.0.0"
        required_indicators = []

    class MockStrategy:
        """Mock strategy with zero indicators."""

        @property
        def metadata(self):
            """Return mock metadata."""
            return MockMetadata()

    return MockStrategy()


def test_indicator_mapping_matches_registry(mock_strategy_with_indicators):
    """Test PerformanceReport indicator_names matches IndicatorRegistry.

    Validates:
    - Report indicator_names exactly matches registry
    - Order preserved from strategy declaration
    - All indicators included
    """
    # Create indicator registry from strategy
    registry = IndicatorRegistry(mock_strategy_with_indicators)
    declared_indicators = registry.get_indicator_names()

    # Create performance report with same indicators
    report = PerformanceReport(
        scan_duration_sec=10.5,
        simulation_duration_sec=8.3,
        peak_memory_mb=512.0,
        manifest_path="test/manifest.json",
        manifest_sha256="a" * 64,
        candle_count=100_000,
        signal_count=500,
        trade_count=450,
        equivalence_verified=True,
        progress_emission_count=50,
        progress_overhead_pct=0.5,
        indicator_names=list(declared_indicators),
        deterministic_mode=True,
    )

    # Verify exact match
    assert report.indicator_names == list(declared_indicators)
    assert len(report.indicator_names) == registry.get_indicator_count()


def test_indicator_mapping_order_preserved(mock_strategy_with_indicators):
    """Test indicator order preserved in PerformanceReport.

    Validates:
    - Indicator order matches declaration order
    - No reordering or sorting applied
    """
    # Create indicator registry
    registry = IndicatorRegistry(mock_strategy_with_indicators)
    declared_indicators = registry.get_indicator_names()

    # Create report with indicators in declared order
    report = PerformanceReport(
        scan_duration_sec=10.5,
        simulation_duration_sec=8.3,
        peak_memory_mb=512.0,
        manifest_path="test/manifest.json",
        manifest_sha256="a" * 64,
        candle_count=100_000,
        signal_count=500,
        trade_count=450,
        equivalence_verified=True,
        progress_emission_count=50,
        progress_overhead_pct=0.5,
        indicator_names=list(declared_indicators),
        deterministic_mode=True,
    )

    # Verify order preservation
    for i, indicator_name in enumerate(declared_indicators):
        assert report.indicator_names[i] == indicator_name


def test_indicator_mapping_zero_indicators(mock_strategy_zero_indicators):
    """Test PerformanceReport with zero indicators.

    Validates:
    - Empty indicator list handled correctly
    - Report creates successfully with zero indicators
    """
    # Create indicator registry for zero-indicator strategy
    registry = IndicatorRegistry(mock_strategy_zero_indicators)
    declared_indicators = registry.get_indicator_names()

    assert len(declared_indicators) == 0

    # Create report with empty indicator list
    report = PerformanceReport(
        scan_duration_sec=5.2,
        simulation_duration_sec=4.1,
        peak_memory_mb=256.0,
        manifest_path="test/manifest.json",
        manifest_sha256="b" * 64,
        candle_count=50_000,
        signal_count=100,
        trade_count=95,
        equivalence_verified=True,
        progress_emission_count=25,
        progress_overhead_pct=0.3,
        indicator_names=list(declared_indicators),
        deterministic_mode=False,
    )

    # Verify empty list handled correctly
    assert report.indicator_names == []
    assert len(report.indicator_names) == 0


def test_indicator_mapping_mismatch_detection():
    """Test detection of indicator mismatch between report and registry.

    Validates:
    - Mismatch can be detected programmatically
    - Extra indicators in report identified
    - Missing indicators in report identified
    """

    class MockMetadata:
        """Mock strategy metadata."""

        name = "test_strategy"
        version = "1.0.0"
        required_indicators = ["ema20", "ema50", "atr14"]

    class MockStrategy:
        """Mock strategy with indicators."""

        @property
        def metadata(self):
            """Return mock metadata."""
            return MockMetadata()

    strategy = MockStrategy()
    registry = IndicatorRegistry(strategy)
    declared_indicators = registry.get_indicator_names()

    # Create report with mismatched indicators (extra indicator)
    report_extra = PerformanceReport(
        scan_duration_sec=10.5,
        simulation_duration_sec=8.3,
        peak_memory_mb=512.0,
        manifest_path="test/manifest.json",
        manifest_sha256="a" * 64,
        candle_count=100_000,
        signal_count=500,
        trade_count=450,
        equivalence_verified=True,
        progress_emission_count=50,
        progress_overhead_pct=0.5,
        indicator_names=["ema20", "ema50", "atr14", "rsi14"],  # Extra indicator
        deterministic_mode=True,
    )

    # Detect mismatch
    assert set(report_extra.indicator_names) != set(declared_indicators)
    assert len(report_extra.indicator_names) > len(declared_indicators)

    # Create report with missing indicator
    report_missing = PerformanceReport(
        scan_duration_sec=10.5,
        simulation_duration_sec=8.3,
        peak_memory_mb=512.0,
        manifest_path="test/manifest.json",
        manifest_sha256="a" * 64,
        candle_count=100_000,
        signal_count=500,
        trade_count=450,
        equivalence_verified=True,
        progress_emission_count=50,
        progress_overhead_pct=0.5,
        indicator_names=["ema20", "ema50"],  # Missing atr14
        deterministic_mode=True,
    )

    # Detect mismatch
    assert set(report_missing.indicator_names) != set(declared_indicators)
    assert len(report_missing.indicator_names) < len(declared_indicators)


def test_indicator_mapping_audit_trail():
    """Test indicator mapping provides audit trail for performance tracking.

    Validates:
    - Report includes all indicators used during scan/simulation
    - Indicator list suitable for compliance audit
    - Report serialization includes indicator_names
    """

    class MockMetadata:
        """Mock strategy metadata."""

        name = "audit_strategy"
        version = "2.0.0"
        required_indicators = ["sma10", "sma20", "macd", "signal", "histogram"]

    class MockStrategy:
        """Mock strategy with multiple indicators."""

        @property
        def metadata(self):
            """Return mock metadata."""
            return MockMetadata()

    strategy = MockStrategy()
    registry = IndicatorRegistry(strategy)
    declared_indicators = registry.get_indicator_names()

    # Create comprehensive report
    report = PerformanceReport(
        scan_duration_sec=15.8,
        simulation_duration_sec=12.4,
        peak_memory_mb=1024.0,
        manifest_path="production/eurusd_2024.json",
        manifest_sha256="c" * 64,
        candle_count=500_000,
        signal_count=2000,
        trade_count=1950,
        equivalence_verified=True,
        progress_emission_count=100,
        progress_overhead_pct=0.8,
        indicator_names=list(declared_indicators),
        deterministic_mode=True,
    )

    # Verify audit trail completeness
    assert len(report.indicator_names) == 5
    assert report.indicator_names == list(declared_indicators)

    # Verify report can be converted to dict (for serialization/audit)
    report_dict = report.model_dump()
    assert "indicator_names" in report_dict
    assert report_dict["indicator_names"] == list(declared_indicators)
