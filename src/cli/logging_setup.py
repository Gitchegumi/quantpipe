"""
Structured logging configuration for CLI commands.

This module sets up Python logging with structured JSON output and
configurable log levels. Uses Rich for human-friendly terminal output
and supports file-based JSON logs for production.
"""

import logging
from pathlib import Path
import sys

from rich.console import Console
from rich.logging import RichHandler


def setup_logging(
    level: str = "INFO",
    log_file: Path | None = None,
    use_json: bool = False,
) -> None:
    """
    Configure Python logging for the trading strategy application.

    Sets up logging with Rich handler for terminal output and optionally
    writes structured JSON logs to a file.

    Args:
        level: Logging level ("DEBUG", "INFO", "WARNING", "ERROR").
        log_file: Optional path to write JSON logs.
        use_json: If True, format file logs as JSON (default False).

    Examples:
        >>> from pathlib import Path
        >>> setup_logging(level="DEBUG", log_file=Path("logs/backtest.log"))
        >>> import logging
        >>> logger = logging.getLogger(__name__)
        >>> logger.info("Starting backtest")
    """
    # Convert level string to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Conditionally add Rich handler for terminal output or a basic StreamHandler
    if sys.stderr.isatty():
        console = Console(stderr=True)
        rich_handler = RichHandler(
            console=console,
            show_time=True,
            show_path=True,
            markup=True,
            rich_tracebacks=True,
        )
        rich_handler.setLevel(numeric_level)
        rich_formatter = logging.Formatter(
            "%(message)s",
            datefmt="[%Y-%m-%d %H:%M:%S]",
        )
        rich_handler.setFormatter(rich_formatter)
        root_logger.addHandler(rich_handler)
    else:
        # Use a basic StreamHandler for non-interactive environments
        stream_handler = logging.StreamHandler(sys.stderr)
        stream_handler.setLevel(numeric_level)
        basic_formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s - %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        stream_handler.setFormatter(basic_formatter)
        root_logger.addHandler(stream_handler)

    # Add file handler if requested
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)

        if use_json:
            # JSON formatter (basic implementation - can be enhanced with python-json-logger)
            file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
            file_handler.setLevel(numeric_level)
            json_formatter = JSONFormatter()
            file_handler.setFormatter(json_formatter)
            root_logger.addHandler(file_handler)
        else:
            # Standard text formatter
            file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
            file_handler.setLevel(numeric_level)
            file_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)

    # Log initial configuration
    root_logger.debug(
        "Logging configured: level=%s, file=%s, json=%s",
        level,
        log_file if log_file else "None",
        use_json,
    )


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging.

    Converts log records to JSON format with timestamp, level, logger name,
    message, and optional exception info.

    Examples:
        >>> import logging
        >>> handler = logging.StreamHandler()
        >>> handler.setFormatter(JSONFormatter())
        >>> logger = logging.getLogger("test")
        >>> logger.addHandler(handler)
        >>> logger.setLevel(logging.INFO)
        >>> logger.info("Test message")
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON string.

        Args:
            record: LogRecord to format.

        Returns:
            JSON-formatted log string.
        """
        import json
        from datetime import datetime

        log_data = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields if present
        if hasattr(record, "extra"):
            log_data["extra"] = record.extra

        return json.dumps(log_data)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.

    Args:
        name: Logger name (typically __name__).

    Returns:
        Configured logger instance.

    Examples:
        >>> logger = get_logger(__name__)
        >>> logger.info("This is a log message")
    """
    return logging.getLogger(name)
