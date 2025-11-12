"""Environment information capture for deterministic benchmarking.

This module provides utilities to capture execution environment metadata
including Python version, platform details, CPU information, and commit hash
to enable reproducible performance benchmarking.
"""

import logging
import platform
import subprocess
from typing import Optional


logger = logging.getLogger(__name__)


def get_python_version() -> str:
    """Get Python version string.

    Returns:
        Python version (e.g., '3.11.5')
    """
    return platform.python_version()


def get_platform_info() -> str:
    """Get platform information string.

    Returns:
        Platform string (e.g., 'Windows-10-10.0.19045-SP0')
    """
    return platform.platform()


def get_cpu_info() -> Optional[str]:
    """Get CPU model information if available.

    Returns:
        CPU model string or None if unavailable

    Note:
        Uses platform-specific methods to extract CPU model name.
        May return None on some systems or if information is unavailable.
    """
    try:
        if platform.system() == "Windows":
            import winreg

            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
            )
            cpu_name = winreg.QueryValueEx(key, "ProcessorNameString")[0]
            winreg.CloseKey(key)
            return cpu_name.strip()
        elif platform.system() == "Linux":
            with open("/proc/cpuinfo", encoding="utf-8") as f:
                for line in f:
                    if "model name" in line:
                        return line.split(":")[1].strip()
        elif platform.system() == "Darwin":
            result = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
    except Exception as e:
        logger.warning("Failed to retrieve CPU info: %s", str(e))

    return None


def get_git_commit_hash() -> Optional[str]:
    """Get current git commit hash if repository is available.

    Returns:
        Short commit hash (7 chars) or None if not a git repository

    Note:
        Uses git command-line tool. Returns None if git is not available
        or current directory is not a git repository.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        return result.stdout.strip()
    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
        subprocess.TimeoutExpired,
    ):
        logger.debug("Git commit hash unavailable (not a git repo or git not found)")
        return None


def capture_environment_metadata() -> dict:
    """Capture comprehensive environment metadata for reproducibility.

    Returns:
        Dictionary containing:
            - python_version: Python version string
            - platform: Platform information
            - cpu_model: CPU model name (if available)
            - commit_hash: Git commit hash (if available)

    Example:
        >>> metadata = capture_environment_metadata()
        >>> print(metadata['python_version'])
        '3.11.5'
    """
    return {
        "python_version": get_python_version(),
        "platform": get_platform_info(),
        "cpu_model": get_cpu_info(),
        "commit_hash": get_git_commit_hash(),
    }
