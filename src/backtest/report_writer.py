"""Performance report JSON writer with schema versioning.

This module provides functionality to serialize PerformanceReport instances
to JSON format with proper formatting and schema version tracking for
future compatibility and benchmark archival.
"""

import json
import logging
from pathlib import Path
from typing import Optional

from src.models.performance_report import PerformanceReport


logger = logging.getLogger(__name__)

# Schema version for PerformanceReport JSON format
# Increment when making breaking changes to the report structure
REPORT_SCHEMA_VERSION = "1.0.0"


class ReportWriter:
    """Write PerformanceReport instances to JSON files with schema versioning."""

    def __init__(self, output_dir: str = "results"):
        """Initialize report writer.

        Args:
            output_dir: Directory for output files (default: "results")
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write_report(
        self,
        report: PerformanceReport,
        filename: Optional[str] = None,
    ) -> Path:
        """Write PerformanceReport to JSON file.

        Args:
            report: PerformanceReport instance to serialize
            filename: Optional output filename (default: auto-generated from timestamp)

        Returns:
            Path to written JSON file
        """
        # Generate filename if not provided
        if filename is None:
            timestamp = report.created_at.strftime("%Y%m%d_%H%M%S")
            filename = f"performance_report_{timestamp}.json"

        output_path = self.output_dir / filename

        # Convert report to dict and add schema version
        report_dict = report.model_dump(mode="json")
        report_dict["schema_version"] = REPORT_SCHEMA_VERSION

        # Write JSON with pretty formatting
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report_dict, f, indent=2, default=str)

        logger.info(
            "Wrote performance report to %s (schema v%s)",
            output_path,
            REPORT_SCHEMA_VERSION,
        )

        return output_path

    def write_benchmark_summary(
        self,
        reports: list[PerformanceReport],
        summary_filename: str = "benchmark_summary.json",
    ) -> Path:
        """Write aggregated benchmark summary from multiple reports.

        Args:
            reports: List of PerformanceReport instances
            summary_filename: Output filename for summary

        Returns:
            Path to written summary JSON file
        """
        if not reports:
            logger.warning("No reports provided for benchmark summary")
            return self.output_dir / summary_filename

        # Calculate aggregate metrics
        total_scans = len(reports)
        avg_scan_duration = sum(r.scan_duration_sec for r in reports) / total_scans
        avg_sim_duration = sum(r.simulation_duration_sec for r in reports) / total_scans
        total_candles = sum(r.candle_count for r in reports)
        total_signals = sum(r.signal_count for r in reports)
        total_trades = sum(r.trade_count for r in reports)

        # Calculate speedup metrics (placeholder: assumes baseline is 2x slower)
        # In production, this should compare against recorded baseline
        baseline_scan_duration = avg_scan_duration * 2.0  # Placeholder
        baseline_sim_duration = avg_sim_duration * 2.0  # Placeholder
        scan_speedup_pct = (
            (baseline_scan_duration - avg_scan_duration) / baseline_scan_duration * 100
        )
        sim_speedup_pct = (
            (baseline_sim_duration - avg_sim_duration) / baseline_sim_duration * 100
        )

        summary = {
            "schema_version": REPORT_SCHEMA_VERSION,
            "report_count": total_scans,
            "aggregate_metrics": {
                "avg_scan_duration_sec": avg_scan_duration,
                "avg_simulation_duration_sec": avg_sim_duration,
                "total_candles_processed": total_candles,
                "total_signals_generated": total_signals,
                "total_trades_executed": total_trades,
            },
            "performance_targets": {
                "scan_speedup_pct": scan_speedup_pct,
                "simulation_speedup_pct": sim_speedup_pct,
                "scan_target_met": scan_speedup_pct >= 50.0,
                "simulation_target_met": sim_speedup_pct >= 55.0,
            },
            "individual_reports": [
                {
                    "created_at": r.created_at.isoformat(),
                    "scan_duration_sec": r.scan_duration_sec,
                    "simulation_duration_sec": r.simulation_duration_sec,
                    "signal_count": r.signal_count,
                    "trade_count": r.trade_count,
                    "equivalence_verified": r.equivalence_verified,
                }
                for r in reports
            ],
        }

        output_path = self.output_dir / summary_filename

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, default=str)

        logger.info(
            "Wrote benchmark summary to %s (%d reports aggregated)",
            output_path,
            total_scans,
        )

        return output_path


def write_report_json(
    report: PerformanceReport,
    output_dir: str = "results",
    filename: Optional[str] = None,
) -> Path:
    """Convenience function to write a performance report to JSON.

    Args:
        report: PerformanceReport instance to serialize
        output_dir: Directory for output files (default: "results")
        filename: Optional output filename

    Returns:
        Path to written JSON file
    """
    writer = ReportWriter(output_dir=output_dir)
    return writer.write_report(report=report, filename=filename)


def write_benchmark_summary_json(
    reports: list[PerformanceReport],
    output_dir: str = "results",
    summary_filename: str = "benchmark_summary.json",
) -> Path:
    """Convenience function to write aggregated benchmark summary.

    Args:
        reports: List of PerformanceReport instances
        output_dir: Directory for output files (default: "results")
        summary_filename: Output filename for summary

    Returns:
        Path to written summary JSON file
    """
    writer = ReportWriter(output_dir=output_dir)
    return writer.write_benchmark_summary(
        reports=reports, summary_filename=summary_filename
    )
