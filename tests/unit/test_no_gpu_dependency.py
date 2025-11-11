"""Unit tests for GPU independence (T095, FR-028)."""

import sys

import pandas as pd
import pytest


def test_no_gpu_imports():
    """Test that codebase has no GPU-specific imports (FR-028)."""
    # Common GPU libraries
    gpu_libraries = [
        "cudf",
        "cupy",
        "numba.cuda",
        "torch",
        "tensorflow",
        "jax",
        "pycuda",
        "rapids",
    ]

    # Check if any GPU libraries are imported
    imported_gpu_libs = []
    for lib in gpu_libraries:
        if lib in sys.modules:
            imported_gpu_libs.append(lib)

    # GPU libraries should not be imported
    assert not imported_gpu_libs, (
        f"GPU libraries found in sys.modules: {imported_gpu_libs}\n"
        "FR-028: Code must run without GPU dependencies"
    )


def test_pandas_operations_work_without_gpu():
    """Test that core pandas operations work without GPU."""
    # Create DataFrame with typical ingestion operations
    df = pd.DataFrame(
        {
            "timestamp": pd.date_range(
                "2024-01-01", periods=100, freq="1min", tz="UTC"
            ),
            "open": range(100),
            "high": range(1, 101),
            "low": range(100),
            "close": range(100),
            "volume": [1000.0] * 100,
        }
    )

    # Sorting
    df_sorted = df.sort_values("timestamp")
    assert len(df_sorted) == 100

    # Duplicate detection
    df_deduped = df_sorted.drop_duplicates(subset=["timestamp"])
    assert len(df_deduped) == 100

    # Numeric operations
    df["is_gap"] = False
    assert "is_gap" in df.columns

    # All operations should work without GPU


def test_numpy_operations_work_without_gpu():
    """Test that NumPy operations work without GPU."""
    import numpy as np

    # Create arrays
    arr = np.array([1.0, 2.0, 3.0, 4.0, 5.0])

    # Vectorized operations
    result = arr * 2
    assert len(result) == 5
    assert result[0] == 2.0

    # Statistical operations
    mean = np.mean(arr)
    assert mean == 3.0

    # Diff operations (used in gap detection)
    diff = np.diff(arr)
    assert len(diff) == 4

    # All operations should work without GPU


def test_ingestion_module_no_gpu_references():
    """Test that ingestion module has no GPU-specific code references."""
    from pathlib import Path

    ingestion_file = Path("src/io/ingestion.py")
    if not ingestion_file.exists():
        pytest.skip("Ingestion file not found")

    content = ingestion_file.read_text(encoding="utf-8")

    # GPU-specific terms that should NOT appear
    gpu_terms = [
        "cudf",
        "cupy",
        "cuda",
        ".gpu(",
        "gpu=",
        "device=",
        "to_gpu",
        "rapids",
    ]

    violations = []
    for term in gpu_terms:
        if term.lower() in content.lower():
            violations.append(term)

    assert not violations, (
        f"GPU-specific terms found in ingestion: {violations}\n"
        "FR-028: Ingestion must not require GPU"
    )


def test_arrow_backend_independent_of_gpu():
    """Test that Arrow backend configuration works without GPU."""
    from src.io.arrow_config import configure_arrow_backend, detect_backend

    # Configure backend
    result = configure_arrow_backend()

    # Should return valid backend without GPU
    assert result in ["arrow", "pandas"]

    # Detection should work
    detected = detect_backend()
    assert detected in ["arrow", "pandas"]


def test_downcast_works_without_gpu():
    """Test that downcast operations work without GPU."""
    from src.io.downcast import downcast_numeric_columns

    df = pd.DataFrame(
        {
            "col1": [1.0, 2.0, 3.0],
            "col2": [4.0, 5.0, 6.0],
        }
    )

    result_df, downcasted_cols = downcast_numeric_columns(df)

    # Should work without GPU
    assert isinstance(result_df, pd.DataFrame)
    assert isinstance(downcasted_cols, list)


def test_gap_detection_works_without_gpu():
    """Test that gap detection works without GPU."""
    from src.io.gaps import detect_gaps

    timestamps = pd.date_range("2024-01-01", periods=10, freq="1min", tz="UTC")

    # Create gaps by skipping some timestamps
    df = pd.DataFrame(
        {
            "timestamp_utc": [timestamps[i] for i in [0, 1, 2, 5, 6, 9]],
            "value": [1, 2, 3, 4, 5, 6],
        }
    )

    gaps = detect_gaps(df, timeframe_minutes=1)

    # Should detect gaps without GPU
    assert isinstance(gaps, list)


def test_gpu_extension_hook_is_future():
    """Test that GPU extension hook is documented as future enhancement."""
    from pathlib import Path

    arrow_config_file = Path("src/io/arrow_config.py")
    if not arrow_config_file.exists():
        pytest.skip("Arrow config file not found")

    content = arrow_config_file.read_text(encoding="utf-8")

    # Should mention GPU as future enhancement
    # This documents that GPU support is planned but not required
    gpu_mentioned = "gpu" in content.lower()

    if gpu_mentioned:
        # Should be marked as future/optional
        assert any(
            keyword in content.lower()
            for keyword in ["future", "enhancement", "optional", "hook"]
        )


def test_no_gpu_in_dependencies():
    """Test that GPU libraries are not in project dependencies."""
    from pathlib import Path

    pyproject_file = Path("pyproject.toml")
    if not pyproject_file.exists():
        pytest.skip("pyproject.toml not found")

    content = pyproject_file.read_text(encoding="utf-8")

    # GPU libraries that should NOT be dependencies
    gpu_deps = [
        "cudf",
        "cupy",
        "torch",
        "tensorflow",
        "jax",
        "pycuda",
        "rapids",
    ]

    violations = []
    for dep in gpu_deps:
        if dep in content.lower():
            violations.append(dep)

    assert not violations, (
        f"GPU dependencies found in pyproject.toml: {violations}\n"
        "FR-028: GPU libraries must not be required dependencies"
    )
