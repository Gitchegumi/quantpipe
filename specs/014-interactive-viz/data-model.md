# Data Model: Interactive Visualization

## Visualization Entities

### ChartConfiguration (Transient)

Configuration object used to pass user preferences to the visualization engine.

| Field        | Type      | Description                        |
| ------------ | --------- | ---------------------------------- |
| `title`      | str       | Title of the chart window/export   |
| `pair`       | str       | Symbol being visualized            |
| `timeframe`  | str       | Timeframe (e.g., "1m")             |
| `indicators` | list[str] | List of indicator names to overlay |

### LayerDefinition (Internal)

Defines a specific data layer on the chart.

| Field   | Type      | Description               |
| ------- | --------- | ------------------------- |
| `name`  | str       | Display name of the layer |
| `type`  | enum      | LINE, HISTOGRAM, MARKER   |
| `data`  | pd.Series | Time-series data points   |
| `color` | str       | Color code (hex/name)     |

## Data Flow

1. **CLI Context**: Holds `enriched_df` (Polars DataFrame with OHLCV + Indicators) and `BacktestResult` (Trade history).
2. **Transformer**: Extracts OHLCV columns and required Indicator columns from `enriched_df` -> Formats for `lightweight-charts`.
3. **Transformer**: Extracts executions from `BacktestResult` -> Formats as Markers.
4. **Renderer**: creating `Chart` object, adding series (Candlestick, Line, Histogram), and calling `chart.show()`.
