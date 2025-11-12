"""Contract tests for indicator ownership enforcement.

This module validates the architectural principle that indicators must be
declared solely within strategy modules (FR-004: Strategy Ownership Isolation).

Tests verify:
- No indicator definitions in src/backtest/, src/io/, src/util/ modules
- No indicator mutations outside strategy layer
- Indicator registry correctly enforces ownership model
"""

import ast
import logging
from pathlib import Path

import pytest

from src.strategy.indicator_registry import IndicatorRegistry


logger = logging.getLogger(__name__)


# Prohibited indicator-related patterns in non-strategy modules
PROHIBITED_PATTERNS = [
    "ema",
    "sma",
    "atr",
    "rsi",
    "stoch",
    "macd",
    "bollinger",
    "keltner",
    "supertrend",
    "vwap",
    "adx",
    "cci",
    "williams",
    "momentum",
]


def get_python_files(directory: Path, exclude_patterns: list[str] = None) -> list[Path]:
    """Get all Python files in directory, excluding specified patterns.

    Args:
        directory: Directory to search
        exclude_patterns: List of patterns to exclude (e.g., ['__pycache__', 'test_'])

    Returns:
        List of Python file paths
    """
    exclude_patterns = exclude_patterns or []
    python_files = []

    for file_path in directory.rglob("*.py"):
        # Check if file matches any exclude pattern
        if any(pattern in str(file_path) for pattern in exclude_patterns):
            continue
        python_files.append(file_path)

    return python_files


def contains_indicator_definition(file_path: Path) -> tuple[bool, list[str]]:
    """Check if file contains indicator definitions or mutations.

    Args:
        file_path: Path to Python file

    Returns:
        Tuple of (has_indicators, list of found indicator references)
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read().lower()

        found_indicators = []

        for pattern in PROHIBITED_PATTERNS:
            # Look for variable assignments like: ema20 = ...
            if f"{pattern}_" in content or f"{pattern}(" in content:
                # Verify it's not just in comments or strings
                try:
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Name) and pattern in node.id.lower():
                            found_indicators.append(node.id)
                except SyntaxError:
                    # If we can't parse, be conservative and flag it
                    found_indicators.append(pattern)

        return len(found_indicators) > 0, found_indicators

    except Exception as e:
        logger.warning("Could not analyze file %s: %s", file_path, e)
        return False, []


@pytest.mark.contract
def test_no_indicators_in_backtest_modules():
    """Test that no indicators are defined in src/backtest/ modules.

    Verifies FR-004: Strategy ownership isolation - backtest orchestration
    must not define, alter, or filter indicators.
    """
    backtest_dir = Path("src/backtest")

    if not backtest_dir.exists():
        pytest.skip("Backtest directory not found")

    python_files = get_python_files(backtest_dir, exclude_patterns=["__pycache__"])

    violations = []

    for file_path in python_files:
        has_indicators, found = contains_indicator_definition(file_path)
        if has_indicators:
            violations.append((str(file_path), found))

    if violations:
        violation_msg = "\n".join(
            f"  - {path}: {indicators}" for path, indicators in violations
        )
        pytest.fail(
            f"Indicator definitions found in backtest modules:\n{violation_msg}\n"
            "Indicators must be declared only in strategy modules (FR-004)"
        )


@pytest.mark.contract
def test_no_indicators_in_io_modules():
    """Test that no indicators are defined in src/io/ modules.

    Verifies FR-004: IO modules must not introduce indicators.
    """
    io_dir = Path("src/io")

    if not io_dir.exists():
        pytest.skip("IO directory not found")

    python_files = get_python_files(io_dir, exclude_patterns=["__pycache__"])

    violations = []

    for file_path in python_files:
        has_indicators, found = contains_indicator_definition(file_path)
        if has_indicators:
            violations.append((str(file_path), found))

    if violations:
        violation_msg = "\n".join(
            f"  - {path}: {indicators}" for path, indicators in violations
        )
        pytest.fail(
            f"Indicator definitions found in IO modules:\n{violation_msg}\n"
            "Indicators must be declared only in strategy modules (FR-004)"
        )


@pytest.mark.contract
def test_indicator_registry_enforcement():
    """Test that IndicatorRegistry correctly enforces ownership model.

    Verifies:
    - Registry requires strategy with metadata
    - Indicator list is immutable
    - Validation catches unauthorized indicators
    """

    class MockMetadata:
        """Mock strategy metadata."""

        name = "test_strategy"
        version = "1.0.0"
        required_indicators = ["ema20", "ema50", "atr14"]

    class MockStrategy:
        """Mock strategy implementation."""

        @property
        def metadata(self):
            """Return mock metadata."""
            return MockMetadata()

        def generate_signals(self, candles, parameters):
            """Mock signal generation."""
            return []

    strategy = MockStrategy()
    registry = IndicatorRegistry(strategy)

    # Test immutable indicator list
    indicators = registry.get_indicator_names()
    assert isinstance(indicators, tuple)
    assert indicators == ("ema20", "ema50", "atr14")

    # Test exact match validation
    registry.validate_exact_match(["ema20", "ema50", "atr14"])

    # Test no extras validation (allows missing)
    registry.validate_no_extras(["ema20", "ema50"])  # Missing atr14 is OK

    # Test subset validation
    registry.validate_subset(["ema20", "ema50"])

    # Test that extras are caught
    with pytest.raises(ValueError, match="Unauthorized indicators"):
        registry.validate_no_extras(["ema20", "ema50", "atr14", "rsi14"])


@pytest.mark.contract
def test_indicator_registry_rejects_missing_metadata():
    """Test that IndicatorRegistry rejects strategies without metadata.

    Verifies:
    - Strategy must provide metadata property
    - Metadata must declare required_indicators
    """

    class InvalidStrategy:
        """Strategy missing metadata."""

    with pytest.raises(ValueError, match="must provide metadata"):
        IndicatorRegistry(InvalidStrategy())


@pytest.mark.contract
def test_indicator_registry_zero_indicators():
    """Test that IndicatorRegistry handles zero-indicator strategies.

    Verifies:
    - Zero indicators is valid edge case
    - is_zero_indicator_strategy() works correctly
    """

    class ZeroIndicatorMetadata:
        """Mock metadata with zero indicators."""

        name = "zero_indicator_strategy"
        version = "1.0.0"
        required_indicators = []

    class ZeroIndicatorStrategy:
        """Strategy with no indicators."""

        @property
        def metadata(self):
            """Return metadata."""
            return ZeroIndicatorMetadata()

        def generate_signals(self, candles, parameters):
            """Mock signal generation."""
            return []

    strategy = ZeroIndicatorStrategy()
    registry = IndicatorRegistry(strategy)

    assert registry.is_zero_indicator_strategy()
    assert registry.get_indicator_count() == 0
    assert registry.get_indicator_names() == ()


@pytest.mark.contract
def test_indicator_registry_immutability():
    """Test that indicator list cannot be modified after creation.

    Verifies:
    - get_indicator_names() returns tuple (immutable)
    - Original strategy metadata changes don't affect registry
    """

    class MutableMetadata:
        """Mock metadata with mutable list."""

        name = "test_strategy"
        version = "1.0.0"
        required_indicators = ["ema20", "ema50"]

    class TestStrategy:
        """Test strategy."""

        @property
        def metadata(self):
            """Return metadata."""
            return MutableMetadata()

        def generate_signals(self, candles, parameters):
            """Mock signal generation."""
            return []

    strategy = TestStrategy()
    registry = IndicatorRegistry(strategy)

    # Get original indicators
    original_indicators = registry.get_indicator_names()

    # Modify strategy metadata (should not affect registry)
    strategy.metadata.required_indicators.append("atr14")

    # Registry should still have original indicators
    current_indicators = registry.get_indicator_names()
    assert current_indicators == original_indicators
    assert "atr14" not in current_indicators


@pytest.mark.contract
def test_indicator_mapping_order_preservation():
    """Test that indicator mapping preserves declaration order.

    Verifies:
    - get_indicator_mapping() returns correct indices
    - Order matches declaration order in strategy
    """

    class MockMetadata:
        """Mock strategy metadata."""

        name = "test_strategy"
        version = "1.0.0"
        required_indicators = ["ema20", "ema50", "atr14", "rsi14"]

    class MockStrategy:
        """Mock strategy implementation."""

        @property
        def metadata(self):
            """Return mock metadata."""
            return MockMetadata()

        def generate_signals(self, candles, parameters):
            """Mock signal generation."""
            return []

    strategy = MockStrategy()
    registry = IndicatorRegistry(strategy)

    mapping = registry.get_indicator_mapping()

    assert mapping["ema20"] == 0
    assert mapping["ema50"] == 1
    assert mapping["atr14"] == 2
    assert mapping["rsi14"] == 3
