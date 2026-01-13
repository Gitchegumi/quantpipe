"""
Risk configuration with pydantic validation.

RiskConfig defines the runtime configuration for risk management policies,
including stop-loss, take-profit, and position sizing parameters.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class StopPolicyConfig(BaseModel):
    """Configuration for stop-loss policy."""

    type: Literal[
        "ATR", "ATR_Trailing", "FixedPips", "FixedPips_Trailing", "MA_Trailing"
    ] = "ATR"
    multiplier: float = Field(default=2.0, ge=0.5, le=10.0)
    period: int = Field(default=14, ge=1, le=100)
    pips: float | None = Field(default=None, ge=1, le=500)
    ma_type: Literal["SMA", "EMA"] | None = "SMA"
    ma_period: int | None = Field(default=50, ge=1, le=500)
    trail_trigger_r: float = Field(default=1.0, ge=0.0)

    @model_validator(mode="after")
    def validate_policy_params(self) -> "StopPolicyConfig":
        """Validate that required parameters are present for each policy type."""
        if self.type in ("FixedPips", "FixedPips_Trailing") and self.pips is None:
            raise ValueError(f"{self.type} policy requires 'pips' parameter")
        if self.type == "MA_Trailing":
            if self.ma_type is None:
                raise ValueError("MA_Trailing policy requires 'ma_type' parameter")
            if self.ma_period is None:
                raise ValueError("MA_Trailing policy requires 'ma_period' parameter")
        return self


class TakeProfitPolicyConfig(BaseModel):
    """Configuration for take-profit policy."""

    type: Literal["RiskMultiple", "None"] = "RiskMultiple"
    rr_ratio: float = Field(default=2.0, ge=0.5, le=20.0)


class PositionSizerConfig(BaseModel):
    """Configuration for position sizing algorithm."""

    type: Literal["RiskPercent"] = "RiskPercent"


class RiskConfig(BaseModel):
    """
    Complete risk management configuration.

    RiskConfig holds all parameters needed to configure the RiskManager,
    including risk percentage, policy selections, and limits.

    Attributes:
        risk_pct: Risk per trade as percentage of account (e.g., 0.25 for 0.25%).
        stop_policy: Stop-loss policy configuration.
        take_profit_policy: Take-profit policy configuration.
        position_sizer: Position sizing algorithm configuration.
        max_position_size: Maximum position size in lots.
        pip_value: Value of 1 pip per lot in base currency.
        lot_step: Minimum lot size increment.
        blackout: Optional blackout configuration (Feature 023).

    Examples:
        >>> config = RiskConfig(risk_pct=0.25)
        >>> config.stop_policy.type
        'ATR'
        >>> config.take_profit_policy.rr_ratio
        2.0
    """

    risk_pct: float = Field(default=0.25, ge=0.01, le=10.0)
    stop_policy: StopPolicyConfig = Field(default_factory=StopPolicyConfig)
    take_profit_policy: TakeProfitPolicyConfig = Field(
        default_factory=TakeProfitPolicyConfig
    )
    position_sizer: PositionSizerConfig = Field(default_factory=PositionSizerConfig)
    max_position_size: float = Field(default=10.0, ge=0.01, le=100.0)
    pip_value: float = Field(default=10.0, ge=0.01)
    lot_step: float = Field(default=0.01, ge=0.001, le=1.0)
    # Optional blackout configuration (Feature 023 - Session Blackouts)
    # Uses Any to avoid circular import; validated at runtime
    blackout: Any = None

    @classmethod
    def from_dict(cls, config_dict: dict[str, Any]) -> "RiskConfig":
        """Create RiskConfig from a dictionary (e.g., parsed JSON)."""
        return cls.model_validate(config_dict)

    @classmethod
    def default(cls) -> "RiskConfig":
        """
        Create default RiskConfig matching legacy behavior.

        Default: 0.25% risk, 2× ATR stop, 2:1 TP.
        """
        return cls()


# Default configuration instance
DEFAULT_RISK_CONFIG = RiskConfig.default()
