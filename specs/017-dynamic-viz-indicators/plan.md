# Implementation Plan: Dynamic Visualization Indicators

**Branch**: `017-dynamic-viz-indicators` | **Date**: 2025-12-21 | **Spec**: [spec.md](file:///e:/GitHub/trading-strategies/specs/017-dynamic-viz-indicators/spec.md)
**Input**: Feature specification from `/specs/017-dynamic-viz-indicators/spec.md`

## Summary

Remove hardcoded indicator patterns (ema20, ema50, rsi14, stoch_rsi) from the visualization module by introducing a `get_visualization_config()` method on the Strategy protocol. This enables strategies to control their own visualization appearance while maintaining full backward compatibility through auto-detection fallback.

## Technical Context

**Language/Version**: Python 3.13
**Primary Dependencies**: HoloViews 1.19+, hvplot 0.10+, Datashader 0.16+, Panel 1.4+, Bokeh 3.4+
**Storage**: N/A (in-memory visualization)
**Testing**: pytest (existing test infrastructure in `tests/visualization/`)
**Target Platform**: Desktop browser (HTML output via Panel/Bokeh)
**Project Type**: Single project
**Performance Goals**: Visualization rendering time unchanged from current implementation
**Constraints**: Must maintain 100% backward compatibility with existing strategies
**Scale/Scope**: 2 source files modified, 1 data model added, 1 strategy updated

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

| Principle                          | Status  | Notes                                                         |
| ---------------------------------- | ------- | ------------------------------------------------------------- |
| I. Strategy-First Architecture     | ✅ PASS | Feature enables strategies to control their own visualization |
| VII. Model Parsimony               | ✅ PASS | Minimal config dataclass, no over-engineering                 |
| VIII. Code Quality & Documentation | ✅ PASS | Type hints, docstrings required for new code                  |
| IX. Dependency Management          | ✅ PASS | No new dependencies required                                  |
| X. Code Quality Automation         | ✅ PASS | All new code must pass Black, Ruff, Pylint (8.0+)             |
| XI. Commit Message Standards       | ✅ PASS | Commits will use `feat(017): ...` format                      |
| XII. Task Tracking                 | ✅ PASS | tasks.md will be maintained                                   |

**Gate Result**: ✅ All gates pass. No violations to justify.

## Project Structure

### Documentation (this feature)

```text
specs/017-dynamic-viz-indicators/
├── plan.md              # This file
├── research.md          # Phase 0 output (not needed - no unknowns)
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (N/A - no API contracts)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/
├── strategy/
│   ├── base.py                    # [MODIFY] Add get_visualization_config() to Protocol
│   └── trend_pullback/
│       └── strategy.py            # [MODIFY] Implement get_visualization_config()
├── models/
│   └── visualization_config.py    # [NEW] VisualizationConfig, IndicatorDisplayConfig
└── visualization/
    └── datashader_viz.py          # [MODIFY] Accept and use visualization config

tests/
├── unit/
│   └── test_visualization_config.py  # [NEW] Unit tests for config models
└── visualization/
    └── test_viz_config_integration.py # [NEW] Integration tests for viz config
```

**Structure Decision**: Single project layout maintained. New `visualization_config.py` model added under `src/models/`. Visualization module receives optional config parameter.

## Proposed Changes

### Models Component

#### [NEW] [visualization_config.py](file:///e:/GitHub/trading-strategies/src/models/visualization_config.py)

New dataclass module defining:

- `IndicatorDisplayConfig`: Individual indicator display settings (name, color, label)
- `VisualizationConfig`: Container with `price_overlays` and `oscillators` lists

Default colors designed for dark background visibility without overpowering candlesticks.

---

### Strategy Component

#### [MODIFY] [base.py](file:///e:/GitHub/trading-strategies/src/strategy/base.py)

Add optional `get_visualization_config()` method to the `Strategy` protocol:

- Returns `Optional[VisualizationConfig]`
- Default implementation returns `None` (triggers auto-detection)
- Method is optional - strategies without it use fallback behavior

#### [MODIFY] [strategy.py](file:///e:/GitHub/trading-strategies/src/strategy/trend_pullback/strategy.py)

Implement `get_visualization_config()` for TrendPullbackStrategy:

- Configure ema20, ema50 as price overlays
- Configure rsi14, stoch_rsi as oscillators
- Use muted, visible colors (gold, cyan, magenta tones)

---

### Visualization Component

#### [MODIFY] [datashader_viz.py](file:///e:/GitHub/trading-strategies/src/visualization/datashader_viz.py)

Update `_create_indicator_overlays()` function:

- Add optional `viz_config: Optional[VisualizationConfig]` parameter
- When config provided: use it exclusively, skip auto-detection
- When config is None: fall back to current pattern-matching logic
- Log warnings for missing indicator columns
- Thread config through from `plot_backtest_results()` caller

---

### Tests Component

#### [NEW] [test_visualization_config.py](file:///e:/GitHub/trading-strategies/tests/unit/test_visualization_config.py)

Unit tests for config models:

- IndicatorDisplayConfig creation and defaults
- VisualizationConfig with various configurations
- Color validation edge cases

#### [NEW] [test_viz_config_integration.py](file:///e:/GitHub/trading-strategies/tests/visualization/test_viz_config_integration.py)

Integration tests for visualization with config:

- Strategy with config produces expected overlays
- Strategy without config uses auto-detection (backward compat)
- Missing indicator columns logged as warnings

## Verification Plan

### Automated Tests

```bash
# Run all tests including new visualization config tests
cd src && poetry run pytest tests/ -v

# Run only visualization-related tests
cd src && poetry run pytest tests/visualization/ tests/unit/test_visualization_config.py -v

# Lint checks
poetry run black src/models/visualization_config.py src/strategy/ src/visualization/
poetry run ruff check src/models/visualization_config.py src/strategy/ src/visualization/
poetry run pylint src/models/visualization_config.py src/strategy/base.py src/visualization/datashader_viz.py --score=yes
```

### Manual Verification

1. Run existing backtest with TrendPullbackStrategy and confirm visualization shows ema20, ema50 overlays and rsi14/stoch_rsi oscillator panel with configured colors
2. Create a test strategy without `get_visualization_config()` and verify auto-detection still works (backward compatibility)
3. Visual inspection of chart colors for visibility on dark background

## Complexity Tracking

> No constitution violations. Table not needed.
