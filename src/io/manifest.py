"""
Data manifest loading and validation.

This module handles loading and verifying DataManifest objects that describe
market data provenance. It validates file checksums to ensure data integrity
and provides a type-safe interface for accessing manifest metadata.

Manifest files are JSON documents that record:
- Trading pair and timeframe
- Date range covered
- Source data provider
- SHA-256 checksum for verification
- Preprocessing notes
- Total candle count
- File path to raw data
"""

import hashlib
import json
import logging
from pathlib import Path

from ..models.core import DataManifest
from ..models.exceptions import DataIntegrityError

logger = logging.getLogger(__name__)


def _compute_file_checksum(file_path: Path) -> str:
    """
    Compute SHA-256 checksum of a file.

    Args:
        file_path: Path to the file to checksum.

    Returns:
        Hexadecimal SHA-256 hash string.

    Raises:
        FileNotFoundError: If file_path does not exist.

    Examples:
        >>> from pathlib import Path
        >>> path = Path("data/EURUSD_M5.csv")
        >>> checksum = _compute_file_checksum(path)
        >>> len(checksum)
        64
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)

    return sha256.hexdigest()


def load_manifest(manifest_path: Path, verify_checksum: bool = True) -> DataManifest:
    """
    Load and validate a data manifest from JSON file.

    Reads manifest metadata and optionally verifies the referenced data file's
    checksum against the stored value. This ensures data integrity per
    Constitution Principle VI.

    Manifest JSON Structure:
        {
            "pair": "EURUSD",
            "timeframe": "M5",
            "start_date": "2025-01-01",
            "end_date": "2025-01-31",
            "source_provider": "HistData.com",
            "checksum": "a1b2c3d4e5f6...",
            "preprocessing_notes": "Removed duplicates",
            "total_candles": 8928,
            "file_path": "data/raw/EURUSD_M5.csv"
        }

    Args:
        manifest_path: Path to JSON manifest file.
        verify_checksum: If True, verify data file checksum (default True).

    Returns:
        Validated DataManifest object.

    Raises:
        DataIntegrityError: If manifest is invalid or checksum verification fails.
        FileNotFoundError: If manifest_path does not exist.

    Examples:
        >>> from pathlib import Path
        >>> manifest_path = Path("data/manifests/EURUSD_M5_2025-01.json")
        >>> manifest = load_manifest(manifest_path)
        >>> print(f"{manifest.pair} {manifest.timeframe}: {manifest.total_candles} candles")
        EURUSD M5: 8928 candles
    """
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest file not found: {manifest_path}")

    logger.info("Loading manifest from %s", manifest_path)

    # Read and parse JSON
    try:
        with open(manifest_path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise DataIntegrityError(
            f"Invalid JSON in manifest: {manifest_path}",
            context={"error": str(e)},
        ) from e

    # Validate required fields
    required_fields = [
        "pair",
        "timeframe",
        "start_date",
        "end_date",
        "source_provider",
        "checksum",
        "preprocessing_notes",
        "total_candles",
        "file_path",
    ]
    missing_fields = [f for f in required_fields if f not in data]
    if missing_fields:
        raise DataIntegrityError(
            "Missing required manifest fields",
            context={"missing": missing_fields, "file": str(manifest_path)},
        )

    # Resolve data file path (relative to manifest directory)
    data_file_path = manifest_path.parent / data["file_path"]
    if not data_file_path.exists():
        raise DataIntegrityError(
            "Data file referenced in manifest not found",
            context={
                "manifest": str(manifest_path),
                "data_file": str(data_file_path),
            },
        )

    # Verify checksum if requested
    if verify_checksum:
        logger.debug("Verifying checksum for %s", data_file_path)
        actual_checksum = _compute_file_checksum(data_file_path)
        expected_checksum = data["checksum"]

        if actual_checksum != expected_checksum:
            raise DataIntegrityError(
                "Data file checksum mismatch",
                context={
                    "file": str(data_file_path),
                    "expected": expected_checksum,
                    "actual": actual_checksum,
                },
            )
        logger.debug("Checksum verification passed")

    # Create DataManifest object
    manifest = DataManifest(
        pair=data["pair"],
        timeframe=data["timeframe"],
        date_range_start=data["start_date"],
        date_range_end=data["end_date"],
        source_provider=data["source_provider"],
        checksum=data["checksum"],
        preprocessing_notes=data["preprocessing_notes"],
        total_candles=data["total_candles"],
        file_path=str(data_file_path),  # Store absolute path
    )

    logger.info(
        "Manifest loaded: %s %s (%s to %s), %d candles",
        manifest.pair,
        manifest.timeframe,
        manifest.date_range_start,
        manifest.date_range_end,
        manifest.total_candles,
    )

    return manifest


def create_manifest(
    data_file_path: Path,
    pair: str,
    timeframe: str,
    start_date: str,
    end_date: str,
    source_provider: str,
    preprocessing_notes: str,
    total_candles: int,
    output_path: Path,
) -> DataManifest:
    """
    Create a new data manifest for a CSV file.

    Computes the data file's SHA-256 checksum and writes a JSON manifest.

    Args:
        data_file_path: Path to the CSV data file.
        pair: Trading pair (e.g., "EURUSD").
        timeframe: Candle timeframe (e.g., "M5").
        start_date: Start date in YYYY-MM-DD format.
        end_date: End date in YYYY-MM-DD format.
        source_provider: Data source (e.g., "HistData.com").
        preprocessing_notes: Description of preprocessing steps.
        total_candles: Total number of candles in the file.
        output_path: Path where manifest JSON will be written.

    Returns:
        Created DataManifest object.

    Raises:
        FileNotFoundError: If data_file_path does not exist.

    Examples:
        >>> from pathlib import Path
        >>> data_path = Path("data/raw/EURUSD_M5.csv")
        >>> manifest_path = Path("data/manifests/EURUSD_M5_2025-01.json")
        >>> manifest = create_manifest(
        ...     data_file_path=data_path,
        ...     pair="EURUSD",
        ...     timeframe="M5",
        ...     start_date="2025-01-01",
        ...     end_date="2025-01-31",
        ...     source_provider="HistData.com",
        ...     preprocessing_notes="Removed duplicates, filled gaps",
        ...     total_candles=8928,
        ...     output_path=manifest_path
        ... )
    """
    if not data_file_path.exists():
        raise FileNotFoundError(f"Data file not found: {data_file_path}")

    logger.info("Creating manifest for %s", data_file_path)

    # Compute checksum
    checksum = _compute_file_checksum(data_file_path)

    # Create manifest object
    manifest = DataManifest(
        pair=pair,
        timeframe=timeframe,
        date_range_start=start_date,
        date_range_end=end_date,
        source_provider=source_provider,
        checksum=checksum,
        preprocessing_notes=preprocessing_notes,
        total_candles=total_candles,
        file_path=str(data_file_path.absolute()),
    )

    # Write JSON (relative path for portability)
    relative_data_path = data_file_path.relative_to(output_path.parent)
    manifest_data = {
        "pair": manifest.pair,
        "timeframe": manifest.timeframe,
        "start_date": manifest.date_range_start,
        "end_date": manifest.date_range_end,
        "source_provider": manifest.source_provider,
        "checksum": manifest.checksum,
        "preprocessing_notes": manifest.preprocessing_notes,
        "total_candles": manifest.total_candles,
        "file_path": str(relative_data_path),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    logger.info("Manifest created: %s", output_path)

    return manifest
