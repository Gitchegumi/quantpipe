"""Unit tests for ingestion module import isolation (T090, FR-017)."""

import ast
import sys
from pathlib import Path


def test_ingestion_has_no_indicator_imports():
    """Test that ingestion module has no imports from indicators package (FR-017).

    This enforces architectural separation: ingestion produces core dataset only,
    indicators are added via separate enrichment step.
    """
    ingestion_file = Path("src/data_io/ingestion.py")
    assert ingestion_file.exists(), f"File not found: {ingestion_file}"

    content = ingestion_file.read_text(encoding="utf-8")
    tree = ast.parse(content, filename=str(ingestion_file))

    # Collect all imports
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)

    # Check for any indicator-related imports
    forbidden_patterns = [
        "src.indicators",
        "indicators.",
        "indicator",  # Catch generic indicator imports
        "src.data_io.enrich",  # Enrichment should not be in ingestion
    ]

    violations = []
    for imp in imports:
        for pattern in forbidden_patterns:
            if pattern in imp.lower():
                violations.append(imp)

    assert not violations, (
        f"Ingestion module imports indicator-related modules: {violations}\n"
        "FR-017: Ingestion must be decoupled from indicator logic."
    )


def test_ingestion_module_no_indicator_references():
    """Test that ingestion module has no string references to indicator names."""
    ingestion_file = Path("src/data_io/ingestion.py")
    content = ingestion_file.read_text(encoding="utf-8")

    # Common indicator names that should NOT appear in ingestion
    # Use word boundaries to avoid false positives (e.g., "schema" contains "ema")
    forbidden_terms = [
        " ema ",
        " ema(",
        " ema.",
        "ema20",
        "ema50",
        " sma ",
        " rsi ",
        "stochrsi",
        "stoch_rsi",
        " atr ",
        "atr14",
        " macd ",
        "bollinger",
        "compute_indicator",
        "apply_indicator",
        "enrich(",
    ]

    # Check for forbidden terms (case-insensitive, excluding comments)
    lines = content.split("\n")
    violations = []

    for i, line in enumerate(lines, 1):
        # Skip comments
        if line.strip().startswith("#"):
            continue

        line_lower = line.lower()
        for term in forbidden_terms:
            if term in line_lower:
                violations.append((i, term, line.strip()))

    assert not violations, (
        "Ingestion module contains indicator-related terms:\n"
        + "\n".join(
            f"  Line {lineno}: '{term}' in {line}" for lineno, term, line in violations
        )
        + "\nFR-017: Ingestion must not reference indicator logic."
    )


def test_enrich_module_exists_separately():
    """Test that enrichment functionality exists in separate module."""
    # Check for enrichment at either location
    enrich_locations = [
        Path("src/data_io/enrich.py"),
        Path("src/indicators/enrich.py"),
    ]

    exists = any(loc.exists() for loc in enrich_locations)
    assert exists, f"Enrichment module should exist at one of: {enrich_locations}"


def test_ingestion_only_imports_core_utilities():
    """Test that ingestion only imports core utilities, not business logic."""
    ingestion_file = Path("src/data_io/ingestion.py")
    content = ingestion_file.read_text(encoding="utf-8")
    tree = ast.parse(content, filename=str(ingestion_file))

    # Collect all imports from src.data_io
    io_imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith("src.data_io"):
                for alias in node.names:
                    io_imports.append((node.module, alias.name))

    # Allowed core utilities
    allowed_modules = {
        "src.data_io.arrow_config",
        "src.data_io.cadence",
        "src.data_io.duplicates",
        "src.data_io.gaps",
        "src.data_io.gap_fill",
        "src.data_io.downcast",
        "src.data_io.perf_utils",
        "src.data_io.progress",
        "src.data_io.schema",
        "src.data_io.timezone_validate",
        "src.data_io.hash_utils",
        "src.data_io.iterator_mode",
        "src.data_io.errors",
        "src.data_io.logging_constants",  # Progress stage names
        "src.data_io.parquet_cache",  # Parquet caching for performance
    }

    # Check for unexpected imports
    violations = []
    for module, name in io_imports:
        if module not in allowed_modules:
            violations.append(f"{module}.{name}")

    assert not violations, (
        f"Ingestion imports unexpected modules: {violations}\n"
        "Only core utilities should be imported."
    )


if __name__ == "__main__":
    # Allow running as standalone script
    sys.exit(
        0
        if all(
            [
                test_ingestion_has_no_indicator_imports() is None,
                test_ingestion_module_no_indicator_references() is None,
                test_enrich_module_exists_separately() is None,
                test_ingestion_only_imports_core_utilities() is None,
            ]
        )
        else 1
    )
