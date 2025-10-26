# Implementation Plan: Trend Pullback Continuation Strategy

**Branch**: `001-trend-pullback` | **Date**: 2025-10-25 | **Spec**: `./spec.md`
**Input**: Feature specification from `/specs/001-trend-pullback/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Develop a parsimonious FX trend-following strategy that enters after validated pullbacks in the prevailing EMA-defined trend. The system computes EMAs (20/50), detects structured pullbacks using price proximity + oscillator extremes, confirms reversals via candle patterns + momentum turn, sizes positions via risk % and ATR-based stops, and exits via fixed R or trailing logic with precedence rule. Backtesting engine provides reproducible metrics, deterministic signal IDs, streaming chunk ingestion for scalability, and observability (latency, slippage, drawdown curve). All design aligns with Constitution principles (strategy modularity, risk integration, reproducibility, monitoring, data provenance, parsimony).

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.11 (chosen for ecosystem breadth, numerical libs, readability)
**Primary Dependencies**: numpy (vector math), pandas (time series handling), ta-lib or custom EMA/ATR/RSI fallback implementation, pydantic (config validation), rich/logging (structured logs), pytest (tests)
**Storage**: Local file system for manifests & logs; raw market data external (excluded via .gitignore)
**Testing**: pytest + hypothesis (property tests for sizing & indicators) + custom fixture datasets
**Target Platform**: Cross-platform (primary dev on Windows; CI on Linux runner)
**Project Type**: Single library + CLI commands
**Performance Goals**: ≥50k candles/sec backtest throughput; p95 candle processing latency ≤5ms; memory footprint ≤150MB for 1y 1m data (single pair) during streaming
**Constraints**: Deterministic outputs, reproducibility hash, interpretable indicators only, modular strategy boundary
**Scale/Scope**: Initial focus: 1–3 FX pairs (EURUSD primary); extendable to portfolio later

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Compliance | Evidence | Action Needed |
|-----------|-----------|----------|---------------|
| Strategy-First Architecture | PASS | Spec isolates strategy module & backtest engine | None |
| Risk Management Integration | PASS | FR-006..FR-014 cover stops, sizing, drawdown halt | None |
| Backtesting & Validation | PASS | FR-012 metrics; SC-001..SC-008 success criteria | Add statistical significance test Phase 2 |
| Real-Time Performance Monitoring | PASS | FR-029 metrics design (adapt for live) | Implement live adapter later |
| Data Integrity & Security | PASS | Manifest concept + checksum (FR-013) | Add encryption for credentials in future live phase |
| Data Version Control & Provenance | PASS | Repro hash + manifest fields | None |
| Model Parsimony & Interpretability | PASS | EMA/RSI/ATR only, rationale documented | None |
| Risk Management Standards | PASS | Position limits, drawdown, volatility regime (FR-014/027) | None |

Gate Status: APPROVED (no blockers). Statistical significance evaluation scheduled post initial backtest (Phase 2 tasks).

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
src/
  indicators/        # EMA, ATR, RSI implementations (vectorized)
  strategy/          # trend_pullback/ module (signal logic, state machines)
  risk/              # position sizing, drawdown tracking
  backtest/          # engine (streaming ingestion, trade simulation)
  models/            # dataclasses/pydantic models (Candle, TrendState, TradeSignal, RunMetrics)
  io/                # manifest loading, chunked data readers
  cli/               # entrypoints: run-backtest, inspect-signals, validate-manifest
tests/
  unit/              # indicator math, signal predicates
  integration/       # end-to-end backtest scenarios
  performance/       # throughput, memory profiling harness
  fixtures/          # synthetic + sampled real candle sets (excluded raw large data)
```

**Structure Decision**: Single-project modular layout with domain-focused subpackages; avoids premature multi-repo complexity while isolating concerns for testability and future extraction.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |

## Post-Design Constitution Re-Evaluation (Phase 1)

| Principle | Status | New Evidence (Phase 1) | Follow-Up |
|-----------|--------|------------------------|-----------|
| Strategy-First Architecture | PASS | Contracts (`strategy_contracts.md`) define clear boundaries | None |
| Risk Management Integration | PASS | `interfaces.py` includes `RiskManager` Protocol | Add portfolio-level aggregator later |
| Backtesting & Validation | PASS | Quickstart outlines test targets; MetricsAggregator contract defined | Implement statistical significance test Phase 2 |
| Real-Time Performance Monitoring | PASS | ObservabilityReporter contract + latency metrics fields | Live adapter deferred |
| Data Integrity & Security | PASS | DataManifest fields + reproducibility hash design | Credential encryption out-of-scope now |
| Data Version Control & Provenance | PASS | Repro hash + manifest referencing in contracts | None |
| Model Parsimony & Interpretability | PASS | Indicators limited to EMA/RSI/ATR; Stoch RSI deferred | Revisit after baseline performance |
| Risk Management Standards | PASS | Position sizing, stops, drawdown in spec & contracts | Portfolio correlation limits deferred |

Re-Eval Result: APPROVED. No regressions introduced by Phase 1 artifacts.

## Artifact Index

| File | Purpose |
|------|---------|
| `spec.md` | Functional requirements & success criteria |
| `research.md` | Decision log & rationale |
| `data-model.md` | Entities, transitions, validation rules |
| `contracts/strategy_contracts.md` | Component interaction & guarantees |
| `contracts/interfaces.py` | Python Protocols for dependency injection |
| `quickstart.md` | Setup & usage onboarding |
| `plan.md` | Implementation roadmap & compliance tracking |

## Next Milestones

1. Implement indicator & state modules per contracts.
2. Build ingestion + manifest verifier.
3. Implement risk manager & execution simulator.
4. Add MetricsAggregator + reproducibility service.
5. Develop initial pytest suite (unit + integration).
6. Run baseline backtest; collect performance metrics.
7. Add statistical significance evaluation (p-value test) per Constitution.
8. Prepare tasks.md (Phase 2 command) for execution sequencing.
