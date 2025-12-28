# Research: Strategy Templating Framework

**Feature**: 022-strategy-templating
**Date**: 2025-12-26

## Overview

This feature had no NEEDS CLARIFICATION markers after the `/speckit.clarify` phase. All key decisions were resolved during specification:

1. **Registration method**: Auto-register (clarified in spec)
2. **Scaffold location**: `src/strategy/<name>/` (clarified in spec)
3. **Validation behavior**: Hard fail with exit (clarified in spec)

## Technology Decisions

### Decision 1: Template Engine

**Decision**: Jinja2
**Rationale**: Industry-standard Python templating, already familiar pattern from Flask/Django ecosystems, excellent documentation
**Alternatives Considered**:

- String `.format()` - Too limited for multi-line templates with conditionals
- Mako - Less common, smaller community
- No templating (raw file copy) - Would require complex string replacement logic

### Decision 2: CLI Framework

**Decision**: Continue using argparse (existing pattern in `src/cli/`)
**Rationale**: Consistency with existing CLI modules (`run_backtest.py`), no new dependencies
**Alternatives Considered**:

- Click - Would add dependency, though more ergonomic
- Typer - Additional dependency, newer/less stable

### Decision 3: Validation Approach

**Decision**: Runtime validation at strategy load time using reflection
**Rationale**: Pythonic approach using `hasattr()`, `callable()`, and signature inspection. No compilation step needed.
**Alternatives Considered**:

- Static type checking only (mypy) - Doesn't catch runtime issues, users may not run mypy
- ABC/abstract base class - Would break existing strategies that use Protocol

### Decision 4: Reference Strategy Complexity

**Decision**: Simple EMA crossover momentum strategy
**Rationale**: Easy to understand, uses single well-known indicator, demonstrates minimal viable strategy
**Alternatives Considered**:

- Mean reversion strategy - More complex logic
- Copy of trend_pullback - Too complex for learning, doesn't show minimal implementation

## Existing Patterns Identified

### Strategy Protocol (from `src/strategy/base.py`)

```python
class Strategy(Protocol):
    @property
    def metadata(self) -> StrategyMetadata: ...
    def generate_signals(self, candles: list, parameters: dict) -> list: ...
    def scan_vectorized(...) -> tuple[...]: ...  # Optional
    def get_visualization_config(self) -> Optional[VisualizationConfig]: ...  # Optional
```

### Registry Pattern (from `src/strategy/registry.py`)

```python
registry.register(
    name="strategy-name",
    func=strategy_callable,
    tags=["tag1", "tag2"],
    version="1.0.0"
)
```

### Existing Strategy Structure (from `src/strategy/trend_pullback/`)

```text
trend_pullback/
├── __init__.py              # Exports strategy instance
├── strategy.py              # Main Strategy class
├── signal_generator.py      # Signal generation logic
├── htf_filter.py            # Optional modules
└── ...
```

## No Unresolved Issues

All technical unknowns resolved. Proceeding to Phase 1 data model and contracts.
