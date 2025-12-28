"""Unit tests for ScaffoldGenerator.

Tests scaffold template rendering, file generation, and Python syntax validity.
"""

import shutil
import tempfile
from pathlib import Path

import pytest

from src.strategy.scaffold.generator import ScaffoldGenerator, ScaffoldResult


class TestScaffoldGenerator:
    """Tests for ScaffoldGenerator class."""

    def test_generate_creates_strategy_directory(self, tmp_path: Path) -> None:
        """Generator creates strategy directory with expected files."""
        generator = ScaffoldGenerator()
        output_dir = tmp_path / "test_strategy"

        result = generator.generate("test_strategy", output_dir=output_dir)

        assert result.success
        assert output_dir.exists()
        assert (output_dir / "strategy.py").exists()
        assert (output_dir / "__init__.py").exists()
        assert (output_dir / "signal_generator.py").exists()

    def test_generate_with_invalid_name_fails(self) -> None:
        """Generator rejects invalid Python identifiers."""
        generator = ScaffoldGenerator()

        # Names starting with numbers
        result = generator.generate("123strategy")
        assert not result.success
        assert "Invalid strategy name" in (result.error or "")

        # Names with spaces
        result = generator.generate("my strategy")
        assert not result.success

        # Names with special characters
        result = generator.generate("my-strategy")
        assert not result.success

    def test_generate_fails_if_directory_exists(self, tmp_path: Path) -> None:
        """Generator fails if output directory already exists."""
        generator = ScaffoldGenerator()
        output_dir = tmp_path / "existing_strategy"
        output_dir.mkdir()

        result = generator.generate("existing_strategy", output_dir=output_dir)

        assert not result.success
        assert "already exists" in (result.error or "")

    def test_generated_files_are_valid_python(self, tmp_path: Path) -> None:
        """Generated files have valid Python syntax."""
        generator = ScaffoldGenerator()
        output_dir = tmp_path / "valid_python_test"

        result = generator.generate("valid_python_test", output_dir=output_dir)

        assert result.success
        for file_path in result.created_files:
            content = file_path.read_text()
            # This will raise SyntaxError if invalid
            compile(content, str(file_path), "exec")

    def test_generate_with_description_and_tags(self, tmp_path: Path) -> None:
        """Generator includes description and tags in template."""
        generator = ScaffoldGenerator()
        output_dir = tmp_path / "tagged_strategy"

        result = generator.generate(
            name="tagged_strategy",
            output_dir=output_dir,
            description="A test strategy with tags",
            tags=["trend", "momentum"],
        )

        assert result.success
        strategy_content = (output_dir / "strategy.py").read_text()
        assert "A test strategy with tags" in strategy_content
        assert '"trend"' in strategy_content
        assert '"momentum"' in strategy_content

    def test_class_name_conversion(self, tmp_path: Path) -> None:
        """Generator converts snake_case to PascalCase for class name."""
        generator = ScaffoldGenerator()
        output_dir = tmp_path / "my_awesome_strategy"

        result = generator.generate("my_awesome_strategy", output_dir=output_dir)

        assert result.success
        strategy_content = (output_dir / "strategy.py").read_text()
        assert "class MyAwesomeStrategy" in strategy_content
        assert "MY_AWESOME_STRATEGY_STRATEGY" in strategy_content

    def test_scaffold_result_contains_created_files(self, tmp_path: Path) -> None:
        """ScaffoldResult lists all created files."""
        generator = ScaffoldGenerator()
        output_dir = tmp_path / "result_test"

        result = generator.generate("result_test", output_dir=output_dir)

        assert result.success
        assert len(result.created_files) == 3
        file_names = {f.name for f in result.created_files}
        assert file_names == {"strategy.py", "__init__.py", "signal_generator.py"}
