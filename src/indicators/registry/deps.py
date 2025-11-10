"""Indicator dependency resolution utilities.

This module provides utilities for resolving indicator dependencies
using topological sorting to ensure correct computation order.
"""

import logging
from typing import Dict, List, Set

from .specs import IndicatorSpec

logger = logging.getLogger(__name__)


class DependencyCycleError(Exception):
    """Raised when a circular dependency is detected."""


def topological_sort(
    indicators: Dict[str, IndicatorSpec],
    requested: List[str],
) -> List[str]:
    """Sort indicators in dependency order using topological sort.

    Args:
        indicators: Dictionary of indicator name to spec.
        requested: List of requested indicator names.

    Returns:
        List[str]: Sorted list of indicator names in dependency order.

    Raises:
        DependencyCycleError: If a circular dependency is detected.
        KeyError: If a required indicator is not found.
    """
    # Build dependency graph
    graph: Dict[str, Set[str]] = {}
    in_degree: Dict[str, int] = {}

    # Initialize graph for all requested indicators
    for name in requested:
        if name not in indicators:
            raise KeyError(f"Indicator '{name}' not found in registry")

        graph[name] = set()
        in_degree[name] = 0

    # Build edges (dependencies)
    for name in requested:
        spec = indicators[name]

        for required in spec.requires:
            # Only track dependencies on other indicators, not core columns
            if required in requested:
                graph[required].add(name)
                in_degree[name] = in_degree.get(name, 0) + 1

    # Kahn's algorithm for topological sort
    result: List[str] = []
    queue: List[str] = [name for name in requested if in_degree[name] == 0]

    while queue:
        current = queue.pop(0)
        result.append(current)

        for neighbor in graph[current]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    # Check for cycles
    if len(result) != len(requested):
        remaining = set(requested) - set(result)
        raise DependencyCycleError(
            f"Circular dependency detected among indicators: "
            f"{', '.join(sorted(remaining))}"
        )

    logger.debug("Dependency resolution order: %s", " -> ".join(result))

    return result


def resolve_dependencies(
    indicators: Dict[str, IndicatorSpec],
    requested: List[str],
) -> List[IndicatorSpec]:
    """Resolve indicator dependencies and return specs in computation order.

    Args:
        indicators: Dictionary of indicator name to spec.
        requested: List of requested indicator names.

    Returns:
        List[IndicatorSpec]: List of indicator specs in dependency order.
    """
    sorted_names = topological_sort(indicators, requested)
    return [indicators[name] for name in sorted_names]
