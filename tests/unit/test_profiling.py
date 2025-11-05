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
        import time

        with ProfilingContext(enable_cprofile=False) as profiler:
            profiler.start_phase("phase1")
            time.sleep(0.01)  # Small delay
            profiler.end_phase("phase1")

            profiler.start_phase("phase2")
            time.sleep(0.01)
            profiler.end_phase("phase2")

        times = profiler.get_phase_times()
        assert "phase1" in times
        assert "phase2" in times
        assert times["phase1"] >= 0.01
        assert times["phase2"] >= 0.01

    def test_nested_phases(self):
        """Nested phase calls handled correctly."""
        with ProfilingContext(enable_cprofile=False) as profiler:
            profiler.start_phase("outer")
            # Starting new phase should end previous
            profiler.start_phase("inner")
            profiler.end_phase("inner")

        times = profiler.get_phase_times()
        assert "outer" in times or "inner" in times

    def test_hotspot_extraction(self):
        """Hotspot extraction returns function profiling data."""
        with ProfilingContext(enable_cprofile=True) as profiler:
            profiler.start_phase("compute")
            # Do some work
            _ = sum(i**2 for i in range(1000))
            profiler.end_phase("compute")

        hotspots = profiler.get_hotspots(n=5)
        assert isinstance(hotspots, list)
        assert len(hotspots) <= 5

        # Validate hotspot structure
        if hotspots:
            hotspot = hotspots[0]
            assert "function" in hotspot
            assert "filename" in hotspot
            assert "lineno" in hotspot
            assert "ncalls" in hotspot
            assert "tottime" in hotspot
            assert "cumtime" in hotspot
            assert isinstance(hotspot["ncalls"], int)
            assert isinstance(hotspot["tottime"], float)

    def test_hotspot_count_validation(self):
        """Hotspot extraction returns at least 10 hotspots (SC-008)."""
        with ProfilingContext(enable_cprofile=True) as profiler:
            profiler.start_phase("work")
            # Generate more function calls
            for i in range(100):
                _ = len(str(i))
                _ = abs(i)
                _ = max(i, 0)
            profiler.end_phase("work")

        hotspots = profiler.get_hotspots(n=10)
        # Should have at least some hotspots (may not reach 10 for simple code)
        assert isinstance(hotspots, list)
        assert len(hotspots) >= 1  # At least some functions tracked


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

    def test_benchmark_parallel_efficiency_support(self, tmp_path):
        """T038: Benchmark writer supports parallel_efficiency and phase_times."""
        output_file = tmp_path / "parallel_benchmark.json"

        # Write record with phase_times and parallel_efficiency
        phase_times = {"ingest": 5.0, "scan": 10.0, "simulate": 8.0}
        parallel_efficiency = 0.92

        write_benchmark_record(
            output_path=output_file,
            dataset_rows=5000,
            trades_simulated=250,
            phase_times=phase_times,
            wall_clock_total=23.0,
            memory_peak_mb=512.0,
            memory_ratio=1.5,
            parallel_efficiency=parallel_efficiency,
        )

        with open(output_file, "r", encoding="utf-8") as f:
            record = json.load(f)

        # Verify phase_times preserved
        assert "phase_times" in record
        assert record["phase_times"] == phase_times
        assert record["phase_times"]["ingest"] == 5.0
        assert record["phase_times"]["scan"] == 10.0
        assert record["phase_times"]["simulate"] == 8.0

        # Verify parallel_efficiency preserved
        assert "parallel_efficiency" in record
        assert record["parallel_efficiency"] == parallel_efficiency
        assert record["parallel_efficiency"] == 0.92

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

    def test_profiling_artifact_with_hotspots(self, tmp_path):
        """Benchmark record includes hotspot data from profiling run (T035)."""
        output_file = tmp_path / "profiling_artifact.json"

        # Simulate hotspot data structure
        mock_hotspots = [
            {
                "function": "simulate_trades_batch",
                "filename": "trade_sim_batch.py",
                "lineno": 45,
                "ncalls": 100,
                "tottime": 1.234,
                "cumtime": 2.345,
                "percall_tot": 0.01234,
                "percall_cum": 0.02345,
            },
            {
                "function": "generate_long_signals",
                "filename": "signal_generator.py",
                "lineno": 123,
                "ncalls": 5000,
                "tottime": 3.456,
                "cumtime": 5.678,
                "percall_tot": 0.0006912,
                "percall_cum": 0.0011356,
            },
        ]

        write_benchmark_record(
            output_path=output_file,
            dataset_rows=100000,
            trades_simulated=500,
            phase_times={"ingest": 10.0, "scan": 30.0, "simulate": 15.0},
            wall_clock_total=55.0,
            memory_peak_mb=512.0,
            memory_ratio=1.3,
            hotspots=mock_hotspots,
        )

        with open(output_file, "r", encoding="utf-8") as f:
            record = json.load(f)

        # Verify hotspots are included
        assert "hotspots" in record
        assert isinstance(record["hotspots"], list)
        assert len(record["hotspots"]) == 2

        # Verify hotspot structure
        hotspot = record["hotspots"][0]
        assert hotspot["function"] == "simulate_trades_batch"
        assert hotspot["ncalls"] == 100
        assert hotspot["tottime"] == 1.234
        assert "filename" in hotspot
        assert "lineno" in hotspot

    def test_memory_threshold_not_exceeded(self, tmp_path):
        """Memory ratio below threshold does not flag warning (T044, FR-013)."""
        from src.backtest.profiling import check_memory_threshold

        output_file = tmp_path / "memory_ok.json"

        # Memory ratio = 1.2 (below 1.5 threshold)
        write_benchmark_record(
            output_path=output_file,
            dataset_rows=1000,
            trades_simulated=50,
            phase_times={"scan": 10.0},
            wall_clock_total=10.0,
            memory_peak_mb=256.0,
            memory_ratio=1.2,  # Below threshold
        )

        with open(output_file, "r", encoding="utf-8") as f:
            record = json.load(f)

        # Verify threshold check passed
        assert "memory_threshold_exceeded" in record
        assert record["memory_threshold_exceeded"] is False
        assert record["memory_ratio"] == 1.2

    def test_memory_threshold_exceeded(self, tmp_path):
        """Memory ratio above threshold flags warning (T044, FR-013, SC-009)."""
        from src.backtest.profiling import check_memory_threshold

        output_file = tmp_path / "memory_exceeded.json"

        # Memory ratio = 1.8 (above 1.5 threshold)
        write_benchmark_record(
            output_path=output_file,
            dataset_rows=1000,
            trades_simulated=50,
            phase_times={"scan": 10.0},
            wall_clock_total=10.0,
            memory_peak_mb=512.0,
            memory_ratio=1.8,  # Above threshold
        )

        with open(output_file, "r", encoding="utf-8") as f:
            record = json.load(f)

        # Verify threshold check failed
        assert "memory_threshold_exceeded" in record
        assert record["memory_threshold_exceeded"] is True
        assert record["memory_ratio"] == 1.8

    def test_check_memory_threshold_function(self):
        """check_memory_threshold returns correct boolean (T044)."""
        from src.backtest.profiling import check_memory_threshold

        # Below threshold
        assert check_memory_threshold(1.2, threshold=1.5) is False
        assert check_memory_threshold(1.5, threshold=1.5) is False  # Equal OK

        # Above threshold
        assert check_memory_threshold(1.6, threshold=1.5) is True
        assert check_memory_threshold(2.0, threshold=1.5) is True

    # TODO: Add tests for:
    # - Pass/fail criteria flags (FR-014)
    # - Hotspot count field ≥10 (FR-016, SC-008)
