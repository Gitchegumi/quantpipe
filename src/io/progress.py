"""Progress reporting utilities for ingestion pipeline.

This module provides utilities for reporting progress during ingestion
operations with visual progress bars using Rich.
"""

import logging
from typing import Optional

from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskID

from .logging_constants import IngestionStage, MAX_PROGRESS_UPDATES

logger = logging.getLogger(__name__)


class ProgressReporter:
    """Progress reporter for ingestion pipeline stages with visual progress bar."""

    def __init__(
        self, total_stages: int = MAX_PROGRESS_UPDATES, show_progress: bool = True
    ) -> None:
        """Initialize progress reporter.

        Args:
            total_stages: Total number of stages to report (max 5).
            show_progress: Whether to show visual progress bar (default True).
        """
        if total_stages > MAX_PROGRESS_UPDATES:
            logger.warning(
                "Progress stages (%d) exceed limit (%d), capping to limit",
                total_stages,
                MAX_PROGRESS_UPDATES,
            )
            total_stages = MAX_PROGRESS_UPDATES

        self.total_stages = total_stages
        self.current_stage = 0
        self.show_progress = show_progress
        self.progress: Optional[Progress] = None
        self.task_id: Optional[TaskID] = None

        if self.show_progress:
            self.progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            )
            self.progress.start()
            self.task_id = self.progress.add_task(
                "Ingesting data...", total=total_stages
            )

    def report_stage(
        self, stage: IngestionStage, message: Optional[str] = None
    ) -> None:
        """Report progress for a pipeline stage.

        Args:
            stage: The stage being reported.
            message: Optional additional message.
        """
        self.current_stage += 1
        progress_pct = (self.current_stage / self.total_stages) * 100

        # Build description
        description = f"Stage {self.current_stage}/{self.total_stages} ({stage.value})"
        if message:
            description += f": {message}"

        # Update visual progress bar
        if self.progress and self.task_id is not None:
            self.progress.update(self.task_id, advance=1, description=description)

        # Also log for records
        logger.info(
            "Stage %d/%d (%s): %d%% %s",
            self.current_stage,
            self.total_stages,
            stage.value,
            progress_pct,
            f"- {message}" if message else "",
        )

    def is_complete(self) -> bool:
        """Check if all stages have been reported.

        Returns:
            bool: True if all stages completed.
        """
        return self.current_stage >= self.total_stages

    def finish(self) -> None:
        """Finalize and stop the progress bar."""
        if self.progress:
            self.progress.stop()
