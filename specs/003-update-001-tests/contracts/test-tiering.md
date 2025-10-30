# Contract: Test Tiering

## Marker Definitions

| Marker      | Purpose                                                        | Time Budget | Deterministic Required |
| ----------- | -------------------------------------------------------------- | ----------- | ---------------------- |
| unit        | Fast tests of isolated functions (indicators, sizing)          | <5s total   | Yes                    |
| integration | End-to-end strategy flows (signal generation, multi-step risk) | <30s total  | Yes                    |
| performance | Longer runtime/backtest style or stress scenarios              | <120s total | Preferred (seeded)     |

## Application Rules

- Each test file MUST include at least one tier marker; if omitted default to `unit`.
- Mixed markers allowed inside a single file only when clearly separated by function groups.
- Performance tests MUST NOT run in default fast CI job; require explicit flag (e.g., `-m performance`).
- No test may declare more than one tier marker simultaneously.

## Naming Conventions

- File names: `test_<area>_<behavior>.py` (e.g., `test_indicator_ema_warmup.py`).
- Performance files may suffix `_perf` (e.g., `test_strategy_trend_pullback_perf.py`).

## Determinism

- Randomness MUST be seeded at top of file if used.
- Time-dependent logic MUST stub/fix timestamp inputs via fixtures.

## Failure Expectations

- Unit tests: immediate precise assertion messaging.
- Integration tests: may aggregate multiple assertions; still avoid broad try/except swallowing.
- Performance tests: can assert upper runtime bounds using timing harness if needed.

## Out of Scope

- Live trading connectivity tests.
- External API latency measurements.
