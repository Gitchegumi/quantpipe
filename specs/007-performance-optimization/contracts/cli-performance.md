# CLI Contract: Performance Optimization Flags

**Command Base**: `poetry run python -m src.cli.run_backtest`

## Flags

| Flag | Type | Default | Required | Validation | Description |
|------|------|---------|----------|------------|-------------|
| --data | path | (none) | yes | file exists | Path to dataset (CSV; Parquet if --use-parquet) |
| --direction | str | BOTH | yes | in {LONG, SHORT, BOTH} | Trade direction mode |
| --data-frac | float | 1.0 | no | 0 < value <= 1 | Fraction of leading rows processed |
| --profile | bool | false | no | bool | Emit profiling report artifact |
| --deterministic | bool | false | no | bool | Enforce reproducible run (seed RNG, ordered processing) |
| --max-workers | int | 1 | no | >=1 <= logical cores | Parallel parameter set workers |
| --benchmark-out | path | auto (`results/benchmarks/benchmark_<ts>.json`) | no | writable directory | Override benchmark artifact location |
| --sim-mode | str | batch | no | in {batch, event} | Simulation algorithm selection (event optional future) |
| --use-parquet | bool | false | no | requires pyarrow | Use Parquet reader if available |
| --log-frequency | int | 250 | no | >=1 | Trades between progress log updates |
| --memory-threshold-mb | int | 0 | no | >=0 | Warn if peak exceeds (>0 activates) |

## Derived Behavior

- When `--deterministic` set, internal seed applied and parallel execution may serialize trades if ordering affects floating arithmetic.
- Benchmark artifact always written (profiling independent); profiling adds hotspot/time breakdown.
- `--data-frac` applied before indicator cache computation; selected dataset slice defines all subsequent index references.
- If `--use-parquet` supplied without dependency, system logs a WARN and falls back to CSV.

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success (benchmarks + optional profiling written) |
| 2 | Validation error (flag or data-frac invalid) |
| 3 | Fidelity failure (results deviate beyond tolerance) |
| 4 | Unexpected exception (trace logged) |

## Validation Messages

| Condition | Message |
|-----------|---------|
| data-frac <=0 or >1 | "Invalid --data-frac: must be 0<frac<=1" |
| max-workers > cores | "Capping --max-workers to (logical core count)" |
| pyarrow missing with --use-parquet | "Parquet requested but dependency not found; using CSV." |
| memory threshold exceeded | "Peak memory exceeded configured threshold" |

## Logging Levels

- INFO: Phase transitions, summary metrics, benchmark path
- DEBUG: Detailed per-phase internal timings (if profiling)
- WARNING: Dependency fallback, threshold exceedances

## Deterministic Guarantees

- Identical seeds & parameters yield identical aggregate metrics within tolerance.
- Random sampling of parameter grids prohibited; parameter enumeration deterministic.

## Future Extensions (Not Implemented Yet)

- `--portion-index` for selecting non-leading segment of dataset (deferred)
- `--random-sample-frac` for uniform random sampling (deferred)
