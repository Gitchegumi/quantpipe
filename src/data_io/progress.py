"""Progress reporting utilities for ingestion pipeline.

This module provides utilities for reporting progress during ingestion
operations with visual progress bars using Rich that track actual data
processing progress within each stage.
"""

import logging
from typing import Optional

from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskID,
    Task,
)
from rich.text import Text as RichText

from .logging_constants import IngestionStage

logger = logging.getLogger(__name__)


class RowCountColumn(TextColumn):
    """Custom column showing row counts for determinate/indeterminate progress."""

    def __init__(self):
        """Initialize with empty text format (we override render)."""
        super().__init__("")

    def render(self, task: Task) -> RichText:
        """Render row count text."""
        if task.total is not None:
            # Determinate progress: show X/Y rows
            text = f"{task.completed:,}/{task.total:,} rows"
            return RichText(text, style="cyan")
        # Indeterminate progress: just show spinner
        return RichText("", style="cyan")

class ProgressReporter:
    """Progress reporter with data-based progress tracking."""

    def __init__(self, show_progress: bool = True) -> None:
        """Initialize progress reporter.

        Args:
            show_progress: Whether to show visual progress bar (default True).
        """
        self.show_progress = show_progress
        self.progress: Optional[Progress] = None
        self.task_id: Optional[TaskID] = None
        self._started = False

        if self.show_progress:
            self.progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                RowCountColumn(),
            )

    def start_stage(
        self, stage: IngestionStage, message: str, total: Optional[int] = None
    ) -> None:
        """Start a new pipeline stage with progress tracking.

        Args:
            stage: The stage being started.
            message: Description of the stage.
            total: Total units to process. If None, uses indeterminate.
        """
        # Build description
        description = f"{stage.value}: {message}"

        # Update or create visual progress bar
        if self.progress:
            # Start progress bar on first use
            if not self._started:
                self.progress.start()
                self._started = True

            if self.task_id is not None:
                # Complete previous task
                if self.progress.tasks[0].total:
                    current_task = self.progress.tasks[0]
                    self.progress.update(
                        self.task_id, completed=current_task.total
                    )
                self.progress.remove_task(self.task_id)

            # Start new task
            if total:
                # Deterministic progress with row counts
                self.task_id = self.progress.add_task(description, total=total)
            else:
                # Indeterminate spinner for atomic operations
                self.task_id = self.progress.add_task(description, total=None)

            # Don't also log when using progress UI - avoid duplication
        else:
            # Log only if no progress UI
            logger.info("%s: %s", stage.value, message)

    def update_progress(
        self, advance: int = 1, completed: Optional[int] = None
    ) -> None:
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
        """Report a simple stage (for backward compatibility).

        Args:
            stage: The stage being reported.
            message: Optional additional message.
        """
        # For backward compatibility
        description = message if message else stage.value
        self.start_stage(stage, description, total=1)
        self.update_progress(completed=1)

    def finish(self) -> None:
        """Finalize and stop the progress bar."""
        if self.progress and self._started:
            self.progress.stop()
            self._started = False
