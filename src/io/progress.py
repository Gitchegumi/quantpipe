"""Progress reporting utilities for ingestion pipeline.

This module provides utilities for reporting progress during ingestion
operations with visual progress bars using Rich that track actual data
processing progress within each stage.
"""

import logging
from typing import Optional

from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskID

from .logging_constants import IngestionStage

logger = logging.getLogger(__name__)


class ProgressReporter:
    """Progress reporter for ingestion pipeline with data-based progress tracking."""

    def __init__(self, show_progress: bool = True) -> None:
        """Initialize progress reporter.

        Args:
            show_progress: Whether to show visual progress bar (default True).
        """
        self.show_progress = show_progress
        self.progress: Optional[Progress] = None
        self.task_id: Optional[TaskID] = None

        if self.show_progress:
            self.progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
            )
            self.progress.start()

    def start_stage(
        self, stage: IngestionStage, message: str, total: Optional[int] = None
    ) -> None:
        """Start a new pipeline stage with progress tracking.

        Args:
            stage: The stage being started.
            message: Description of the stage.
            total: Total units to process. If None, uses indeterminate spinner.
        """
        # Build description
        description = f"{stage.value}: {message}"

        # Update or create visual progress bar
        if self.progress:
            if self.task_id is not None:
                # Complete previous task
                if self.progress.tasks[0].total:
                    self.progress.update(self.task_id, completed=self.progress.tasks[0].total)
                self.progress.remove_task(self.task_id)
            
            # Start new task
            if total:
                # Deterministic progress with row counts
                self.task_id = self.progress.add_task(description, total=total)
            else:
                # Indeterminate spinner for atomic operations
                self.task_id = self.progress.add_task(description, total=None)

        # Also log for records
        logger.info("%s: %s", stage.value, message)

    def update_progress(self, advance: int = 1, completed: Optional[int] = None) -> None:
        """Update progress within current stage.

        Args:
            advance: Number of units to advance (default 1).
            completed: Set absolute completion amount (overrides advance).
        """
        if self.progress and self.task_id is not None:
            if completed is not None:
                self.progress.update(self.task_id, completed=completed)
            else:
                self.progress.update(self.task_id, advance=advance)

    def report_stage(
        self, stage: IngestionStage, message: Optional[str] = None
    ) -> None:
        """Report a simple stage completion (for stages without data progress).

        Args:
            stage: The stage being reported.
            message: Optional additional message.
        """
        # For backward compatibility - start and immediately complete the stage
        description = message if message else stage.value
        self.start_stage(stage, description, total=1)
        self.update_progress(completed=1)

    def finish(self) -> None:
        """Check if all stages have been reported.

        Returns:
            bool: True if all stages completed.
        """
        return self.current_stage >= self.total_stages

    def finish(self) -> None:
        """Finalize and stop the progress bar."""
        if self.progress:
            self.progress.stop()
