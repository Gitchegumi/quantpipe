"""Logging style and documentation audit script (T063, FR-017).

This script audits Python source files for:
1. Lazy % formatting in logging calls (not f-strings)
2. Complete docstrings on all modules, classes, and functions
3. Type hints on all function signatures

References:
- FR-017: Enforce lazy logging, docstrings, type hints
- Constitution Principle VIII (PEP 8, PEP 257 compliance)
- Copilot instructions: "MUST use lazy % formatting"
"""

import argparse
import ast
import sys
from pathlib import Path
from typing import List, Tuple


class LoggingStyleChecker(ast.NodeVisitor):
    """AST visitor to check for f-string usage in logging calls."""

    def __init__(self, filename: str):
        self.filename = filename
        self.violations: List[Tuple[int, str]] = []

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
                            f"F-string used in logging call at line {node.lineno}. "
                            "Use lazy % formatting instead.",
                        )
                    )

        self.generic_visit(node)


class DocstringChecker(ast.NodeVisitor):
    """AST visitor to check for missing docstrings."""

    def __init__(self, filename: str):
        self.filename = filename
        self.violations: List[Tuple[int, str]] = []

    def visit_Module(self, node: ast.Module):
        """Check module-level docstring."""
        if not ast.get_docstring(node):
            self.violations.append((1, f"Module {self.filename} missing docstring"))
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        """Check class docstring."""
        if not ast.get_docstring(node):
            self.violations.append(
                (node.lineno, f"Class {node.name} missing docstring")
            )
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Check function docstring."""
        # Skip special methods like __init__, __repr__, etc.
        if not node.name.startswith("_") or node.name.startswith("__"):
            if not ast.get_docstring(node):
                # Allow test functions without docstrings
                if not (
                    "test" in self.filename.lower() and node.name.startswith("test_")
                ):
                    self.violations.append(
                        (
                            node.lineno,
                            f"Function {node.name} missing docstring",
                        )
                    )
        self.generic_visit(node)


class TypeHintChecker(ast.NodeVisitor):
    """AST visitor to check for missing type hints."""

    def __init__(self, filename: str):
        self.filename = filename
        self.violations: List[Tuple[int, str]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Check function type hints."""
        # Skip test functions and special methods
        if "test" in self.filename.lower() and node.name.startswith("test_"):
            self.generic_visit(node)
            return

        if node.name.startswith("__") and node.name.endswith("__"):
            self.generic_visit(node)
            return

        # Check return type annotation
        if node.returns is None and node.name != "__init__":
            self.violations.append(
                (
                    node.lineno,
                    f"Function {node.name} missing return type annotation",
                )
            )

        # Check parameter type annotations
        for arg in node.args.args:
            if arg.annotation is None and arg.arg != "self" and arg.arg != "cls":
                self.violations.append(
                    (
                        node.lineno,
                        f"Function {node.name} parameter '{arg.arg}' missing type annotation",
                    )
                )

        self.generic_visit(node)


def audit_file(filepath: Path) -> Tuple[int, int, int]:
    """Audit a single Python file for logging, docstring, and type hint issues.

    Args:
        filepath: Path to Python file to audit.

    Returns:
        Tuple of (logging_violations, docstring_violations, type_hint_violations).
    """
    try:
        content = filepath.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(filepath))
    except (SyntaxError, UnicodeDecodeError) as e:
        print(f"Error parsing {filepath}: {e}")
        return 0, 0, 0

    # Check logging style
    logging_checker = LoggingStyleChecker(str(filepath))
    logging_checker.visit(tree)

    # Check docstrings
    docstring_checker = DocstringChecker(str(filepath))
    docstring_checker.visit(tree)

    # Check type hints
    typehint_checker = TypeHintChecker(str(filepath))
    typehint_checker.visit(tree)

    # Report violations
    all_violations = (
        logging_checker.violations
        + docstring_checker.violations
        + typehint_checker.violations
    )

    if all_violations:
        print(f"\n{filepath}:")
        for lineno, message in sorted(all_violations):
            print(f"  Line {lineno}: {message}")

    return (
        len(logging_checker.violations),
        len(docstring_checker.violations),
        len(typehint_checker.violations),
    )


def main() -> int:
    """Main entry point for audit script."""
    parser = argparse.ArgumentParser(
        description="Audit Python files for logging style, docstrings, and type hints"
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=Path("src"),
        help="Path to audit (default: src/)",
    )
    parser.add_argument(
        "--fail-on-violations",
        action="store_true",
        help="Exit with error code if violations found",
    )

    args = parser.parse_args()

    total_logging = 0
    total_docstring = 0
    total_typehint = 0
    total_files = 0

    # Find all Python files
    python_files = list(args.path.rglob("*.py"))

    if not python_files:
        print(f"No Python files found in {args.path}")
        return 1

    print(f"Auditing {len(python_files)} Python files in {args.path}...")

    for filepath in python_files:
        logging_count, docstring_count, typehint_count = audit_file(filepath)
        total_logging += logging_count
        total_docstring += docstring_count
        total_typehint += typehint_count
        total_files += 1

    # Print summary
    print(f"\n{'='*60}")
    print(f"Audit Summary ({total_files} files)")
    print(f"{'='*60}")
    print(f"Logging violations (f-strings in logging): {total_logging}")
    print(f"Missing docstrings: {total_docstring}")
    print(f"Missing type hints: {total_typehint}")
    print(f"Total violations: {total_logging + total_docstring + total_typehint}")

    if args.fail_on_violations and (
        total_logging > 0 or total_docstring > 0 or total_typehint > 0
    ):
        print("\n[FAIL] Violations found")
        return 1
    else:
        print("\n[PASS] Audit complete")
        return 0


if __name__ == "__main__":
    sys.exit(main())
