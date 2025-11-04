"""Manifest writer for multi-strategy backtest reproducibility.

This module writes RunManifest instances to JSON files for audit trails
and reproducibility verification per FR-018, FR-023, SC-008.
"""

import json
import logging
from pathlib import Path
from src.models.run_manifest import RunManifest

logger = logging.getLogger(__name__)


def write_manifest(
    manifest: RunManifest,
    output_path: str | Path,
) -> None:
    """
    Write RunManifest to JSON file.

    Creates parent directories if needed. Serializes manifest with
    sorted keys for readability and deterministic output.

    Args:
        manifest: RunManifest instance to serialize.
        output_path: Path to output JSON file.

    Raises:
        IOError: If file cannot be written.
        TypeError: If manifest cannot be serialized.

    Examples:
        >>> from src.models.run_manifest import RunManifest
        >>> from datetime import datetime, timezone
        >>> manifest = RunManifest(
        ...     run_id="test_run_001",
        ...     strategies=["alpha", "beta"],
        ...     strategy_versions=["1.0.0", "1.0.0"],
        ...     weights=[0.6, 0.4],
        ...     global_drawdown_limit=None,
        ...     data_manifest_refs=["data/eurusd.json"],
        ...     start_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
        ...     end_time=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        ...     correlation_status="deferred",
        ...     deterministic_run_id="abc123def456",
        ...     global_abort_triggered=False,
        ...     risk_breaches=[]
        ... )
        >>> write_manifest(manifest, "/tmp/test_manifest.json")  # doctest: +SKIP
    """
    output_path = Path(output_path)

    # Create parent directories if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert manifest to dict
    manifest_dict = {
        "run_id": manifest.run_id,
        "strategies": list(manifest.strategies),
        "strategy_versions": list(manifest.strategy_versions),
        "weights": list(manifest.weights),
        "global_drawdown_limit": manifest.global_drawdown_limit,
        "data_manifest_refs": list(manifest.data_manifest_refs),
        "start_time": manifest.start_time.isoformat() if manifest.start_time else None,
        "end_time": manifest.end_time.isoformat() if manifest.end_time else None,
        "correlation_status": manifest.correlation_status,
        "deterministic_run_id": manifest.deterministic_run_id,
        "global_abort_triggered": manifest.global_abort_triggered,
        "risk_breaches": list(manifest.risk_breaches),
    }

    # Write with sorted keys for deterministic output
    try:
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(manifest_dict, f, indent=2, sort_keys=True)
        logger.info(
            "Wrote manifest: run_id=%s path=%s",
            manifest.run_id,
            output_path,
        )
    except (IOError, TypeError) as e:
        logger.error(
            "Failed to write manifest: run_id=%s path=%s error=%s",
            manifest.run_id,
            output_path,
            e,
        )
        raise


def compute_manifest_hash(manifest: RunManifest) -> str:
    """
    Compute SHA-256 hash of manifest for linking to metrics output.

    Args:
        manifest: RunManifest to hash.

    Returns:
        Lowercase hexadecimal SHA-256 hash (truncated to 16 chars).

    Examples:
        >>> from src.models.run_manifest import RunManifest
        >>> from datetime import datetime, timezone
        >>> manifest = RunManifest(
        ...     run_id="test",
        ...     strategies=["alpha"],
        ...     strategy_versions=["1.0.0"],
        ...     weights=[1.0],
        ...     global_drawdown_limit=None,
        ...     data_manifest_refs=["data.json"],
        ...     start_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
        ...     end_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
        ...     correlation_status="deferred",
        ...     deterministic_run_id="abc123",
        ...     global_abort_triggered=False,
        ...     risk_breaches=[]
        ... )
        >>> hash_val = compute_manifest_hash(manifest)
        >>> len(hash_val)
        16
    """
    import hashlib

    # Serialize manifest to canonical JSON
    manifest_dict = {
        "run_id": manifest.run_id,
        "strategies": list(manifest.strategies),
        "strategy_versions": list(manifest.strategy_versions),
        "weights": [float(w) for w in manifest.weights],
        "global_drawdown_limit": manifest.global_drawdown_limit,
        "data_manifest_refs": list(manifest.data_manifest_refs),
        "start_time": manifest.start_time.isoformat() if manifest.start_time else None,
        "end_time": manifest.end_time.isoformat() if manifest.end_time else None,
        "deterministic_run_id": manifest.deterministic_run_id,
    }

    canonical_json = json.dumps(manifest_dict, sort_keys=True, separators=(",", ":"))
    hash_obj = hashlib.sha256(canonical_json.encode("utf-8"))
    return hash_obj.hexdigest()[:16]


__all__ = ["write_manifest", "compute_manifest_hash"]
