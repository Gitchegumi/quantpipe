#!/usr/bin/env python3
"""
Code quality check script for CI/CD pipeline.

Runs Pylint on src/ directory and enforces minimum score threshold.
Constitution Principle X requires Pylint score ≥ 8.0/10.

Usage:
    python scripts/ci/check_quality.py
    python scripts/ci/check_quality.py --threshold 8.0
    python scripts/ci/check_quality.py --path src/backtest
"""

import argparse
import subprocess
import sys
from pathlib import Path


DEFAULT_THRESHOLD = 8.0
DEFAULT_PATH = "src/"


def run_pylint(path: str) -> tuple[float, str]:
    """
    Run Pylint on specified path and extract score.

    Args:
        path: Directory or file path to lint

    Returns:
        Tuple of (score, output_text)

    Raises:
        RuntimeError: If pylint execution fails
    """
    try:
        result = subprocess.run(
            ["pylint", path, "--score=yes"],
            capture_output=True,
            text=True,
            check=False,
        )

        output = result.stdout + result.stderr

        # Extract score from output
        # Pylint outputs: "Your code has been rated at X.XX/10"
        for line in output.splitlines():
            if "rated at" in line:
                # Parse "Your code has been rated at 9.47/10"
                parts = line.split("rated at")[1].strip()
                score_str = parts.split("/")[0].strip()
                return float(score_str), output

        raise RuntimeError("Could not extract Pylint score from output")

    except FileNotFoundError:
        print("Error: pylint not found. Install it with: poetry add --group dev pylint")
        sys.exit(1)
    except subprocess.SubprocessError as e:
        raise RuntimeError(f"Pylint execution failed: {e}") from e


def check_quality(
    path: str = DEFAULT_PATH, threshold: float = DEFAULT_THRESHOLD
) -> bool:
    """
    Check code quality against threshold.

    Args:
        path: Directory or file path to check
        threshold: Minimum acceptable Pylint score

    Returns:
        True if quality meets threshold, False otherwise
    """
    print(f"Running Pylint on {path}...")
    print(f"Minimum required score: {threshold}/10")
    print("-" * 60)

    score, output = run_pylint(path)

    print(output)
    print("-" * 60)
    print(f"\nPylint Score: {score}/10")
    print(f"Threshold:    {threshold}/10")

    if score >= threshold:
        print(f"✓ PASS - Code quality meets threshold ({score} >= {threshold})")
        return True

    print(f"✗ FAIL - Code quality below threshold ({score} < {threshold})")
    print("\nConstitution Principle X requires Pylint score ≥ 8.0/10")
    print("Run 'pylint src/ --score=yes' to see detailed issues")
    return False


def main():
    """Main entry point for quality check script."""
    parser = argparse.ArgumentParser(
        description="Code quality check with Pylint threshold enforcement"
    )
    parser.add_argument(
        "--path", default=DEFAULT_PATH, help=f"Path to lint (default: {DEFAULT_PATH})"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help=f"Minimum Pylint score (default: {DEFAULT_THRESHOLD})",
    )

    args = parser.parse_args()

    # Validate path exists
    if not Path(args.path).exists():
        print(f"Error: Path does not exist: {args.path}")
        sys.exit(1)

    # Validate threshold
    if not 0 <= args.threshold <= 10:
        print(f"Error: Threshold must be between 0 and 10, got {args.threshold}")
        sys.exit(1)

    # Run quality check
    passed = check_quality(path=args.path, threshold=args.threshold)

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
