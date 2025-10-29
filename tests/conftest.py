"""
Pytest configuration and global fixtures.

This module provides shared test fixtures used across the test suite,
including parameter configurations, temporary file paths, and sample data.
"""

from pathlib import Path

import pytest

from src.config.parameters import StrategyParameters


@pytest.fixture
def sample_parameters():
    """
    Provide default strategy parameters for testing.

    Returns:
        StrategyParameters instance with default configuration.

    Examples:
        >>> def test_something(sample_parameters):
        ...     assert sample_parameters.ema_fast == 20
    """
    return StrategyParameters()


@pytest.fixture
def custom_parameters():
    """
    Provide customizable strategy parameters factory.

    Returns:
        Callable that accepts parameter overrides and returns StrategyParameters.

    Examples:
        >>> def test_custom(custom_parameters):
        ...     params = custom_parameters(ema_fast=10, ema_slow=30)
        ...     assert params.ema_fast == 10
    """

    def _create_params(**overrides):
        return StrategyParameters(**overrides)

    return _create_params


@pytest.fixture
def temp_manifest_path(tmp_path):
    """
    Provide temporary path for manifest files.

    Args:
        tmp_path: pytest built-in temporary directory fixture.

    Returns:
        Path object pointing to temporary manifest file location.

    Examples:
        >>> def test_manifest(temp_manifest_path):
        ...     manifest_file = temp_manifest_path / "test_manifest.json"
        ...     manifest_file.write_text('{"pair": "EURUSD"}')
    """
    manifest_dir = tmp_path / "manifests"
    manifest_dir.mkdir(exist_ok=True)
    return manifest_dir


@pytest.fixture
def fixtures_dir():
    """
    Provide path to test fixtures directory.

    Returns:
        Path object pointing to tests/fixtures/ directory.

    Examples:
        >>> def test_load_fixture(fixtures_dir):
        ...     candles_file = fixtures_dir / "sample_candles_long.csv"
        ...     assert candles_file.exists()
    """
    return Path(__file__).parent / "fixtures"
