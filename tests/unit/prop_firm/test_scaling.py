"""
Unit tests for Prop Firm Scaling Logic.
"""

import pytest
from datetime import datetime, timedelta, timezone
from src.risk.prop_firm.scaling import evaluate_scaling


def test_promotion(base_config, scaling_config, create_trade):
    """Test standard promotion after 4 months and 10% profit."""
    # Month 1: +$500
    # Month 2: +$600 (Total +1100 > 1000)
    # Months profitable: 2.
    # Time: must be past 4 months.

    trades = [
        create_trade(500.0, 0),  # Jan (M1) - Expires by May (Day 125)
        create_trade(600.0, 32),  # Feb (M2) - In Window
        create_trade(10.0, 60),  # Mar (M3) - In Window (Need 2nd profitable month)
        create_trade(50.0, 125),  # May (M5)
    ]

    report = evaluate_scaling(trades, base_config, scaling_config)

    # Expect 2 lives: Life 1 Promoted, Life 2 Started.
    assert len(report.lives) == 2
    assert report.lives[0].status == "PROMOTED"
    assert report.lives[0].end_balance == 11160.0  # 10000 + 1160
    assert report.lives[1].start_tier_balance == 20000.0  # Next tier


def test_reset_logic(base_config, scaling_config, create_trade):
    """Test reset to Tier 1 on failure."""
    # Scale up first (reuse logic or manually setup).
    # Step 1: Promote to Tier 2 ($20k).
    # May trade triggers promotion.
    trades = [
        create_trade(500.0, 0),
        create_trade(600.0, 32),
        create_trade(10.0, 80),  # Trade in M3/M4 to ensure profitable months count
        create_trade(50.0, 125),  # Triggers promotion
    ]

    # Step 2: Fail at Tier 2.
    # Tier 2 Balance $20,000. Drawdown Limit 5% ($1000).
    # Lose $2000.
    # Note: Trade sizing in create_trade uses risk_amount=$100 by default.
    # In scaling logic, we rescale PnL based on Tier.
    # Tier 2 (20k) / Base (10k) = 2x.
    # So a trade with pnl=$100 (1R) becomes $200.
    # To lose $2000, we need 10R loss? No, $1000 limit. 5R loss.

    # We add a trade later in time.
    trades.append(
        create_trade(
            -600.0, 130
        )  # 6R loss. Scaled -> $1200 loss. Violates $1000 limit.
    )

    report = evaluate_scaling(trades, base_config, scaling_config)

    assert len(report.lives) == 3
    # Life 1: Promoted
    # Life 2: Failed (Tier 2)
    # Life 3: In Progress (Tier 1 Reset)

    assert report.lives[1].status == "FAILED_DRAWDOWN"
    assert report.lives[1].start_tier_balance == 20000.0

    # Life 3 should be back at Tier 1 (10000)
    assert report.lives[2].start_tier_balance == 10000.0


def test_independent_pnl(base_config, scaling_config, create_trade):
    """Verify PnL is reset between lives."""
    # Life 1: +1100 (Promote)
    # Life 2: -600 (Fail)
    # Life 3: +100

    trades = [
        # Life 1
        create_trade(1100.0, 0),
        create_trade(10.0, 32),  # Ensure we have activity for months count if needed?
        # Actually logic needs 2 profitable months. M1 is +1100.
        # If we check at M5 (Day 125), M1 expires.
        # So we need M2, M3 to be profitable.
        create_trade(10.0, 60),
        create_trade(
            10.0, 125
        ),  # Trigger review (Must be >0 for profitable month check)
        # Life 2 (Tier 2, Scale 2.0.)
        # Loss -600 (base) -> -1200 (scaled). Fails 5% of 20k ($1000).
        create_trade(-600.0, 130),
        # Life 3 (Tier 1, Scale 1.0)
        create_trade(100.0, 140),
    ]

    report = evaluate_scaling(trades, base_config, scaling_config)

    # Life 1 PnL: 1100 + 10 + 10 + 10 = 1130.
    assert report.lives[0].pnl == 1130.0

    assert report.lives[1].pnl == -1200.0

    # Life 3 PnL: +100. (Start 10000, End 10100).
    # Should NOT satisfy Life 1's PnL.
    assert report.lives[2].pnl == 100.0


def test_sliding_window_promotion(base_config, scaling_config, create_trade):
    """Test promotion on a sliding window basis after month 4."""
    # Month 1-4: Accumulate some profit but not enough.
    # Target is 10% ($1000).
    # Month 1: +200
    # Month 2: +200
    # Month 3: +200
    # Month 4: +200  (Total +800 < 1000). Misses review at Month 4.

    # Month 5: +300 (Total +1100).
    # Expected: Keep checking after Month 4.
    # At Month 5 close, we have +1100 > 1000.
    # Last 4 months (M2, M3, M4, M5) are all profitable.
    # Should promote immediately.

    trades = [
        create_trade(200.0, 10),  # Month 1
        create_trade(200.0, 40),  # Month 2
        create_trade(200.0, 70),  # Month 3
        create_trade(200.0, 100),  # Month 4 (~Day 100 < 120).
        # At day 120 (Month 4 end), profit is 800. Fails.
        # Trigger explicit failure at end of Window 1 (Day 122).
        create_trade(
            10.0, 122
        ),  # Day 122 > 120. PnL 810 < 1000. Fails. Review bumped to M8.
        create_trade(
            300.0, 130
        ),  # Month 5. Day 130. Total 1110. Should promote now if sliding.
    ]

    report = evaluate_scaling(trades, base_config, scaling_config)

    # If fixed window, it waits for Month 8. Life 1 should end approx Day 240.
    # If sliding window, it promotes at Day 130.

    assert len(report.lives) == 2
    assert report.lives[0].status == "PROMOTED"
    # End date should be close to Day 130 (Month 5), not Month 8.

    # 2024 (Leap year) days: 31, 29, 31, 30, 31.
    # Day 130 is mid-May. Month 5.
    assert report.lives[0].end_date.month == 5
