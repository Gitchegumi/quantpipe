"""Unit tests for configuration override and merge logic.

Tests the config_override module functions:
- merge_config
- validate_config_types
- apply_strategy_overrides

Validates FR-005 (per-strategy config overrides).
"""

import pytest
from src.strategy.config_override import (
    merge_config,
    validate_config_types,
    apply_strategy_overrides,
)


def test_merge_config_no_overrides():
    """Test merge with no overrides returns copy of base."""
    base = {"ema_fast": 20, "ema_slow": 50}

    result = merge_config(base, overrides=None)

    assert result == {"ema_fast": 20, "ema_slow": 50}
    assert result is not base  # Should be a copy


def test_merge_config_empty_overrides():
    """Test merge with empty overrides dict."""
    base = {"ema_fast": 20, "ema_slow": 50}

    result = merge_config(base, overrides={})

    assert result == {"ema_fast": 20, "ema_slow": 50}


def test_merge_config_single_override():
    """Test merging single parameter override."""
    base = {"ema_fast": 20, "ema_slow": 50, "atr_mult": 2.0}
    overrides = {"ema_fast": 12}

    result = merge_config(base, overrides)

    assert result == {"ema_fast": 12, "ema_slow": 50, "atr_mult": 2.0}


def test_merge_config_multiple_overrides():
    """Test merging multiple parameter overrides."""
    base = {"ema_fast": 20, "ema_slow": 50, "atr_mult": 2.0}
    overrides = {"ema_fast": 12, "atr_mult": 3.0}

    result = merge_config(base, overrides)

    assert result == {"ema_fast": 12, "ema_slow": 50, "atr_mult": 3.0}


def test_merge_config_unknown_keys_preserved():
    """Test that unknown override keys are added to result."""
    base = {"ema_fast": 20}
    overrides = {"ema_fast": 12, "new_param": 100}

    result = merge_config(base, overrides)

    assert result["ema_fast"] == 12
    assert result["new_param"] == 100


def test_merge_config_does_not_modify_base():
    """Test that merge does not mutate base config."""
    base = {"ema_fast": 20, "ema_slow": 50}
    overrides = {"ema_fast": 12}

    merge_config(base, overrides)

    assert base == {"ema_fast": 20, "ema_slow": 50}  # Unchanged


def test_validate_config_types_all_valid():
    """Test validation passes when all types correct."""
    config = {"ema_fast": 20, "ema_slow": 50, "atr_mult": 2.0}
    expected = {"ema_fast": int, "ema_slow": int, "atr_mult": float}

    validate_config_types(config, expected)  # Should not raise


def test_validate_config_types_missing_param_ignored():
    """Test validation ignores params not in config."""
    config = {"ema_fast": 20}
    expected = {"ema_fast": int, "ema_slow": int}

    validate_config_types(config, expected)  # Should not raise


def test_validate_config_types_wrong_type_raises_error():
    """Test validation raises TypeError for wrong type."""
    config = {"ema_fast": "not_an_int"}
    expected = {"ema_fast": int}

    with pytest.raises(TypeError, match="expected type int"):
        validate_config_types(config, expected)


def test_validate_config_types_float_int_mismatch():
    """Test validation catches float vs int mismatch."""
    config = {"ema_fast": 20.5}
    expected = {"ema_fast": int}

    with pytest.raises(TypeError, match="expected type int"):
        validate_config_types(config, expected)


def test_apply_strategy_overrides_no_overrides():
    """Test apply with None overrides returns base copy."""
    base = {"ema_fast": 20, "ema_slow": 50}

    result = apply_strategy_overrides("alpha", base, user_overrides=None)

    assert result == {"ema_fast": 20, "ema_slow": 50}
    assert result is not base


def test_apply_strategy_overrides_strategy_not_in_overrides():
    """Test apply when strategy has no specific overrides."""
    base = {"ema_fast": 20}
    overrides = {"beta": {"ema_fast": 12}}

    result = apply_strategy_overrides("alpha", base, overrides)

    assert result == {"ema_fast": 20}


def test_apply_strategy_overrides_strategy_specific():
    """Test apply with strategy-specific overrides."""
    base = {"ema_fast": 20, "ema_slow": 50}
    overrides = {
        "alpha": {"ema_fast": 12},
        "beta": {"ema_slow": 100},
    }

    result_alpha = apply_strategy_overrides("alpha", base, overrides)
    result_beta = apply_strategy_overrides("beta", base, overrides)

    assert result_alpha == {"ema_fast": 12, "ema_slow": 50}
    assert result_beta == {"ema_fast": 20, "ema_slow": 100}


def test_apply_strategy_overrides_multiple_params():
    """Test apply with multiple params overridden."""
    base = {"ema_fast": 20, "ema_slow": 50, "atr_mult": 2.0}
    overrides = {"alpha": {"ema_fast": 10, "atr_mult": 3.5}}

    result = apply_strategy_overrides("alpha", base, overrides)

    assert result == {"ema_fast": 10, "ema_slow": 50, "atr_mult": 3.5}


def test_merge_config_preserves_types():
    """Test that merge preserves value types."""
    base = {"int_param": 10, "float_param": 1.5, "str_param": "test"}
    overrides = {"int_param": 20}

    result = merge_config(base, overrides)

    assert isinstance(result["int_param"], int)
    assert isinstance(result["float_param"], float)
    assert isinstance(result["str_param"], str)


def test_apply_strategy_overrides_empty_override_dict():
    """Test apply when strategy has empty override dict."""
    base = {"ema_fast": 20}
    overrides = {"alpha": {}}

    result = apply_strategy_overrides("alpha", base, overrides)

    assert result == {"ema_fast": 20}


def test_validate_config_types_bool_type():
    """Test validation handles bool types correctly."""
    config = {"stop_on_breach": True, "use_atr": False}
    expected = {"stop_on_breach": bool, "use_atr": bool}

    validate_config_types(config, expected)  # Should not raise


def test_validate_config_types_list_type():
    """Test validation handles list types."""
    config = {"symbols": ["EURUSD", "GBPUSD"]}
    expected = {"symbols": list}

    validate_config_types(config, expected)  # Should not raise
