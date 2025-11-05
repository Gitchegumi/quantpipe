"""Unit tests for benchmark aggregation utility (T071).

Tests CI gate regression thresholds, success criteria flags, and fallback checks.
"""

# pylint: disable=unused-import

import json
import subprocess


class TestBenchmarkAggregatorCIGates:
    """Test suite for T071 CI gate regression detection."""

    def test_fail_on_regression_success_criteria_pass(self, tmp_path):
        """T071: --fail-on-regression passes when success_criteria_passed=True."""
        # Create benchmark with all criteria passing
        benchmark_file = tmp_path / "benchmark_pass.json"
        benchmark_data = {
            "dataset_rows": 1000000,
            "trades_simulated": 5000,
            "phase_times": {"scan": 120.0},
            "wall_clock_total": 180.0,
            "memory_peak_mb": 1024.0,
            "memory_ratio": 1.2,
            "success_criteria_passed": True,
            "runtime_passed": True,
            "memory_passed": True,
            "hotspot_count_passed": True,
            "parallel_efficiency_passed": None,
        }

        with benchmark_file.open("w") as f:
            json.dump(benchmark_data, f)

        # Run aggregator with --fail-on-regression
        result = subprocess.run(
            [
                "poetry",
                "run",
                "python",
                "scripts/ci/aggregate_benchmarks.py",
                "--pattern",
                str(tmp_path / "benchmark_*.json"),
                "--output",
                str(tmp_path / "summary.json"),
                "--fail-on-regression",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        # Should exit 0 (success)
        assert result.returncode == 0, f"Expected exit 0, got {result.returncode}"
        assert "[PASS] All benchmarks passed success criteria" in result.stdout

    def test_fail_on_regression_success_criteria_fail(self, tmp_path):
        """T071: --fail-on-regression fails when success_criteria_passed=False."""
        # Create benchmark with failed criteria
        benchmark_file = tmp_path / "benchmark_fail.json"
        benchmark_data = {
            "dataset_rows": 6922364,
            "trades_simulated": 17724,
            "phase_times": {"scan": 900.0, "simulate": 600.0},
            "wall_clock_total": 1500.0,  # Exceeds 1200s threshold
            "memory_peak_mb": 2048.0,
            "memory_ratio": 1.2,
            "success_criteria_passed": False,
            "runtime_passed": False,  # SC-001 failed
            "memory_passed": True,
            "hotspot_count_passed": None,
            "parallel_efficiency_passed": None,
        }

        with benchmark_file.open("w") as f:
            json.dump(benchmark_data, f)

        # Run aggregator with --fail-on-regression
        result = subprocess.run(
            [
                "poetry",
                "run",
                "python",
                "scripts/ci/aggregate_benchmarks.py",
                "--pattern",
                str(tmp_path / "benchmark_*.json"),
                "--output",
                str(tmp_path / "summary.json"),
                "--fail-on-regression",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        # Should exit 1 (failure)
        assert result.returncode == 1, f"Expected exit 1, got {result.returncode}"
        assert "[FAIL] BENCHMARK REGRESSION DETECTED" in result.stdout
        assert "runtime_passed=False" in result.stdout

    def test_fail_on_regression_fallback_runtime_threshold(self, tmp_path):
        """
        T071: Fallback runtime threshold check for old schema 
        (no success_criteria_passed).
        """
        # Create benchmark without success_criteria_passed flag (old schema)
        benchmark_file = tmp_path / "benchmark_old_schema.json"
        benchmark_data = {
            "dataset_rows": 1000000,
            "trades_simulated": 5000,
            "phase_times": {"scan": 600.0, "simulate": 700.0},
            "wall_clock_total": 1300.0,  # Exceeds default 1200s threshold
            "memory_peak_mb": 1024.0,
            "memory_ratio": 1.2,
            # No success_criteria_passed field
        }

        with benchmark_file.open("w") as f:
            json.dump(benchmark_data, f)

        # Run aggregator with --fail-on-regression
        result = subprocess.run(
            [
                "poetry",
                "run",
                "python",
                "scripts/ci/aggregate_benchmarks.py",
                "--pattern",
                str(tmp_path / "benchmark_*.json"),
                "--output",
                str(tmp_path / "summary.json"),
                "--fail-on-regression",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        # Should exit 1 due to runtime threshold
        assert result.returncode == 1
        assert "[FAIL] BENCHMARK REGRESSION DETECTED" in result.stdout
        assert "Runtime exceeds threshold" in result.stdout
        assert "1300.0s > 1200" in result.stdout
        assert "SC-001" in result.stdout

    def test_fail_on_regression_fallback_memory_threshold(self, tmp_path):
        """T071: Fallback memory threshold check for old schema."""
        # Create benchmark with memory ratio exceeding threshold
        benchmark_file = tmp_path / "benchmark_memory_high.json"
        benchmark_data = {
            "dataset_rows": 1000000,
            "trades_simulated": 5000,
            "phase_times": {"scan": 120.0},
            "wall_clock_total": 180.0,
            "memory_peak_mb": 2048.0,
            "memory_ratio": 1.8,  # Exceeds default 1.5 threshold
        }

        with benchmark_file.open("w") as f:
            json.dump(benchmark_data, f)

        # Run aggregator with --fail-on-regression
        result = subprocess.run(
            [
                "poetry",
                "run",
                "python",
                "scripts/ci/aggregate_benchmarks.py",
                "--pattern",
                str(tmp_path / "benchmark_*.json"),
                "--output",
                str(tmp_path / "summary.json"),
                "--fail-on-regression",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        # Should exit 1 due to memory threshold
        assert result.returncode == 1
        assert "[FAIL] BENCHMARK REGRESSION DETECTED" in result.stdout
        assert "Memory ratio exceeds threshold" in result.stdout
        assert "1.80× > 1.5×" in result.stdout
        assert "SC-009" in result.stdout

    def test_fail_on_regression_custom_thresholds(self, tmp_path):
        """T071: Custom runtime and memory thresholds respected."""
        # Create benchmark that would fail default but pass custom thresholds
        benchmark_file = tmp_path / "benchmark_custom.json"
        benchmark_data = {
            "dataset_rows": 1000000,
            "trades_simulated": 5000,
            "phase_times": {"scan": 500.0},
            "wall_clock_total": 1400.0,  # Exceeds default 1200s, but < 1500s
            "memory_peak_mb": 1024.0,
            "memory_ratio": 1.6,  # Exceeds default 1.5, but < 2.0
        }

        with benchmark_file.open("w") as f:
            json.dump(benchmark_data, f)

        # Run with custom thresholds
        result = subprocess.run(
            [
                "poetry",
                "run",
                "python",
                "scripts/ci/aggregate_benchmarks.py",
                "--pattern",
                str(tmp_path / "benchmark_*.json"),
                "--output",
                str(tmp_path / "summary.json"),
                "--fail-on-regression",
                "--runtime-threshold",
                "1500.0",  # Higher runtime threshold
                "--memory-threshold",
                "2.0",  # Higher memory threshold
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        # Should pass with custom thresholds
        assert result.returncode == 0
        assert "[PASS] All benchmarks passed success criteria" in result.stdout

    def test_no_fail_on_regression_flag_always_succeeds(self, tmp_path):
        """T071: Without --fail-on-regression flag, always exits 0."""
        # Create failing benchmark
        benchmark_file = tmp_path / "benchmark_fail.json"
        benchmark_data = {
            "dataset_rows": 1000000,
            "trades_simulated": 5000,
            "phase_times": {"scan": 900.0},
            "wall_clock_total": 2000.0,  # Way over threshold
            "memory_peak_mb": 4096.0,
            "memory_ratio": 3.0,  # Way over threshold
            "success_criteria_passed": False,
        }

        with benchmark_file.open("w") as f:
            json.dump(benchmark_data, f)

        # Run WITHOUT --fail-on-regression
        result = subprocess.run(
            [
                "poetry",
                "run",
                "python",
                "scripts/ci/aggregate_benchmarks.py",
                "--pattern",
                str(tmp_path / "benchmark_*.json"),
                "--output",
                str(tmp_path / "summary.json"),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        # Should always exit 0 without flag
        assert result.returncode == 0
        assert "[FAIL] BENCHMARK REGRESSION" not in result.stdout
