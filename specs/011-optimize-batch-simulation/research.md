# Research: Optimize Batch Simulation Performance

**Branch**: `011-optimize-batch-simulation` | **Date**: 2025-11-12 | **Spec**: [spec.md](spec.md)

This document outlines the research tasks required to identify and implement performance optimizations for the batch simulation engine.

# Research: Optimize Batch Simulation Performance

**Branch**: `011-optimize-batch-simulation` | **Date**: 2025-11-12 | **Spec**: [spec.md](spec.md)

This document outlines the research tasks required to identify and implement performance optimizations for the batch simulation engine.

## Research Tasks

### Profiling Results (T002)

A profiling run was conducted using `poetry run python -m src.cli.run_backtest --pair EURUSD --direction LONG --profile --data-frac 0.1 --portion 1`. The results indicate a significant bottleneck in the simulation phase.

- **Dataset Size**: 692,236 candles (10% of the full dataset)
- **Scan Phase Duration**: 0.15 seconds (identifying signals)
- **Simulation Phase Duration**: 384.08 seconds (executing trades based on signals)
- **Signals Generated**: 8,205
- **Trades Simulated**: 1,157

The simulation phase, which involves iterating through candles and applying strategy logic (including pandas window operations), accounts for almost all of the execution time. This confirms the hypothesis that pandas window operations are a major performance bottleneck.

### Task 1: Profile Pandas Window Operations


**Objective**: Identify the performance bottlenecks related to legacy pandas window operations.

**Approach**:
1.  Use a profiling tool (e.g., `cProfile`, `py-spy`) to analyze the execution time and memory usage of the pandas window operations in the `src/backtest/` modules.
2.  Focus the profiling on the code that handles the 100-candle windows on the 6.9 million candle dataset.
3.  Analyze the identified bottlenecks to understand the root cause of the performance issues.

**Expected Outcome**: A detailed report on the performance bottlenecks caused by the pandas window operations.

### Task 2: Investigate Alternatives to Pandas Rolling Windows

**Investigation:**

The current implementation uses `pandas.DataFrame.rolling` which is known to be slow for large datasets. The main alternatives investigated are:

1.  **Polars:** A modern, high-performance DataFrame library written in Rust. It has a `rolling` function that is specifically designed for time series data and is a direct replacement for the pandas equivalent. The syntax is `df.rolling(index_column="time_column", period="5d")`. Given that Polars is designed for performance and has a similar API to pandas, it is a strong candidate for replacing the current implementation.

2.  **NumPy:** While NumPy can be used to implement rolling windows, it requires more manual implementation using array manipulation (e.g., with `np.lib.stride_tricks.as_strided`). This approach is more complex and error-prone than using a dedicated DataFrame library like Polars.

**Prototype Proposal (Polars):**

A prototype will be created to replace the pandas rolling window logic in `src/backtest/trade_sim_batch.py` with a Polars-based implementation.

The prototype will involve the following steps:
1.  Convert the pandas DataFrame to a Polars DataFrame.
2.  Use the `rolling` function in Polars to calculate the required rolling aggregations (e.g., EMA, ATR).
3.  Benchmark the performance of the Polars-based implementation against the original pandas implementation.

The expected outcome is a significant performance improvement, in line with the project's goal of a 90% reduction in simulation time.

**Objective**: Research and evaluate methods to replace the slow pandas rolling windows with a more performant solution.

**Approach**:
1.  Investigate how to implement rolling window operations using vectorized methods in Polars or NumPy.
2.  Explore other libraries that provide efficient rolling window implementations.
3.  Prototype a solution to replace the pandas rolling windows and measure the performance improvement.

**Expected Outcome**: A recommendation for the best approach to replace the pandas rolling windows, including a prototype and performance benchmarks.

### Task 3: Evaluate Parallelization Strategies

**Investigation:**

An evaluation of Python's parallelization libraries was conducted, focusing on their suitability for executing multiple independent simulations concurrently.

1.  **`multiprocessing`**: Python's built-in module for process-based parallelism. It's effective for CPU-bound tasks and avoids the Global Interpreter Lock (GIL). It provides a lower-level API, requiring more manual management of processes and inter-process communication.

2.  **`joblib`**: Built on top of `multiprocessing`, `joblib` offers a simpler API for parallelizing loops and caching function results. It's particularly well-suited for "embarrassingly parallel" tasks, where independent computations can be run in parallel with minimal communication overhead. Its efficient serialization of Python objects is a significant advantage.

3.  **`dask`**: A flexible library for parallel computing, providing DataFrame and Array objects that extend pandas and NumPy to larger-than-memory or distributed datasets. Dask excels at scaling existing pandas/NumPy workflows and performing complex distributed data processing with lazy evaluation and task graph optimization.

4.  **`ray`**: A general-purpose distributed computing framework offering a more flexible and dynamic task execution model. Ray supports actors (stateful computations) and dynamic task graphs, making it suitable for complex distributed applications, including machine learning and reinforcement learning.

**Recommendation:**

For the immediate goal of executing *multiple independent simulations concurrently* (an embarrassingly parallel problem), **`joblib`** is the recommended choice. Its high-level API (`Parallel`, `delayed`) simplifies the parallelization of loops, and its efficient handling of function arguments and return values makes it very practical for this use case. While Dask and Ray offer more extensive distributed computing capabilities, they introduce additional complexity that is not strictly necessary for simply running multiple independent simulations. If the internal logic of a *single* simulation were to be parallelized, Dask or Ray would be more appropriate.

**Objective**: Research and compare different parallelization techniques for executing multiple simulations concurrently.

**Approach**:
1.  Investigate the capabilities of Python's parallelization libraries, including `multiprocessing`, `joblib`, `dask`, and `ray`.
2.  Evaluate each library based on its suitability for the project's specific needs, considering factors such as ease of use, scalability, and overhead.
3.  Prototype a simple parallel execution loop using the most promising libraries to measure the potential performance gains.

**Expected Outcome**: A recommendation for the most suitable parallelization library and a high-level design for its integration into the backtesting engine.

## Decisions

| Decision | Rationale | Alternatives Considered |
|---|---|---|
| Replace pandas rolling windows with Polars | Polars offers a high-performance, DataFrame-based solution with a similar API to pandas, making it a suitable and efficient replacement for the identified bottleneck. | NumPy (more complex, lower-level), keeping pandas (performance bottleneck) |
| Use `joblib` for parallelizing multiple simulations | `joblib` provides a simple, high-level API for embarrassingly parallel tasks, which is ideal for running multiple independent simulations concurrently. It efficiently handles serialization and is less complex than Dask or Ray for this specific use case. | `multiprocessing` (lower-level API), `dask` (overkill for independent simulations), `ray` (overkill for independent simulations) |
