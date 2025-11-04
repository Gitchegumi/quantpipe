"""
OpenAPI contract validation tests for multi-strategy backtesting API.

Tests verify that the conceptual REST contract (openapi.yaml) examples
are valid and align with the implemented data structures.
"""

# pylint: disable=unused-import, redefined-outer-name

import json
from pathlib import Path

import pytest
import yaml


@pytest.fixture
def openapi_spec():
    """Load OpenAPI specification from contracts directory."""
    spec_path = (
        Path(__file__).parent.parent.parent
        / "specs"
        / "006-multi-strategy"
        / "contracts"
        / "openapi.yaml"
    )
    with open(spec_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_openapi_spec_loads(openapi_spec):
    """Test that OpenAPI spec loads successfully."""
    assert openapi_spec is not None
    assert openapi_spec["openapi"] == "3.1.0"
    assert (
        openapi_spec["info"]["title"] == "Multi-Strategy Backtesting API (Conceptual)"
    )


def test_strategy_schema_structure(openapi_spec):
    """Test Strategy schema has required fields."""
    strategy_schema = openapi_spec["components"]["schemas"]["Strategy"]
    assert "id" in strategy_schema["properties"]
    assert "name" in strategy_schema["properties"]
    assert "tags" in strategy_schema["properties"]
    assert strategy_schema["properties"]["tags"]["type"] == "array"


def test_backtest_request_schema_required_fields(openapi_spec):
    """Test BacktestRequest schema has required fields."""
    backtest_schema = openapi_spec["components"]["schemas"]["BacktestRequest"]
    assert "strategies" in backtest_schema["required"]
    assert "dataset_ref" in backtest_schema["required"]
    assert "strategies" in backtest_schema["properties"]
    assert "aggregate" in backtest_schema["properties"]
    assert "weights" in backtest_schema["properties"]


def test_portfolio_aggregate_schema_structure(openapi_spec):
    """Test PortfolioAggregate schema includes aggregation fields."""
    portfolio_schema = openapi_spec["components"]["schemas"]["PortfolioAggregate"]
    properties = portfolio_schema["properties"]

    # Core aggregation fields
    assert "strategies_count" in properties
    assert "weights_applied" in properties
    assert "aggregate_pnl" in properties
    assert "aggregate_drawdown" in properties
    assert "aggregate_volatility" in properties

    # Risk management fields
    assert "global_abort_triggered" in properties
    assert "risk_breaches" in properties

    # Reproducibility fields
    assert "deterministic_run_id" in properties


def test_risk_limits_schema_structure(openapi_spec):
    """Test RiskLimits schema has position/loss controls."""
    risk_schema = openapi_spec["components"]["schemas"]["RiskLimits"]
    properties = risk_schema["properties"]

    assert "max_position_size" in properties
    assert "daily_loss_limit" in properties
    assert "global_drawdown_limit" in properties
    assert "max_trade_notional" in properties


def test_strategy_result_schema_structure(openapi_spec):
    """Test StrategyResult includes metrics and halt status."""
    result_schema = openapi_spec["components"]["schemas"]["StrategyResult"]
    properties = result_schema["properties"]

    assert "strategy_id" in properties
    assert "metrics" in properties
    assert "halted" in properties
    assert "halt_reason" in properties
    assert "risk_events" in properties


def test_run_manifest_schema_structure(openapi_spec):
    """Test RunManifest includes reproducibility metadata."""
    manifest_schema = openapi_spec["components"]["schemas"]["RunManifest"]
    properties = manifest_schema["properties"]

    assert "run_id" in properties
    assert "timestamp_start" in properties
    assert "timestamp_end" in properties
    assert "strategies" in properties
    assert "weights_mode" in properties
    assert "data_manifest_ref" in properties
    assert "correlation_status" in properties
    assert "deterministic_run_id" in properties
    assert "version_hash" in properties


def test_all_endpoints_defined(openapi_spec):
    """Test that all required endpoints are defined."""
    paths = openapi_spec["paths"]

    assert "/strategies" in paths
    assert "/strategies/{id}" in paths
    assert "/backtests" in paths
    assert "/backtests/{runId}" in paths


def test_list_strategies_endpoint(openapi_spec):
    """Test GET /strategies endpoint definition."""
    list_endpoint = openapi_spec["paths"]["/strategies"]["get"]

    assert list_endpoint["operationId"] == "listStrategies"
    assert "200" in list_endpoint["responses"]

    response_schema = list_endpoint["responses"]["200"]["content"]["application/json"][
        "schema"
    ]
    assert response_schema["type"] == "array"


def test_register_strategy_endpoint(openapi_spec):
    """Test POST /strategies/{id} endpoint definition."""
    register_endpoint = openapi_spec["paths"]["/strategies/{id}"]["post"]

    assert register_endpoint["operationId"] == "registerStrategy"
    assert "201" in register_endpoint["responses"]
    assert "400" in register_endpoint["responses"]
    assert register_endpoint["requestBody"]["required"] is True


def test_run_backtest_endpoint(openapi_spec):
    """Test POST /backtests endpoint definition."""
    run_endpoint = openapi_spec["paths"]["/backtests"]["post"]

    assert run_endpoint["operationId"] == "runBacktest"
    assert "202" in run_endpoint["responses"]
    assert "400" in run_endpoint["responses"]


def test_get_aggregate_results_endpoint(openapi_spec):
    """Test GET /backtests/{runId} endpoint definition."""
    get_endpoint = openapi_spec["paths"]["/backtests/{runId}"]["get"]

    assert get_endpoint["operationId"] == "getAggregateResults"
    assert "200" in get_endpoint["responses"]
    assert "404" in get_endpoint["responses"]


def test_strategy_metrics_schema_completeness(openapi_spec):
    """Test StrategyMetrics schema includes key performance indicators."""
    metrics_schema = openapi_spec["components"]["schemas"]["StrategyMetrics"]
    properties = metrics_schema["properties"]

    assert "total_trades" in properties
    assert "gross_pnl" in properties
    assert "net_pnl" in properties
    assert "max_drawdown" in properties
    assert "volatility" in properties
    assert "win_rate" in properties
    assert "average_trade_pnl" in properties


def test_risk_event_schema_structure(openapi_spec):
    """Test RiskEvent schema has required fields."""
    risk_event_schema = openapi_spec["components"]["schemas"]["RiskEvent"]
    properties = risk_event_schema["properties"]

    assert "event_type" in properties
    assert "timestamp" in properties
    assert "detail" in properties
    assert properties["timestamp"]["format"] == "date-time"


def test_example_backtest_request_valid_structure():
    """Test that example BacktestRequest structure is valid."""
    example_request = {
        "strategies": [
            {
                "strategy_id": "alpha",
                "parameters": {"lookback": 20},
                "risk_limits": {"max_position_size": 100000, "daily_loss_limit": 5000},
                "weight": 0.6,
            },
            {
                "strategy_id": "beta",
                "parameters": {"threshold": 0.02},
                "risk_limits": {"max_position_size": 50000, "daily_loss_limit": 2500},
                "weight": 0.4,
            },
        ],
        "dataset_ref": "eurusd_test_2023",
        "aggregate": True,
        "global_drawdown_limit": 0.15,
    }

    # Verify required fields
    assert "strategies" in example_request
    assert "dataset_ref" in example_request
    assert len(example_request["strategies"]) == 2

    # Verify strategy structure
    for strategy in example_request["strategies"]:
        assert "strategy_id" in strategy
        assert "weight" in strategy
        assert 0 <= strategy["weight"] <= 1


def test_example_portfolio_aggregate_valid_structure():
    """Test that example PortfolioAggregate structure is valid."""
    example_aggregate = {
        "strategies_count": 2,
        "weights_applied": {"alpha": 0.6, "beta": 0.4},
        "aggregate_pnl": 1250.75,
        "aggregate_drawdown": 0.08,
        "aggregate_volatility": 0.12,
        "net_exposure_by_instrument": {"EURUSD": 75000},
        "total_trades": 45,
        "global_abort_triggered": False,
        "risk_breaches": [],
        "deterministic_run_id": "abc123def456",
    }

    # Verify core fields
    assert example_aggregate["strategies_count"] == 2
    assert sum(example_aggregate["weights_applied"].values()) == pytest.approx(1.0)
    assert isinstance(example_aggregate["aggregate_pnl"], (int, float))
    assert isinstance(example_aggregate["global_abort_triggered"], bool)
    assert isinstance(example_aggregate["risk_breaches"], list)


def test_schema_references_valid(openapi_spec):
    """Test that all schema references are valid."""
    schemas = openapi_spec["components"]["schemas"]

    # Check RiskLimits reference in Strategy
    strategy_schema = schemas["Strategy"]
    assert (
        strategy_schema["properties"]["default_risk_limits"]["$ref"]
        == "#/components/schemas/RiskLimits"
    )

    # Check nested schema references in BacktestRequest
    backtest_schema = schemas["BacktestRequest"]
    assert (
        backtest_schema["properties"]["strategies"]["items"]["$ref"]
        == "#/components/schemas/StrategyConfig"
    )

    # Check StrategyMetrics reference in StrategyResult
    result_schema = schemas["StrategyResult"]
    assert (
        result_schema["properties"]["metrics"]["$ref"]
        == "#/components/schemas/StrategyMetrics"
    )


def test_correlation_status_placeholder_documented(openapi_spec):
    """Test that correlation_status is included in schemas per FR-022."""
    # Check RunManifest includes correlation_status
    manifest_schema = openapi_spec["components"]["schemas"]["RunManifest"]
    assert "correlation_status" in manifest_schema["properties"]
    assert manifest_schema["properties"]["correlation_status"]["type"] == "string"
