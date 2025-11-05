"""Unit tests for profiling and benchmark recording.

Tests phase timing context, benchmark record schema (SC-007), hotspot count
validation (FR-016, SC-008: ≥10), a/fail flag embedding (FR-014).
"""

# pylint: disable=unused-import, fixme

import json
from pathlib import Path
import pytest
from src.backtest.profiling import ProfilingContext, write_benchmark_record


class TestProfilingContext:
    """Test suite for ProfilingContext class."""

    def test_phase_timing(self):
        """Context manager records phase durations."""
        # TODO: Implement timing test with mock sleep

    def test_nested_phases(self):
        """Nested phase calls handled correctly."""
        # TODO: Test start_phase called before end_phase


class TestBenchmarkRecord:
    """Test suite for benchmark record writing."""

    def test_write_benchmark_record(self, tmp_path):
        """Benchmark record writes valid JSON with required fields."""
        output_file = tmp_path / "test_benchmark.json"

        write_benchmark_record(
            output_path=output_file,
            dataset_rows=1000,
            trades_simulated=50,
            phase_times={"ingest": 1.5, "scan": 2.0, "simulate": 3.0},
            wall_clock_total=6.5,
            memory_peak_mb=128.0,
            memory_ratio=1.2,
        )

        assert output_file.exists()
        with open(output_file, "r", encoding="utf-8") as f:
            record = json.load(f)

        assert record["dataset_rows"] == 1000
        assert record["trades_simulated"] == 50
        assert "phase_times" in record
        assert record["wall_clock_total"] == 6.5

    def test_benchmark_schema_validation(self, tmp_path):
        """Benchmark record passes schema validation (SC-007)."""
        output_file = tmp_path / "schema_test.json"

        # Write benchmark with all required fields
        write_benchmark_record(
            output_path=output_file,
            dataset_rows=6922364,
            trades_simulated=17724,
            phase_times={"ingest": 480.0, "scan": 3600.0, "simulate": 1200.0},
            wall_clock_total=5280.0,
            memory_peak_mb=2048.0,
            memory_ratio=1.4,
        )

        # Load and validate schema
        with open(output_file, "r", encoding="utf-8") as f:
            record = json.load(f)

        # Required fields
        assert "dataset_rows" in record, "Missing dataset_rows field"
        assert "trades_simulated" in record, "Missing trades_simulated field"
        assert "phase_times" in record, "Missing phase_times field"
        assert "wall_clock_total" in record, "Missing wall_clock_total field"
        assert "memory_peak_mb" in record, "Missing memory_peak_mb field"
        assert "memory_ratio" in record, "Missing memory_ratio field"

        # Type validation
        assert isinstance(record["dataset_rows"], int), "dataset_rows must be int"
        assert isinstance(
            record["trades_simulated"], int
        ), "trades_simulated must be int"
        assert isinstance(record["phase_times"], dict), "phase_times must be dict"
        assert isinstance(
            record["wall_clock_total"], (int, float)
        ), "wall_clock_total must be numeric"
        assert isinstance(
            record["memory_peak_mb"], (int, float)
        ), "memory_peak_mb must be numeric"
        assert isinstance(
            record["memory_ratio"], (int, float)
        ), "memory_ratio must be numeric"

        # Phase times structure validation
        for phase_name, duration in record["phase_times"].items():
            assert isinstance(
                phase_name, str
            ), f"Phase name {phase_name} must be string"
            assert isinstance(
                duration, (int, float)
            ), f"Phase duration {duration} must be numeric"
            assert duration >= 0, f"Phase duration {duration} must be non-negative"

        # Value constraints
        assert record["dataset_rows"] > 0, "dataset_rows must be positive"
        assert record["trades_simulated"] >= 0, "trades_simulated must be non-negative"
        assert record["wall_clock_total"] > 0, "wall_clock_total must be positive"
        assert record["memory_peak_mb"] > 0, "memory_peak_mb must be positive"
        assert record["memory_ratio"] > 0, "memory_ratio must be positive"

    def test_benchmark_optional_fields(self, tmp_path):
        """Benchmark record accepts optional metadata fields."""
        output_file = tmp_path / "optional_test.json"

        # Write with optional kwargs
        write_benchmark_record(
            output_path=output_file,
            dataset_rows=1000,
            trades_simulated=50,
            phase_times={"scan": 10.0},
            wall_clock_total=15.0,
            memory_peak_mb=256.0,
            memory_ratio=1.1,
            fraction=0.1,
            parallel_efficiency=0.85,
            custom_field="test_value",
        )

        with open(output_file, "r", encoding="utf-8") as f:
            record = json.load(f)

        # Verify optional fields preserved
        assert record["fraction"] == 0.1
        assert record["parallel_efficiency"] == 0.85
        assert record["custom_field"] == "test_value"

    def test_benchmark_empty_phase_times(self, tmp_path):
        """Benchmark record handles empty phase_times dict."""
        output_file = tmp_path / "empty_phases.json"

        write_benchmark_record(
            output_path=output_file,
            dataset_rows=100,
            trades_simulated=5,
            phase_times={},  # Empty dict
            wall_clock_total=1.0,
            memory_peak_mb=64.0,
            memory_ratio=1.0,
        )

        with open(output_file, "r", encoding="utf-8") as f:
            record = json.load(f)

        assert record["phase_times"] == {}
        assert isinstance(record["phase_times"], dict)

    # TODO: Add tests for:
    # - Pass/fail criteria flags (FR-014)
    # - Hotspot count field ≥10 (FR-016, SC-008)
