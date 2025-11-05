"""Unit tests for deterministic run ID generation."""

from src.backtest.reproducibility import generate_deterministic_run_id


def test_identical_inputs_produce_identical_ids():
    """Same inputs should always produce same run ID."""
    id1 = generate_deterministic_run_id(
        strategies=["alpha", "beta"],
        weights=[0.6, 0.4],
        data_manifest_refs=["data/manifests/eurusd.json"],
    )
    id2 = generate_deterministic_run_id(
        strategies=["alpha", "beta"],
        weights=[0.6, 0.4],
        data_manifest_refs=["data/manifests/eurusd.json"],
    )
    assert id1 == id2
    assert len(id1) == 16  # Truncated to 16 chars


def test_different_strategies_produce_different_ids():
    """Changing strategy names should produce different IDs."""
    id1 = generate_deterministic_run_id(
        strategies=["alpha"],
        weights=[1.0],
        data_manifest_refs=["data.json"],
    )
    id2 = generate_deterministic_run_id(
        strategies=["beta"],
        weights=[1.0],
        data_manifest_refs=["data.json"],
    )
    assert id1 != id2


def test_different_weights_produce_different_ids():
    """Changing weights should produce different IDs."""
    id1 = generate_deterministic_run_id(
        strategies=["alpha", "beta"],
        weights=[0.6, 0.4],
        data_manifest_refs=["data.json"],
    )
    id2 = generate_deterministic_run_id(
        strategies=["alpha", "beta"],
        weights=[0.5, 0.5],
        data_manifest_refs=["data.json"],
    )
    assert id1 != id2


def test_different_data_manifests_produce_different_ids():
    """Changing data manifest refs should produce different IDs."""
    id1 = generate_deterministic_run_id(
        strategies=["alpha"],
        weights=[1.0],
        data_manifest_refs=["data1.json"],
    )
    id2 = generate_deterministic_run_id(
        strategies=["alpha"],
        weights=[1.0],
        data_manifest_refs=["data2.json"],
    )
    assert id1 != id2


def test_different_seeds_produce_different_ids():
    """Changing seed should produce different IDs."""
    id1 = generate_deterministic_run_id(
        strategies=["alpha"],
        weights=[1.0],
        data_manifest_refs=["data.json"],
        seed=0,
    )
    id2 = generate_deterministic_run_id(
        strategies=["alpha"],
        weights=[1.0],
        data_manifest_refs=["data.json"],
        seed=42,
    )
    assert id1 != id2


def test_config_params_affect_id():
    """Including config params should affect run ID."""
    id1 = generate_deterministic_run_id(
        strategies=["alpha"],
        weights=[1.0],
        data_manifest_refs=["data.json"],
        config_params={"ema_fast": 20},
    )
    id2 = generate_deterministic_run_id(
        strategies=["alpha"],
        weights=[1.0],
        data_manifest_refs=["data.json"],
        config_params={"ema_fast": 30},
    )
    assert id1 != id2


def test_none_config_params_handled():
    """None config params should not raise error."""
    run_id = generate_deterministic_run_id(
        strategies=["alpha"],
        weights=[1.0],
        data_manifest_refs=["data.json"],
        config_params=None,
    )
    assert isinstance(run_id, str)
    assert len(run_id) == 16
