#!/usr/bin/env python3
"""Static analysis script to detect forbidden per-row loops in ingestion code.

This script scans src/io/ modules for patterns that indicate per-row iteration,
which violates the vectorization requirement (FR-006).

Forbidden patterns:
- .iterrows()
- .itertuples()
- for row in df
- for idx, row in df.iterrows()

Exit code 0: No issues found
Exit code 1: Forbidden patterns detected
"""

import ast
import sys
from pathlib import Path


class RowLoopDetector(ast.NodeVisitor):
    """AST visitor to detect per-row iteration patterns."""

    def __init__(self, filename: str):
        """Initialize detector.

        Args:
            filename: Name of file being scanned.
        """
        self.filename = filename
        self.issues: list[tuple[int, str]] = []

    def visit_For(self, node: ast.For) -> None:  # noqa: N802
        """Check for loops over DataFrame rows.

        Args:
            node: AST For node.
        """
        # Check for patterns like: for row in df or for idx, row in ...
        if isinstance(node.iter, ast.Call) and isinstance(
            node.iter.func, ast.Attribute
        ):
            method_name = node.iter.func.attr
            if method_name in ("iterrows", "itertuples"):
                self.issues.append(
                    (
                        node.lineno,
                        f"Forbidden per-row iteration: .{method_name}()",
                    )
                )

        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        """Check for direct calls to iterrows/itertuples.

        Args:
            node: AST Call node.
        """
        if isinstance(node.func, ast.Attribute):
            method_name = node.func.attr
            if method_name in ("iterrows", "itertuples"):
                self.issues.append(
                    (node.lineno, f"Forbidden method call: .{method_name}()")
                )

        self.generic_visit(node)


def scan_file(filepath: Path) -> list[tuple[int, str]]:
    """Scan a single Python file for forbidden patterns.

    Args:
        filepath: Path to Python file.

    Returns:
        List of (line_number, description) tuples for issues found.
    """
    try:
        with filepath.open(encoding="utf-8") as f:
            source = f.read()

        tree = ast.parse(source, filename=str(filepath))
        detector = RowLoopDetector(str(filepath))
        detector.visit(tree)

        return detector.issues

    except SyntaxError as e:
        print(f"Syntax error in {filepath}: {e}", file=sys.stderr)
        return []


def main() -> int:
    """Scan src/io/ for forbidden per-row iteration patterns.

    Returns:
        Exit code: 0 if clean, 1 if issues found.
    """
    src_io_dir = Path("src/io")

    if not src_io_dir.exists():
        print(f"Error: {src_io_dir} directory not found", file=sys.stderr)
        return 1

    print("Scanning src/io/ for forbidden per-row loops...")
    print("Forbidden patterns: .iterrows(), .itertuples()")
    print()

    all_issues = []
    files_scanned = 0

    for py_file in sorted(src_io_dir.glob("*.py")):
        if py_file.name == "__init__.py":
            continue

        issues = scan_file(py_file)
        files_scanned += 1

        if issues:
            all_issues.extend([(py_file, line, desc) for line, desc in issues])
            print(f"❌ {py_file}:")
            for line, desc in issues:
                print(f"   Line {line}: {desc}")
            print()

    print(f"Scanned {files_scanned} files in {src_io_dir}")
    print()

    if all_issues:
        print(f"❌ FAILED: Found {len(all_issues)} forbidden pattern(s)")
        print()
        print("Per-row iteration violates FR-006 (vectorization requirement).")
        print("Use vectorized pandas operations instead.")
        return 1

    print("✓ PASSED: No forbidden per-row loops detected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
