# Research: Optimize Batch Simulation Performance

**Branch**: `011-optimize-batch-simulation` | **Date**: 2025-11-12 | **Spec**: [spec.md](spec.md)

This document outlines the research tasks required to identify and implement performance optimizations for the batch simulation engine.

## Research Tasks

### Task 1: Profile Pandas Window Operations

**Objective**: Identify the performance bottlenecks related to legacy pandas window operations.

**Approach**:
1.  Use a profiling tool (e.g., `cProfile`, `py-spy`) to analyze the execution time and memory usage of the pandas window operations in the `src/backtest/` modules.
2.  Focus the profiling on the code that handles the 100-candle windows on the 6.9 million candle dataset.
3.  Analyze the identified bottlenecks to understand the root cause of the performance issues.

**Expected Outcome**: A detailed report on the performance bottlenecks caused by the pandas window operations.

### Task 2: Investigate Alternatives to Pandas Rolling Windows

**Objective**: Research and evaluate methods to replace the slow pandas rolling windows with a more performant solution.

**Approach**:
1.  Investigate how to implement rolling window operations using vectorized methods in Polars or NumPy.
2.  Explore other libraries that provide efficient rolling window implementations.
3.  Prototype a solution to replace the pandas rolling windows and measure the performance improvement.

**Expected Outcome**: A recommendation for the best approach to replace the pandas rolling windows, including a prototype and performance benchmarks.

### Task 3: Evaluate Parallelization Strategies

**Objective**: Research and compare different parallelization techniques for executing multiple simulations concurrently.

**Approach**:
1.  Investigate the capabilities of Python's parallelization libraries, including `multiprocessing`, `joblib`, `dask`, and `ray`.
2.  Evaluate each library based on its suitability for the project's specific needs, considering factors such as ease of use, scalability, and overhead.
3.  Prototype a simple parallel execution loop using the most promising libraries to measure the potential performance gains.

**Expected Outcome**: A recommendation for the most suitable parallelization library and a high-level design for its integration into the backtesting engine.

## Decisions

*This section will be filled in after the research tasks are completed.*

| Decision | Rationale | Alternatives Considered |
|---|---|---|
| | | |
