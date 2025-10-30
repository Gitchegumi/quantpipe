# Glossary: 001 Test Suite Alignment

Canonical definitions to eliminate ambiguity (referenced by `test-suite.md`).
\n## Deterministic

Outcome of a test run is invariant given identical inputs, environment, and seeded randomness. No dependence on wall-clock time, external services, or unseeded pseudo-random generators. If randomness is unavoidable, a fixed seed (e.g., `random.seed(42)`, `numpy.random.seed(42)`) MUST be set before value generation. Determinism is evaluated at the assertion level: expected indicator sequences, signal counts, and risk sizes remain identical across ≥3 consecutive runs.
\n## Redundant Test

A test is redundant if ALL of the following hold:

1. Setup (fixtures, parameters, initialization) is identical to another test or can be expressed via a parameterized variant.
2. Assertions duplicate logic or expected values already covered elsewhere (same indicator warm-up behavior, same risk sizing formula outcome, etc.).
3. The only differences are constant parameter enumerations better expressed through `@pytest.mark.parametrize`.

Redundant tests MUST be consolidated or removed (FR-003) provided coverage metrics (SC-001) remain unchanged.
\n## Flaky Test

Any test that fails ≥1 time in 3 consecutive deterministic runs OR exhibits non-deterministic timing variance beyond the performance tolerance (±20% of tier budget) without code changes. Flakiness triage requires stabilization before merge (FR-009). A test that intermittently raises different exceptions/messages qualifies as flaky even if final status is pass most runs.
\n## Warm-up Period

Initial sequence where indicator values (e.g., EMA, ATR) are NaN or unstable until the lookback length is satisfied. Stable value point is defined as the FIRST non-NaN value after the lookback window (e.g., EMA(20) stable starting at index 19). Tests assert correct count of NaNs and verify first stable value against expected numeric output.
\n## Fixture Manifest

Structured YAML file (`tests/fixtures/manifest.yaml`) enumerating each deterministic dataset with: `id`, `filename`, `scenario_type` (trend | flat | spike), `row_count`, `checksum` (SHA256), `seed` (if generated), `indicators_covered`, `created` (ISO timestamp), `notes`. Ensures reproducibility and traceability (FR-004, FR-005).
\n## Tier Runtime (Suite Time)

Runtime thresholds (<5s unit, <30s integration, <120s performance) apply to the cumulative wall-clock time of executing ALL tests in that marker group excluding environment setup (Poetry install). Individual test functions may be faster; threshold is not per-test. Measured with `time.perf_counter()` around `pytest -m <tier>` invocation. Success criteria allow ±20% tolerance for transient CI variance (SC-003..SC-007).
\n## Fixture Row Count Scope

Supported deterministic fixture size range is 10–300 rows. Below minimum (<10) risks insufficient warm-up coverage; above maximum (>300) risks unnecessary performance cost. Performance tier may temporarily stage larger slices but they are not treated as core deterministic fixtures.
