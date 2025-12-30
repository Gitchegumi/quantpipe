# Research: Parallel Indicator Parameter Sweep

**Feature**: 024-parallel-param-sweep
**Date**: 2025-12-30

## Technical Decisions

### 1. Parameter Discovery Approach

**Decision**: Use `IndicatorSpec.params` dict from registry for dynamic discovery

**Rationale**:

- Existing `IndicatorSpec` already has `params: dict[str, Any]` field with defaults
- No new data structures needed for parameter introspection
- Works with any indicator registered in the system

**Alternatives Considered**:

- Decorator-based parameter declaration → More refactoring, less alignment with existing registry
- Strategy-level parameter schemas → Would duplicate registry data

### 2. Semantic Indicator Naming

**Decision**: Extend `IndicatorSpec` registration to support semantic aliases

**Rationale**:

- Strategies declare semantic roles (`fast_ema`, `slow_ema`)
- Registry maps semantic names to parameterized indicator types
- Allows same EMA compute function with different defaults per role

**Implementation**:

```python
# Register semantic alias with different defaults
IndicatorSpec(
    name="fast_ema",
    requires=["close"],
    provides=["fast_ema"],
    compute=_ema_wrapper,
    params={"period": 20, "column": "close"},
)
```

### 3. Range Parsing

**Decision**: Simple regex-based parser for `start-end step increment` syntax

**Rationale**:

- Matches user expectation from GitHub issue examples
- Easy to validate and error on malformed input
- Pattern: `r"(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)\s+step\s+(\d+(?:\.\d+)?)"`

**Alternatives Considered**:

- JSON/YAML config files → Less interactive, more friction
- Python slicing syntax → Non-intuitive for quant users

### 4. Parallel Execution Foundation

**Decision**: Reuse existing `src/backtest/parallel.py` `run_parallel()` function

**Rationale**:

- Already implements `ProcessPoolExecutor` with worker capping
- Tested with efficiency metrics (≥70% target per SC-011)
- Handles task ordering and exception propagation

### 5. Constraint Validation

**Decision**: Post-generation filtering with skip count logged at end

**Rationale**:

- Per user clarification: skip invalid combinations silently
- Log count at end for transparency
- Simpler than pre-generation constraint solving

### 6. CLI Flag Design

**Decision**: Add `--test_range` flag to existing `run_backtest.py`

**Rationale**:

- Single entry point for all backtest modes
- Consistent with existing flag pattern (`--dry-run`, `--visualize`)
- No new CLI script needed

## Dependencies

| Dependency         | Version  | Purpose                                 |
| ------------------ | -------- | --------------------------------------- |
| Rich               | existing | Interactive prompts with formatting     |
| itertools          | stdlib   | `product()` for cartesian sweep         |
| concurrent.futures | stdlib   | `ProcessPoolExecutor` (via parallel.py) |

## Integration Points

1. **CLI**: `src/cli/run_backtest.py` - add `--test_range` argument
2. **Registry**: `src/indicators/registry/builtins.py` - add semantic indicator aliases
3. **Strategy**: `src/strategy/trend_pullback/strategy.py` - update `required_indicators` to semantic names
4. **Parallel**: `src/backtest/parallel.py` - reuse existing `run_parallel()`
