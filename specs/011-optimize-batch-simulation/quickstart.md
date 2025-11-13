# Quickstart: Optimize Batch Simulation Performance

**Branch**: `011-optimize-batch-simulation` | **Date**: 2025-11-12 | **Spec**: [spec.md](spec.md)

This document provides a quick overview of how to use the optimized batch simulation feature.

## Running a Batch Simulation

The optimized batch simulation can be run from the command line. The following is an example of how to run a batch of simulations for different strategies and instruments.

```bash
python -m src.cli.main run-batch --experiment-name "My Experiment" --strategies "strategy1,strategy2" --instruments "EURUSD,USDJPY"
```

## Monitoring Progress

The progress of the batch simulation will be displayed in the console. The output will include the status of each individual simulation and the overall progress of the experiment.

## Viewing Results

The results of the batch simulation will be saved to the `results/` directory. The results will be organized by experiment and will include a summary of the performance of each simulation.
