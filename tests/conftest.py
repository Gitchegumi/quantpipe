"""
Pytest configuration and global fixtures.

This module provides shared test fixtures used across the test suite,
including parameter configurations, temporary file paths, and sample data.
"""

import random
import time
from pathlib import Path

import numpy as np
import pytest

from src.config.parameters import StrategyParameters


SEED = 42


def _apply_global_seed():
    """Apply global deterministic seed for tests.

    Ensures repeatable outcomes for any test relying on random or numpy generation.
    """
    random.seed(SEED)
    np.random.seed(SEED)


_apply_global_seed()


def pytest_sessionstart(session):  # noqa: D401
    """Record session start time for runtime smoke assertions.

    Stored on the config object as `_suite_start_time` for later retrieval
    by runtime tests (e.g., Phase 2 timing smoke test T018b).
    """
    session.config._suite_start_time = time.perf_counter()


@pytest.fixture()
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


@pytest.fixture()
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


@pytest.fixture()
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


@pytest.fixture()
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
