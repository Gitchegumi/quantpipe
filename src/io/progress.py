"""Progress reporting utilities for ingestion pipeline.

This module provides utilities for reporting progress during ingestion
operations with a limit of ≤5 updates.
"""

import logging
from typing import Optional

from .logging_constants import IngestionStage, MAX_PROGRESS_UPDATES

logger = logging.getLogger(__name__)


class ProgressReporter:
    """Progress reporter for ingestion pipeline stages."""

    def __init__(self, total_stages: int = MAX_PROGRESS_UPDATES) -> None:
        """Initialize progress reporter.

        Args:
            total_stages: Total number of stages to report (max 5).
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

        log_msg = (
            f"Stage {self.current_stage}/{self.total_stages} "
            f"({stage.value}): {progress_pct:.0f}%"
        )

        if message:
            log_msg += f" - {message}"

        logger.info(log_msg)

    def is_complete(self) -> bool:
        """Check if all stages have been reported.

        Returns:
            bool: True if all stages completed.
        """
        return self.current_stage >= self.total_stages
