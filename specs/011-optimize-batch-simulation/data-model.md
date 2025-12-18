# Data Model: Optimize Batch Simulation Performance

**Branch**: `011-optimize-batch-simulation` | **Date**: 2025-11-12 | **Spec**: [spec.md](spec.md)

This document describes the data model for the entities involved in the batch simulation performance optimization feature.

## Key Entities

### Simulation

Represents a single backtest run.

**Attributes**:

-   `id`: A unique identifier for the simulation.
-   `strategy`: The name of the trading strategy being tested.
-   `instrument`: The financial instrument (e.g., 'EURUSD') being traded.
-   `start_time`: The start time of the simulation period.
-   `end_time`: The end time of the simulation period.
-   `parameters`: A set of parameters used for the strategy.
-   `execution_time`: The total time taken to run the simulation, in seconds.
-   `results`: The outcome of the simulation, including performance metrics such as net profit, drawdown, and Sharpe ratio.
-   `status`: The current status of the simulation (e.g., 'pending', 'running', 'completed', 'failed').

**State Transitions**:

A `Simulation` can transition through the following states:

-   `pending` -> `running`
-   `running` -> `completed`
-   `running` -> `failed`

### Experiment

Represents a collection of one or more simulations.

**Attributes**:

-   `id`: A unique identifier for the experiment.
-   `name`: A user-defined name for the experiment.
-   `simulations`: A list of `Simulation` objects that are part of the experiment.
-   `status`: The overall status of the experiment (e.g., 'running', 'completed').

**Relationships**:

-   An `Experiment` has a one-to-many relationship with `Simulation`.
