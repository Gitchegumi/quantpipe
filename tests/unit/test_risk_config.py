"""
Unit tests for RiskConfig schema and defaults.

Tests validate:
- RiskConfig pydantic validation
- Default values match specification
- Policy config constraints
- JSON deserialization
"""

from datetime import UTC, datetime

import pytest

from src.risk.config import RiskConfig, StopPolicyConfig, TakeProfitPolicyConfig


pytestmark = pytest.mark.unit


class TestRiskConfigDefaults:
    """Test RiskConfig default values."""

    def test_default_risk_pct(self):
        """Default risk percentage should be 0.25%."""
        config = RiskConfig()
        assert config.risk_pct == 0.25

    def test_default_stop_policy(self):
        """Default stop policy should be ATR with 2.0 multiplier."""
        config = RiskConfig()
        assert config.stop_policy.type == "ATR"
        assert config.stop_policy.multiplier == 2.0
        assert config.stop_policy.period == 14

    def test_default_tp_policy(self):
        """Default TP policy should be RiskMultiple with 2:1 ratio."""
        config = RiskConfig()
        assert config.take_profit_policy.type == "RiskMultiple"
        assert config.take_profit_policy.rr_ratio == 2.0

    def test_default_position_sizer(self):
        """Default sizer should be RiskPercent."""
        config = RiskConfig()
        assert config.position_sizer.type == "RiskPercent"

    def test_default_max_position_size(self):
        """Default max position size should be 10.0 lots."""
        config = RiskConfig()
        assert config.max_position_size == 10.0


class TestRiskConfigValidation:
    """Test RiskConfig validation constraints."""

    def test_risk_pct_minimum(self):
        """Risk percentage must be at least 0.01%."""
        with pytest.raises(ValueError):
            RiskConfig(risk_pct=0.001)

    def test_risk_pct_maximum(self):
        """Risk percentage must be at most 10%."""
        with pytest.raises(ValueError):
            RiskConfig(risk_pct=15.0)

    def test_valid_risk_pct(self):
        """Valid risk percentages should be accepted."""
        config = RiskConfig(risk_pct=1.0)
        assert config.risk_pct == 1.0

    def test_atr_multiplier_range(self):
        """ATR multiplier must be between 0.5 and 10."""
        # Valid multiplier
        config = RiskConfig(stop_policy=StopPolicyConfig(multiplier=3.0))
        assert config.stop_policy.multiplier == 3.0

    def test_rr_ratio_range(self):
        """RR ratio must be between 0.5 and 20."""
        config = RiskConfig(take_profit_policy=TakeProfitPolicyConfig(rr_ratio=3.0))
        assert config.take_profit_policy.rr_ratio == 3.0


class TestStopPolicyConfig:
    """Test StopPolicyConfig validation."""

    def test_atr_policy_no_pips_required(self):
        """ATR policies don't require pips parameter."""
        config = StopPolicyConfig(type="ATR")
        assert config.pips is None

    def test_fixed_pips_requires_pips(self):
        """FixedPips policy requires pips parameter."""
        with pytest.raises(ValueError, match="FixedPips.*requires.*pips"):
            StopPolicyConfig(type="FixedPips")

    def test_fixed_pips_with_pips(self):
        """FixedPips policy accepts pips parameter."""
        config = StopPolicyConfig(type="FixedPips", pips=50)
        assert config.pips == 50

    def test_trailing_policy_type(self):
        """ATR_Trailing is a valid policy type."""
        config = StopPolicyConfig(type="ATR_Trailing")
        assert config.type == "ATR_Trailing"


class TestRiskConfigFromDict:
    """Test RiskConfig.from_dict() method."""

    def test_from_empty_dict(self):
        """Empty dict should use all defaults."""
        config = RiskConfig.from_dict({})
        assert config.risk_pct == 0.25
        assert config.stop_policy.type == "ATR"

    def test_from_partial_dict(self):
        """Partial dict should override specified values."""
        config = RiskConfig.from_dict({"risk_pct": 0.5})
        assert config.risk_pct == 0.5
        assert config.stop_policy.type == "ATR"  # Default

    def test_from_full_dict(self):
        """Full dict should set all values."""
        config = RiskConfig.from_dict(
            {
                "risk_pct": 1.0,
                "stop_policy": {"type": "ATR_Trailing", "multiplier": 1.5},
                "take_profit_policy": {"type": "None"},
                "max_position_size": 5.0,
            }
        )
        assert config.risk_pct == 1.0
        assert config.stop_policy.type == "ATR_Trailing"
        assert config.stop_policy.multiplier == 1.5
        assert config.take_profit_policy.type == "None"
        assert config.max_position_size == 5.0


class TestDefaultRiskConfig:
    """Test the default() class method."""

    def test_default_matches_constructor(self):
        """default() should return same as empty constructor."""
        default_config = RiskConfig.default()
        constructor_config = RiskConfig()

        assert default_config.risk_pct == constructor_config.risk_pct
        assert default_config.stop_policy.type == constructor_config.stop_policy.type
        assert (
            default_config.take_profit_policy.rr_ratio
            == constructor_config.take_profit_policy.rr_ratio
        )
