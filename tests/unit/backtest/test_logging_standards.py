"""
Logging standards verification tests.

Validates compliance with project logging standards:
- No f-string formatting in logging calls (W1203)
- Use lazy % formatting instead
- Adherence to Constitution Principle X
"""

# pylint: disable=unused-import, redefined-outer-name

import ast
import re
from pathlib import Path

import pytest


def find_python_files(directory: Path) -> list[Path]:
    """Find all Python files in directory, excluding __pycache__."""
    python_files = []
    for path in directory.rglob("*.py"):
        if "__pycache__" not in str(path):
            python_files.append(path)
    return python_files


def extract_logger_calls(source_code: str) -> list[tuple[int, str, str]]:
    """
    Extract logger calls from source code.

    Returns list of (line_number, method_name, format_arg) tuples.
    """
    tree = ast.parse(source_code)
    logger_calls = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            # Check if it's a logger.* call
            if isinstance(node.func, ast.Attribute):
                method_name = node.func.attr
                # Common logging methods
                if method_name in (
                    "debug",
                    "info",
                    "warning",
                    "error",
                    "critical",
                    "exception",
                ):
                    # Check first argument (message)
                    if node.args:
                        first_arg = node.args[0]
                        line_number = node.lineno

                        # Get the source representation
                        arg_repr = (
                            ast.unparse(first_arg) if hasattr(ast, "unparse") else ""
                        )

                        logger_calls.append((line_number, method_name, arg_repr))

    return logger_calls


def has_fstring_formatting(arg_repr: str) -> bool:
    """Check if argument uses f-string formatting."""
    # Check for f-string pattern: f"..." or f'...'
    return arg_repr.startswith('f"') or arg_repr.startswith("f'")


@pytest.fixture
def src_directory():
    """Get src directory path."""
    # Go up from tests/unit/backtest/ to project root, then to src
    return Path(__file__).parent.parent.parent.parent / "src"


@pytest.fixture
def all_src_files(src_directory):
    """Get all Python files in src directory."""
    return find_python_files(src_directory)


def test_no_fstring_in_logging_calls(all_src_files):
    """Test that no logging calls use f-string formatting (W1203)."""
    violations = []

    for filepath in all_src_files:
        with open(filepath, encoding="utf-8") as f:
            source = f.read()

        try:
            logger_calls = extract_logger_calls(source)
        except SyntaxError:
            # Skip files with syntax errors
            continue

        for line_number, method_name, arg_repr in logger_calls:
            if has_fstring_formatting(arg_repr):
                # Go up from tests/unit/backtest/ to project root for relative path
                relative_path = filepath.relative_to(
                    Path(__file__).parent.parent.parent.parent
                )
                violations.append(
                    f"{relative_path}:{line_number} - logger.{method_name}({arg_repr})"
                )

    if violations:
        message = (
            "Found f-string formatting in logging calls (W1203 violation).\n"
            "Use lazy % formatting instead:\n"
            "  ✗ logger.info(f'Processing {count} items')\n"
            "  ✓ logger.info('Processing %d items', count)\n\n"
            "Violations:\n" + "\n".join(violations)
        )
        pytest.fail(message)


def test_src_files_found(all_src_files):
    """Test that we found Python files to check."""
    assert len(all_src_files) > 0, "No Python files found in src directory"


def test_parser_can_extract_logger_calls():
    """Test that parser correctly identifies logger calls."""
    sample_code = """
import logging
logger = logging.getLogger(__name__)

def example():
    logger.info("Static message")
    logger.warning("Value: %s", value)
    logger.error(f"Bad: {value}")
    logger.debug("Count: %d", count)
"""

    calls = extract_logger_calls(sample_code)

    # Should find 4 logger calls
    assert len(calls) == 4

    # Check methods detected
    methods = [method for _, method, _ in calls]
    assert "info" in methods
    assert "warning" in methods
    assert "error" in methods
    assert "debug" in methods


def test_fstring_detection():
    """Test that f-string detection works correctly."""
    assert has_fstring_formatting('f"test"') is True
    assert has_fstring_formatting("f'test'") is True
    assert has_fstring_formatting('"test"') is False
    assert has_fstring_formatting("'test'") is False
    assert has_fstring_formatting('"Processing %s"') is False


def test_logging_standards_documented():
    """Test that logging standards are documented in copilot-instructions."""
    # Go up from tests/unit/backtest/ to project root, then to .github
    instructions_path = (
        Path(__file__).parent.parent.parent.parent
        / ".github"
        / "copilot-instructions.md"
    )

    with open(instructions_path, encoding="utf-8") as f:
        content = f.read()

    # Check for logging standards section
    assert "Logging Standards" in content or "logging" in content.lower()
    assert "lazy % formatting" in content or "W1203" in content
    assert "PROHIBITED" in content or "MUST" in content


def test_no_violations_in_backtest_module(src_directory):
    """Test that backtest module has no f-string logging violations."""
    backtest_dir = src_directory / "backtest"
    if not backtest_dir.exists():
        pytest.skip("Backtest directory not found")

    backtest_files = find_python_files(backtest_dir)
    violations = []

    for filepath in backtest_files:
        with open(filepath, encoding="utf-8") as f:
            source = f.read()

        try:
            logger_calls = extract_logger_calls(source)
        except SyntaxError:
            continue

        for line_number, method_name, arg_repr in logger_calls:
            if has_fstring_formatting(arg_repr):
                relative_path = filepath.relative_to(
                    Path(__file__).parent.parent.parent
                )
                violations.append(
                    f"{relative_path}:{line_number} - logger.{method_name}({arg_repr})"
                )

    assert (
        len(violations) == 0
    ), "Backtest module has f-string violations:\n" + "\n".join(violations)


def test_no_violations_in_strategy_module(src_directory):
    """Test that strategy module has no f-string logging violations."""
    strategy_dir = src_directory / "strategy"
    if not strategy_dir.exists():
        pytest.skip("Strategy directory not found")

    strategy_files = find_python_files(strategy_dir)
    violations = []

    for filepath in strategy_files:
        with open(filepath, encoding="utf-8") as f:
            source = f.read()

        try:
            logger_calls = extract_logger_calls(source)
        except SyntaxError:
            continue

        for line_number, method_name, arg_repr in logger_calls:
            if has_fstring_formatting(arg_repr):
                relative_path = filepath.relative_to(
                    Path(__file__).parent.parent.parent
                )
                violations.append(
                    f"{relative_path}:{line_number} - logger.{method_name}({arg_repr})"
                )

    assert (
        len(violations) == 0
    ), "Strategy module has f-string violations:\n" + "\n".join(violations)


def test_no_violations_in_cli_module(src_directory):
    """Test that CLI module has no f-string logging violations."""
    cli_dir = src_directory / "cli"
    if not cli_dir.exists():
        pytest.skip("CLI directory not found")

    cli_files = find_python_files(cli_dir)
    violations = []

    for filepath in cli_files:
        with open(filepath, encoding="utf-8") as f:
            source = f.read()

        try:
            logger_calls = extract_logger_calls(source)
        except SyntaxError:
            continue

        for line_number, method_name, arg_repr in logger_calls:
            if has_fstring_formatting(arg_repr):
                relative_path = filepath.relative_to(
                    Path(__file__).parent.parent.parent
                )
                violations.append(
                    f"{relative_path}:{line_number} - logger.{method_name}({arg_repr})"
                )

    assert len(violations) == 0, "CLI module has f-string violations:\n" + "\n".join(
        violations
    )
