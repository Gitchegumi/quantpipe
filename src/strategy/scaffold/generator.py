"""Strategy scaffold generator using Jinja2 templates.

This module provides the ScaffoldGenerator class for creating new
strategy directories from templates.

Example:
    from src.strategy.scaffold.generator import ScaffoldGenerator

    generator = ScaffoldGenerator()
    result = generator.generate("my_strategy")
    print(f"Created: {result.created_files}")
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from jinja2 import Environment, FileSystemLoader


logger = logging.getLogger(__name__)

# Template directory relative to this file
TEMPLATE_DIR = Path(__file__).parent / "templates"


@dataclass
class ScaffoldResult:
    """Result of scaffold generation.

    Attributes:
        success: Whether generation succeeded.
        created_files: List of created file paths.
        strategy_dir: Path to created strategy directory.
        error: Error message if generation failed.
    """

    success: bool
    created_files: list[Path] = field(default_factory=list)
    strategy_dir: Path | None = None
    error: str | None = None


class ScaffoldGenerator:
    """Generator for creating new strategy directories from templates.

    Uses Jinja2 templates to create strategy files with proper
    structure and TODO markers for customization.

    Attributes:
        template_dir: Directory containing Jinja2 templates.
    """

    def __init__(self, template_dir: Path | None = None) -> None:
        """Initialize the scaffold generator.

        Args:
            template_dir: Optional custom template directory.
                         Defaults to built-in templates.
        """
        self.template_dir = template_dir or TEMPLATE_DIR
        self._env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            keep_trailing_newline=True,
        )

    def generate(
        self,
        name: str,
        output_dir: Path | None = None,
        description: str = "",
        tags: list[str] | None = None,
    ) -> ScaffoldResult:
        """Generate a new strategy from templates.

        Args:
            name: Strategy name (must be valid Python identifier).
            output_dir: Target directory. Defaults to src/strategy/<name>/.
            description: Optional strategy description.
            tags: Optional list of strategy tags.

        Returns:
            ScaffoldResult with success status and created files.

        Raises:
            ValueError: If name is not a valid Python identifier.
            FileExistsError: If output directory already exists.
        """
        # Validate name
        if not self._is_valid_identifier(name):
            return ScaffoldResult(
                success=False,
                error=f"Invalid strategy name: '{name}'. Must be a valid Python "
                "identifier (alphanumeric and underscores, not starting "
                "with a number).",
            )

        # Determine output directory
        if output_dir is None:
            # Default to src/strategy/<name>/ relative to repo root
            repo_root = Path(__file__).parent.parent.parent.parent
            output_dir = repo_root / "strategy" / name

        # Check if directory exists
        if output_dir.exists():
            return ScaffoldResult(
                success=False,
                error=f"Directory already exists: {output_dir}",
            )

        # Prepare template context
        context = self._build_context(name, description, tags or [])

        try:
            # Create directory
            output_dir.mkdir(parents=True, exist_ok=False)
            created_files: list[Path] = []

            # Generate files from templates
            templates = [
                ("strategy.py.j2", "strategy.py"),
                ("__init__.py.j2", "__init__.py"),
                ("signal_generator.py.j2", "signal_generator.py"),
            ]

            for template_name, output_name in templates:
                template = self._env.get_template(template_name)
                content = template.render(**context)
                file_path = output_dir / output_name
                file_path.write_text(content, encoding="utf-8")
                created_files.append(file_path)
                logger.info("Created file: %s", file_path)

            logger.info(
                "Successfully scaffolded strategy '%s' at %s",
                name,
                output_dir,
            )

            return ScaffoldResult(
                success=True,
                created_files=created_files,
                strategy_dir=output_dir,
            )

        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.error("Failed to scaffold strategy: %s", exc)
            # Clean up partial directory if it was created
            if output_dir.exists():
                import shutil

                shutil.rmtree(output_dir, ignore_errors=True)
            return ScaffoldResult(
                success=False,
                error=str(exc),
            )

    def _is_valid_identifier(self, name: str) -> bool:
        """Check if name is a valid Python identifier."""
        if not name:
            return False
        # Must be alphanumeric + underscore, not start with number
        pattern = r"^[a-zA-Z_][a-zA-Z0-9_]*$"
        return bool(re.match(pattern, name))

    def _build_context(
        self,
        name: str,
        description: str,
        tags: list[str],
    ) -> dict:
        """Build template context dictionary."""
        # Convert snake_case to PascalCase for class name
        class_name = "".join(word.capitalize() for word in name.split("_"))
        if not class_name.endswith("Strategy"):
            class_name += "Strategy"

        # Create constant name (UPPER_SNAKE_CASE)
        constant_name = name.upper() + "_STRATEGY"

        # Format tags as Python list literal
        if tags:
            tags_literal = ", ".join(f'"{tag}"' for tag in tags)
        else:
            tags_literal = '"custom"'

        return {
            "strategy_name": name,
            "strategy_class_name": class_name,
            "strategy_constant": constant_name,
            "description": description or f"{class_name} trading strategy.",
            "tags_list": tags_literal,
        }


__all__ = ["ScaffoldGenerator", "ScaffoldResult"]
