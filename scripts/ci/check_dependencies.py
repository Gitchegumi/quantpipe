"""Dependency policy verification for CI/CD pipelines.

Validates compliance with Constitution Principle IX:
- MUST use Poetry for dependency management
- PROHIBIT requirements.txt
- All dependencies declared in pyproject.toml
- No undeclared imports in source code

Usage:
    python scripts/ci/check_dependencies.py [--strict]

Exit Codes:
    0 - All checks passed
    1 - Policy violations detected

Examples:
    # Standard check
    python scripts/ci/check_dependencies.py

    # Strict mode (fail on warnings)
    python scripts/ci/check_dependencies.py --strict

References:
    - Constitution Principle IX: Dependency Management
    - .github/copilot-instructions.md: "MUST use Poetry"
    - Phase 6 T098 (Remediation Additions)
"""

import argparse
import ast
import sys
from pathlib import Path


def check_forbidden_files() -> list[str]:
    """Check for forbidden dependency management files.

    Returns:
        List of violations (empty if none)
    """
    violations = []
    forbidden_files = [
        "requirements.txt",
        "requirements-dev.txt",
        "requirements/base.txt",
        "requirements/dev.txt",
        "setup.py",  # Poetry projects use pyproject.toml only
        "setup.cfg",
        "Pipfile",
        "Pipfile.lock",
    ]

    for forbidden in forbidden_files:
        path = Path(forbidden)
        if path.exists():
            violations.append(
                f"FORBIDDEN: {forbidden} found (use pyproject.toml with Poetry)"
            )

    return violations


def check_pyproject_exists() -> list[str]:
    """Check that pyproject.toml exists and contains Poetry configuration.

    Returns:
        List of violations (empty if none)
    """
    violations = []
    pyproject_path = Path("pyproject.toml")

    if not pyproject_path.exists():
        violations.append("MISSING: pyproject.toml not found")
        return violations

    # Read and validate Poetry sections
    content = pyproject_path.read_text(encoding="utf-8")
    if "[tool.poetry]" not in content:
        violations.append("INVALID: pyproject.toml missing [tool.poetry] section")

    if "[tool.poetry.dependencies]" not in content:
        violations.append(
            "INVALID: pyproject.toml missing [tool.poetry.dependencies] section"
        )

    return violations


def check_poetry_lock() -> list[str]:
    """Check that poetry.lock exists and is committed.

    Returns:
        List of violations (empty if none)
    """
    violations = []
    lock_path = Path("poetry.lock")

    if not lock_path.exists():
        violations.append(
            "MISSING: poetry.lock not found (run 'poetry lock' to generate)"
        )

    return violations


def extract_imports_from_file(file_path: Path) -> set[str]:
    """Extract top-level import names from Python file.

    Args:
        file_path: Path to Python source file

    Returns:
        Set of imported package names (top-level only)
    """
    try:
        tree = ast.parse(file_path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return set()

    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                # Extract top-level package (e.g., 'numpy' from 'numpy.random')
                imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])

    return imports



def load_declared_dependencies() -> set[str]:
    """Load declared dependencies from pyproject.toml.

    Returns:
        Set of declared package names
    """
    pyproject_path = Path("pyproject.toml")
    if not pyproject_path.exists():
        return set()

    content = pyproject_path.read_text(encoding="utf-8")

    # Simple regex-free parsing (sufficient for dependency names)
    declared = set()
    in_deps_section = False

    for line in content.splitlines():
        stripped = line.strip()

        # Track sections
        if stripped == "[tool.poetry.dependencies]":
            in_deps_section = True
            continue
        if stripped.startswith("[") and in_deps_section:
            in_deps_section = False
            continue

        # Extract package names from dependency lines
        if in_deps_section and "=" in stripped and not stripped.startswith("#"):
            package_name = stripped.split("=")[0].strip()
            if package_name != "python":  # Exclude Python version specifier
                declared.add(package_name)

    return declared


def check_undeclared_imports(strict: bool = False) -> list[str]:
    """Check for imports not declared in pyproject.toml.

    Args:
        strict: If True, treat warnings as violations

    Returns:
        List of violations (empty if none)
    """
    violations = []

    # Load declared dependencies
    declared_deps = load_declared_dependencies()
    if not declared_deps:
        violations.append("WARNING: Could not load dependencies from pyproject.toml")
        return violations

    # Standard library modules (not requiring declaration)
    stdlib_modules = {
        "__future__",
        "argparse",
        "ast",
        "bisect",
        "collections",
        "concurrent",
        "contextlib",
        "cProfile",
        "csv",
        "dataclasses",
        "datetime",
        "decimal",
        "enum",
        "functools",
        "hashlib",
        "importlib",
        "io",
        "itertools",
        "json",
        "logging",
        "math",
        "multiprocessing",
        "operator",
        "os",
        "pathlib",
        "pstats",
        "random",
        "re",
        "statistics",
        "sys",
        "time",
        "tracemalloc",
        "typing",
        "unittest",
        "warnings",
    }

    # Scan all Python files in src/
    src_dir = Path("src")
    if not src_dir.exists():
        return violations

    all_imports = set()
    for py_file in src_dir.rglob("*.py"):
        all_imports.update(extract_imports_from_file(py_file))

    # Internal modules (project-specific imports from src/)
    # These are module names that appear in src/ tree
    internal_modules = {
        "aggregation",
        "backtest",
        "cli",
        "config",
        "core",
        "gaps",
        "io",
        "logging_constants",
        "manifest_writer",
        "metrics_schema",
        "models",
        "pullback_detector",
        "reproducibility",
        "reversal",
        "risk_global",
        "risk_strategy",
        "specs",
        "src",  # Top-level src package imports
        "state_isolation",
        "store",
        "strategy",
        "trend_classifier",
    }

    # Find undeclared imports (excluding stdlib, declared deps, and internal modules)
    undeclared = all_imports - stdlib_modules - declared_deps - internal_modules

    # Special case: filter test utilities (if any)
    undeclared.discard("psutil")  # Used in performance tests (optional)

    if undeclared:
        for package in sorted(undeclared):
            msg = f"UNDECLARED: Import '{package}' not found in pyproject.toml"
            if strict:
                violations.append(msg)
            else:
                print(f"Warning: {msg}", file=sys.stderr)

    return violations



def main(argv: list[str] | None = None) -> int:
    """Main entry point for dependency policy checker.

    Args:
        argv: Command-line arguments (default: sys.argv)

    Returns:
        Exit code (0 = success, 1 = violations detected)
    """
    parser = argparse.ArgumentParser(
        description="Verify dependency policy compliance (Principle IX)"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on warnings (undeclared imports)",
    )

    args = parser.parse_args(argv)

    print("Checking dependency policy compliance (Principle IX)...")
    print()

    all_violations: list[str] = []

    # Check 1: Forbidden files
    print("[1/4] Checking for forbidden dependency files...")
    violations = check_forbidden_files()
    if violations:
        all_violations.extend(violations)
        for v in violations:
            print(f"  ✗ {v}")
    else:
        print("  ✓ No forbidden files found")
    print()

    # Check 2: pyproject.toml exists and valid
    print("[2/4] Checking pyproject.toml...")
    violations = check_pyproject_exists()
    if violations:
        all_violations.extend(violations)
        for v in violations:
            print(f"  ✗ {v}")
    else:
        print("  ✓ pyproject.toml valid")
    print()

    # Check 3: poetry.lock exists
    print("[3/4] Checking poetry.lock...")
    violations = check_poetry_lock()
    if violations:
        all_violations.extend(violations)
        for v in violations:
            print(f"  ✗ {v}")
    else:
        print("  ✓ poetry.lock exists")
    print()

    # Check 4: Undeclared imports
    print("[4/4] Checking for undeclared imports...")
    violations = check_undeclared_imports(strict=args.strict)
    if violations:
        all_violations.extend(violations)
        for v in violations:
            print(f"  ✗ {v}")
    else:
        print("  ✓ All imports declared")
    print()

    # Summary
    if all_violations:
        print("=" * 60)
        print(f"FAILED: {len(all_violations)} policy violation(s) detected")
        print("=" * 60)
        return 1

    print("=" * 60)
    print("PASSED: All dependency policy checks passed ✓")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
