# Test Fixtures

Deterministic synthetic OHLC fixtures used for indicator, signal, and risk tests.

## Files

- `fixture_trend_example.csv` upward drift with small pullbacks
- `fixture_flat_prices.csv` near-zero volatility sequence
- `fixture_spike_outlier.csv` single large spike candle then stabilization

All fixtures follow column ordering: timestamp, open, high, low, close. Row counts within 10–300 supported range.

See `specs/003-update-001-tests/fixture-manifest.md` and forthcoming `tests/fixtures/manifest.yaml` for metadata.
