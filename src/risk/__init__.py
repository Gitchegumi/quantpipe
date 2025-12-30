"""Risk management modules."""

from src.risk.config import RiskConfig, DEFAULT_RISK_CONFIG
from src.risk.manager import RiskManager
from src.risk.registry import PolicyRegistry, policy_registry
from src.risk.policies import (
    StopPolicy,
    TakeProfitPolicy,
    PositionSizer,
    RiskConfigurationError,
)

# Blackout module exports (Feature 023 - Session Blackouts)
from src.risk.blackout.config import (
    BlackoutConfig,
    NewsBlackoutConfig,
    SessionBlackoutConfig,
)

__all__ = [
    "RiskConfig",
    "DEFAULT_RISK_CONFIG",
    "RiskManager",
    "PolicyRegistry",
    "policy_registry",
    "StopPolicy",
    "TakeProfitPolicy",
    "PositionSizer",
    "RiskConfigurationError",
    # Blackout module
    "BlackoutConfig",
    "NewsBlackoutConfig",
    "SessionBlackoutConfig",
]
