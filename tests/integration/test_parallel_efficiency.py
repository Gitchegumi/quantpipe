"""Integration tests for parallel execution efficiency.

Tests FR-008, FR-008a worker capping, SC-011 efficiency ≥70%, SC-012 warning.
"""

# pylint: disable=unused-import, fixme

import logging
import multiprocessing
import time

from src.backtest.parallel import get_worker_count, run_parallel


def _dummy_worker(duration: float) -> float:
    """Dummy worker that sleeps for specified duration.

    Args:
        duration: Sleep time in seconds

    Returns:
        The duration value
    """
    time.sleep(duration)
    return duration


class TestParallelEfficiency:
    """Integration test suite for parallel backtest execution."""

    def test_parallel_efficiency_calculation(self):
        """Parallel efficiency ≥ 70% for up to 4 workers (SC-011).

        Calculates efficiency = ideal_time / (actual_time × workers)
        where ideal_time is single-worker baseline.
        """
        # Use lightweight tasks for reliable timing
        num_tasks = 8
        task_duration = 0.5  # 500ms per task
        tasks = [task_duration] * num_tasks

        # 1. Single worker baseline (ideal time)
        start = time.perf_counter()
        run_parallel(_dummy_worker, tasks, max_workers=1)
        ideal_time = time.perf_counter() - start

        # 2. Test with 2 workers
        start = time.perf_counter()
        run_parallel(_dummy_worker, tasks, max_workers=2)
        time_2_workers = time.perf_counter() - start
        efficiency_2 = ideal_time / (time_2_workers * 2)

        # 3. Test with 4 workers (if available)
        logical_cores = multiprocessing.cpu_count()
        if logical_cores >= 4:
            start = time.perf_counter()
            run_parallel(_dummy_worker, tasks, max_workers=4)
            time_4_workers = time.perf_counter() - start
            efficiency_4 = ideal_time / (time_4_workers * 4)

            # Assert SC-011: efficiency ≥ 0.70
            assert (
                efficiency_4 >= 0.70
            ), f"4-worker efficiency {efficiency_4:.2f} < 0.70 threshold (SC-011)"

        # Assert SC-011 for 2 workers
        assert (
            efficiency_2 >= 0.70
        ), f"2-worker efficiency {efficiency_2:.2f} < 0.70 threshold (SC-011)"

    def test_worker_cap_warning(self, caplog):
        """Worker cap emits single warning when requested > cores (FR-008a, SC-012)."""
        logical_cores = multiprocessing.cpu_count()
        requested = logical_cores + 2

        # Capture warnings
        with caplog.at_level(logging.WARNING):
            actual_workers = get_worker_count(requested)

        # Verify capped to logical cores
        assert (
            actual_workers == logical_cores
        ), f"Workers not capped: got {actual_workers}, expected {logical_cores}"

        # Verify exactly one warning (SC-012)
        warning_messages = [
            record.message
            for record in caplog.records
            if record.levelname == "WARNING"
            and "exceeds logical cores" in record.message
        ]
        assert (
            len(warning_messages) == 1
        ), f"Expected 1 warning, got {len(warning_messages)} (SC-012)"

    def test_max_workers_flag_integration(self):
        """Worker count respects max_workers parameter (FR-008a)."""
        # Test with explicit worker count
        tasks = [0.1] * 4

        # Request specific worker count
        max_workers = 2
        start = time.perf_counter()
        results = run_parallel(_dummy_worker, tasks, max_workers=max_workers)
        elapsed = time.perf_counter() - start

        # Verify all tasks completed
        assert len(results) == len(tasks), "Not all tasks completed"
        assert all(r == 0.1 for r in results), "Results don't match input"

        # Verify execution completed (basic sanity check)
        assert elapsed < 1.0, f"Execution took too long: {elapsed:.2f}s"

    def test_get_worker_count_auto_detection(self):
        """Auto-detection leaves one core free (FR-008)."""
        logical_cores = multiprocessing.cpu_count()
        auto_workers = get_worker_count(None)

        # Should be cores - 1, but at least 1
        expected = max(1, logical_cores - 1)
        assert (
            auto_workers == expected
        ), f"Auto-detection failed: got {auto_workers}, expected {expected}"

    def test_get_worker_count_respects_request(self):
        """Requested worker count is honored when valid (FR-008a)."""
        logical_cores = multiprocessing.cpu_count()

        # Request valid count (cores - 1)
        if logical_cores > 2:
            requested = logical_cores - 1
            actual = get_worker_count(requested)
            assert (
                actual == requested
            ), f"Valid request not honored: requested {requested}, got {actual}"
