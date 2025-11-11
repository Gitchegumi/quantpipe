"""Logging format enforcement script (T087, NFR-004, Principle X).

Ensures all logging calls use lazy % formatting instead of f-strings.
This is a focused wrapper around check_logging_and_docs.py for CI integration.

References:
- NFR-004: Lazy % formatting mandatory
- Constitution Principle X: W1203 warnings must be fixed
- Copilot instructions: "MUST use lazy % formatting"

Usage:
    python scripts/ci/check_logging_format.py
    python scripts/ci/check_logging_format.py src/io/
"""

import ast
import sys
from pathlib import Path


class LoggingStyleChecker(ast.NodeVisitor):
    """AST visitor to check for f-string usage in logging calls."""

    def __init__(self, filename: str):
        self.filename = filename
        self.violations = []

    def visit_Call(self, node: ast.Call):
        """Check logging calls for f-string usage."""
        # Check if this is a logging call (logger.info, logger.warning, etc.)
        if isinstance(node.func, ast.Attribute):
            if node.func.attr in {
                "debug",
                "info",
                "warning",
                "error",
                "critical",
            }:
                # Check if first argument is an f-string
                if node.args and isinstance(node.args[0], ast.JoinedStr):
                    self.violations.append(
                        (
                            node.lineno,
                            "F-string used in logging call. Use lazy % formatting.",
                        )
                    )

        self.generic_visit(node)


def check_file(filepath: Path):
    """Check a single Python file for logging format violations."""
    try:
        content = filepath.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(filepath))
    except (SyntaxError, UnicodeDecodeError) as e:
        print(f"Error parsing {filepath}: {e}")
        return []

    checker = LoggingStyleChecker(str(filepath))
    checker.visit(tree)
    return [(str(filepath), lineno, msg) for lineno, msg in checker.violations]


def main():
    """Run logging format checks on source files."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Check logging format compliance (lazy % formatting)"
    )
    parser.add_argument(
        "paths",
        nargs="*",
        default=["src/", "tests/"],
        help="Paths to check (default: src/ tests/)",
    )
    args = parser.parse_args()

    violations = []
    for path_str in args.paths:
        path = Path(path_str)
        if path.is_file():
            files = [path]
        else:
            files = list(path.rglob("*.py"))

        for file_path in files:
            file_violations = check_file(file_path)
            violations.extend(file_violations)

    if violations:
        print("❌ Logging format violations found:")
        for filename, lineno, message in violations:
            print(f"  {filename}:{lineno}: {message}")
        print(
            f"\nTotal violations: {len(violations)}\n"
            "Fix: Replace f-strings with lazy % formatting in logging calls."
        )
        return 1

    print("✓ All logging calls use lazy % formatting")
    return 0


if __name__ == "__main__":
    sys.exit(main())
