"""Multi-symbol portfolio backtesting components.

This package contains modules for executing backtests across multiple currency
pairs in two modes:
- Independent mode: Isolated per-symbol runs with shared context but no capital pooling
- Portfolio mode: Shared capital pool with correlation-aware position sizing

Modules:
    correlation_service: Rolling correlation computation
    allocation_engine: Capital allocation with correlation awareness
    orchestrator: Portfolio-level backtest coordination
    snapshot_logger: Periodic portfolio state persistence
    validation: Multi-symbol dataset validation
    errors: Custom exceptions for portfolio operations
"""
