# Feature Specification: Dynamic Visualization Indicators

**Feature Branch**: `017-dynamic-viz-indicators`
**Created**: 2025-12-21
**Status**: Draft
**Input**: User description: "Remove hardcoded indicators from visualization module. Strategies should expose their required indicators via get_visualization_config() method."
**Related Issue**: #37

## User Scenarios & Testing _(mandatory)_

### User Story 1 - Strategy-Defined Visualization Config (Priority: P1)

A strategy developer wants their strategy to control which indicators appear in the visualization output. When they define a new strategy, they specify the exact indicators (EMAs, oscillators) that should be visualized along with their display properties (colors, labels), ensuring that only relevant indicators for their strategy appear on the chart.

**Why this priority**: This is the core feature that enables decoupling - without this, all other stories are not possible. It directly addresses the primary pain point of hardcoded indicator patterns.

**Independent Test**: Can be fully tested by creating a strategy with visualization config and verifying that running a backtest with that strategy produces a chart showing only the configured indicators with the specified colors.

**Acceptance Scenarios**:

1. **Given** a strategy with `get_visualization_config()` returning `{"price_overlays": [{"name": "ema20", "color": "#FFD700"}]}`, **When** a backtest is run and visualization is generated, **Then** the chart displays only the ema20 indicator with gold color.
2. **Given** a strategy with oscillator config `{"oscillators": [{"name": "stoch_rsi", "color": "cyan"}]}`, **When** visualization is generated, **Then** the oscillator panel displays only stoch_rsi in cyan.
3. **Given** a strategy returning visualization config with custom labels, **When** visualization is generated, **Then** the legend shows the custom labels instead of column names.

---

### User Story 2 - Backward Compatible Auto-Detection (Priority: P2)

An existing user has developed their own strategy that does not implement the visualization config method. When they run a backtest with visualization, the system automatically detects available indicators in the data and displays them using sensible defaults, ensuring existing workflows are not broken.

**Why this priority**: Ensures existing strategies and workflows continue to work without modification. Critical for adoption without forcing immediate code changes.

**Independent Test**: Can be tested by running a backtest with an existing strategy that lacks `get_visualization_config()` and verifying that indicators are still auto-detected and displayed.

**Acceptance Scenarios**:

1. **Given** a strategy without `get_visualization_config()` method, **When** visualization is generated, **Then** the system falls back to auto-detecting indicators from column names (ema, sma, rsi, stoch patterns).
2. **Given** a strategy without visualization config and data containing ema20 and rsi14 columns, **When** visualization is generated, **Then** both indicators appear with default colors.

---

### User Story 3 - Visible but Non-Overpowering Color Scheme (Priority: P3)

A user viewing a backtest chart wants to clearly see indicator lines without them obscuring the price action. The indicator colors should have sufficient contrast against the dark chart background while using muted/pastel tones that don't overpower the candlesticks.

**Why this priority**: Improves usability but doesn't change core functionality. Can be applied as a refinement after P1 and P2 are complete.

**Independent Test**: Can be tested by visual inspection of generated charts, verifying that indicator lines are visible but candlesticks remain the dominant visual element.

**Acceptance Scenarios**:

1. **Given** a visualization with multiple indicators, **When** the chart is rendered, **Then** all indicator lines are visible against the dark background with sufficient contrast.
2. **Given** indicator colors chosen by the strategy, **When** the chart is rendered, **Then** the indicator lines use colors that are distinguishable from each other and don't overpower the candlesticks.

---

### Edge Cases

- What happens when a strategy returns an empty visualization config? → Display price chart only with no indicator overlays.
- How does the system handle indicator names in the config that don't exist in the data? → Skip missing indicators silently with a warning log.
- What happens when both strategy config and auto-detection find indicators? → Strategy config takes precedence; auto-detection is only used when no config is provided.
- How does the system handle invalid color specifications? → Fall back to a default color and log a warning.

## Requirements _(mandatory)_

### Functional Requirements

- **FR-001**: Strategies MUST be able to expose visualization configuration via a `get_visualization_config()` method on the `Strategy` protocol.
- **FR-002**: The visualization configuration MUST support defining price overlay indicators (EMAs, SMAs, etc.) with name, color, and optional label.
- **FR-003**: The visualization configuration MUST support defining oscillator indicators (RSI, StochRSI, etc.) with name, color, and optional label.
- **FR-004**: The `_create_indicator_overlays()` function MUST accept an optional visualization configuration parameter.
- **FR-005**: When visualization config is provided, the system MUST use it exclusively instead of auto-detection.
- **FR-006**: When no visualization config is provided (method returns None or is not implemented), the system MUST fall back to current auto-detection behavior.
- **FR-007**: Default indicator colors MUST be visible on dark backgrounds but not overpower the main price chart.
- **FR-008**: The system MUST log warnings for indicator names in config that don't match available data columns.
- **FR-009**: The `TrendPullbackStrategy` MUST be updated to implement `get_visualization_config()` with appropriate colors for its indicators.

### Key Entities

- **VisualizationConfig**: Configuration object containing:
  - `price_overlays`: List of price-scale indicator configs (name, color, label)
  - `oscillators`: List of oscillator indicator configs (name, color, label, optional y-axis bounds)
- **IndicatorDisplayConfig**: Individual indicator display settings (name, color, label)
- **Strategy (extended)**: Protocol extended with optional `get_visualization_config()` method

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: Strategies can define their own visualization configuration without modifying the visualization module.
- **SC-002**: Existing strategies without visualization config continue to work unchanged (100% backward compatibility).
- **SC-003**: All indicator colors are visible on the default dark chart background when tested against WCAG 2.1 contrast guidelines.
- **SC-004**: New strategies added to the codebase do not require any changes to `datashader_viz.py`.
- **SC-005**: The TrendPullbackStrategy displays its 5 indicators (ema20, ema50, atr14, rsi14, stoch_rsi) with distinct, visible colors.

## Assumptions

- The existing auto-detection logic based on column name patterns (ema, sma, rsi, stoch, etc.) is sufficient for fallback behavior.
- Strategies have access to their indicator requirements via the existing `metadata.required_indicators` property.
- The visualization module already correctly handles missing indicator columns by skipping them.
- The `get_visualization_config()` method can reasonably return static configuration since strategies know their indicator requirements at definition time.
