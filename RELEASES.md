# Release History

This document tracks all official releases of the trading-strategies project.

## Release Guidelines

- Follow [Semantic Versioning](https://semver.org/): MAJOR.MINOR.PATCH
- Create GitHub releases from this branch after merging to main
- Tag format: `v{version}` (e.g., `v0.0.1`, `v1.0.0`)
- Include changelog excerpt in release notes
- Attach any relevant artifacts (test results, benchmarks)

## Version Status

### Current Version: 0.0.1

- **Status**: Released
- **Date**: 2025-11-12
- **Branch**: 010-scan-sim-perf
- **Commit**: a723ed0
- **PR**: #27

### Next Version: 0.0.2 (Planned)

- **Focus**: Dataset pathing fixes and Parquet compatibility verification
- **Tracking**: Issue #28
- **Target**: TBD

---

## Released Versions

### [v0.0.1] - 2025-11-12

**Theme**: Scan & Simulation Performance Optimization

**Highlights**:

- High-performance vectorized scanning (6.9M candles in ~0.02s)
- Complete trade execution pipeline with metrics
- Rich progress bars with clean terminal output
- Auto-constructed data paths from CLI flags
- Direct Parquet loading (10-15x speedup over CSV)

**Key Features**:

- BatchScan with strategy.scan_vectorized() protocol
- SimulationResult with 10 trade detail arrays
- TradeExecution conversion and metrics calculation
- CLI auto-path: `--pair EURUSD --dataset test`
- Smart file format detection (.parquet/.csv fallback)

**Code Quality**:

- All modules ≥9.78/10 Pylint scores
- 16 files changed, 680 insertions, 88 deletions
- New test script: `scripts/test_vectorized_scan.py`

**Related**:

- Feature Spec: 010-scan-sim-perf
- Pull Request: #27
- Commit: a723ed0

---

## Version Planning

### v0.0.x (Patch Releases)

- Bug fixes and minor improvements
- Documentation updates
- Performance optimizations
- No breaking changes

### v0.1.0 (Next Minor Release)

- Multi-symbol portfolio support (#28)
- Enhanced metrics and reporting
- Additional strategy implementations
- Possible API refinements

### v1.0.0 (Future Major Release)

- Stable public API
- Production-ready backtesting engine
- Comprehensive strategy library
- Full documentation and examples
