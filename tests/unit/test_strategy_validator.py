"""Unit tests for strategy validator.

Tests validation of strategy contract conformance including:
- Missing method detection
- Invalid metadata detection
- Wrong signature detection
"""

import pytest

from src.strategy.base import StrategyMetadata
from src.strategy.validator import (
    StrategyValidationError,
    ValidationResult,
    validate_strategy,
)


class ValidStrategy:
    """A valid strategy that passes all validation checks."""

    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="valid_test_strategy",
            version="1.0.0",
            required_indicators=["ema20"],
            tags=["test"],
        )

    def generate_signals(self, candles: list, parameters: dict) -> list:
        return []


class TestValidatorMissingMethod:
    """Tests for detecting missing required methods."""

    def test_valid_strategy_passes(self) -> None:
        """Valid strategy passes validation."""
        strategy = ValidStrategy()
        result = validate_strategy(strategy, strict=False)

        assert result.is_valid
        assert len(result.errors) == 0
        assert result.strategy_name == "valid_test_strategy"

    def test_missing_generate_signals_fails(self) -> None:
        """Strategy missing generate_signals fails validation."""

        class MissingGenerateSignals:
            @property
            def metadata(self) -> StrategyMetadata:
                return StrategyMetadata(
                    name="missing_method",
                    version="1.0.0",
                    required_indicators=["ema20"],
                )

        strategy = MissingGenerateSignals()
        result = validate_strategy(strategy, strict=False)

        assert not result.is_valid
        assert any("generate_signals" in err for err in result.errors)

    def test_missing_metadata_fails(self) -> None:
        """Strategy missing metadata property fails validation."""

        class MissingMetadata:
            def generate_signals(self, candles: list, parameters: dict) -> list:
                return []

        strategy = MissingMetadata()
        result = validate_strategy(strategy, strict=False)

        assert not result.is_valid
        assert any("metadata" in err for err in result.errors)


class TestValidatorInvalidMetadata:
    """Tests for detecting invalid metadata fields."""

    def test_empty_name_fails(self) -> None:
        """Strategy with empty name fails validation."""

        class EmptyName:
            @property
            def metadata(self) -> StrategyMetadata:
                return StrategyMetadata(
                    name="",
                    version="1.0.0",
                    required_indicators=["ema20"],
                )

            def generate_signals(self, candles: list, parameters: dict) -> list:
                return []

        strategy = EmptyName()
        result = validate_strategy(strategy, strict=False)

        assert not result.is_valid
        assert any("name" in err.lower() for err in result.errors)

    def test_empty_version_fails(self) -> None:
        """Strategy with empty version fails validation."""

        class EmptyVersion:
            @property
            def metadata(self) -> StrategyMetadata:
                return StrategyMetadata(
                    name="test",
                    version="",
                    required_indicators=["ema20"],
                )

            def generate_signals(self, candles: list, parameters: dict) -> list:
                return []

        strategy = EmptyVersion()
        result = validate_strategy(strategy, strict=False)

        assert not result.is_valid
        assert any("version" in err.lower() for err in result.errors)

    def test_empty_indicators_fails(self) -> None:
        """Strategy with empty required_indicators fails validation."""

        class EmptyIndicators:
            @property
            def metadata(self) -> StrategyMetadata:
                return StrategyMetadata(
                    name="test",
                    version="1.0.0",
                    required_indicators=[],
                )

            def generate_signals(self, candles: list, parameters: dict) -> list:
                return []

        strategy = EmptyIndicators()
        result = validate_strategy(strategy, strict=False)

        assert not result.is_valid
        assert any("indicators" in err.lower() for err in result.errors)


class TestValidatorSignatureCheck:
    """Tests for detecting wrong method signatures."""

    def test_wrong_parameter_count_detected(self) -> None:
        """Strategy with wrong number of parameters is detected."""

        class WrongParamCount:
            @property
            def metadata(self) -> StrategyMetadata:
                return StrategyMetadata(
                    name="wrong_params",
                    version="1.0.0",
                    required_indicators=["ema20"],
                )

            def generate_signals(self) -> list:  # Missing parameters
                return []

        strategy = WrongParamCount()
        result = validate_strategy(strategy, strict=False)

        assert not result.is_valid
        assert any("parameter" in err.lower() for err in result.errors)


class TestValidatorStrictMode:
    """Tests for strict mode exception raising."""

    def test_strict_mode_raises_exception(self) -> None:
        """Strict mode raises StrategyValidationError on failure."""

        class InvalidStrategy:
            @property
            def metadata(self) -> StrategyMetadata:
                return StrategyMetadata(
                    name="",  # Invalid empty name
                    version="1.0.0",
                    required_indicators=["ema20"],
                )

            def generate_signals(self, candles: list, parameters: dict) -> list:
                return []

        strategy = InvalidStrategy()

        with pytest.raises(StrategyValidationError) as exc_info:
            validate_strategy(strategy, strict=True)

        assert "failed validation" in str(exc_info.value)
        assert len(exc_info.value.errors) > 0

    def test_non_strict_mode_returns_result(self) -> None:
        """Non-strict mode returns ValidationResult without raising."""

        class InvalidStrategy:
            @property
            def metadata(self) -> StrategyMetadata:
                return StrategyMetadata(
                    name="",
                    version="1.0.0",
                    required_indicators=["ema20"],
                )

            def generate_signals(self, candles: list, parameters: dict) -> list:
                return []

        strategy = InvalidStrategy()
        result = validate_strategy(strategy, strict=False)

        assert isinstance(result, ValidationResult)
        assert not result.is_valid


class TestValidatorSuggestions:
    """Tests for suggestion generation."""

    def test_suggestions_provided_for_missing_method(self) -> None:
        """Validator provides suggestions for missing methods."""

        class MissingMethod:
            @property
            def metadata(self) -> StrategyMetadata:
                return StrategyMetadata(
                    name="missing",
                    version="1.0.0",
                    required_indicators=["ema20"],
                )

        strategy = MissingMethod()
        result = validate_strategy(strategy, strict=False)

        assert len(result.suggestions) > 0
        assert any("generate_signals" in s for s in result.suggestions)

    def test_suggestions_for_empty_indicators(self) -> None:
        """Validator provides suggestions for empty indicators."""

        class EmptyIndicators:
            @property
            def metadata(self) -> StrategyMetadata:
                return StrategyMetadata(
                    name="test",
                    version="1.0.0",
                    required_indicators=[],
                )

            def generate_signals(self, candles: list, parameters: dict) -> list:
                return []

        strategy = EmptyIndicators()
        result = validate_strategy(strategy, strict=False)

        assert any("indicator" in s.lower() for s in result.suggestions)
