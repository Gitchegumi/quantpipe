# Performance Optimization Guide

## Overview

This document tracks performance improvements for the backtesting engine, focusing on reducing runtime for large datasets (millions of candles) from hours to minutes.

## Baseline Metrics (TODO)

Performance baseline measurements will be captured and recorded here before optimization work begins.

| Metric | Baseline | Target | Status |
|--------|----------|--------|--------|
| Full run time (6.9M candles) | TBD | ≤20 min | Pending |
| Simulation phase speedup | 1× | ≥10× | Pending |
| Load + slice time (10M rows) | TBD | ≤60s | Pending |
| Memory peak ratio | TBD | ≤1.5× | Pending |
| Parallel efficiency (4 workers) | TBD | ≥70% | Pending |

## Before/After Timing (TODO)

Detailed timing comparisons will be added as optimizations are implemented.

## Usage

Detailed usage instructions will be added in later phases covering:

- Profiling flag usage
- Dataset fraction iteration
- Deterministic mode
- Benchmark artifact interpretation

## Benchmarks

Benchmark records are stored in `results/benchmarks/` as JSON files.
