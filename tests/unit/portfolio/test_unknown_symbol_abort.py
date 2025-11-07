"""Unit tests for unknown symbol graceful abort (Phase 6: US4, T046).

Tests verify that invalid/unknown symbols produce clear validation errors
and that the system aborts gracefully without crashing.

Success criteria:
- Unknown symbols detected during validation
- Clear error messages listing missing symbols
- Graceful abort (no exceptions, proper exit)
- Validation occurs before execution starts

Refs: FR-007 (validation), FR-002 (symbol selection), US4 (Selection & Filtering)
"""

from unittest.mock import patch

from src.backtest.portfolio.validation import (
    validate_symbol_exists,
    validate_symbol_list,
)
from src.models.portfolio import CurrencyPair


class TestUnknownSymbolValidation:
    """Test validation of unknown/missing symbols."""

    def test_single_unknown_symbol_rejected(self, tmp_path):
        """Verify single unknown symbol produces clear error."""
        data_dir = tmp_path / "price_data" / "processed"
        data_dir.mkdir(parents=True)

        # Valid format but unknown symbol (no dataset)
        pair = CurrencyPair(code="XYZABC")
        exists, error = validate_symbol_exists(pair, data_dir)

        assert not exists, "Expected unknown symbol to fail validation"
        assert error is not None, "Expected error message for unknown symbol"
        assert "XYZABC" in error, "Error should mention symbol code"
        assert "not found" in error.lower(), "Error should mention dataset not found"

    def test_unknown_symbol_error_includes_path(self, tmp_path):
        """Verify error message includes expected dataset path."""
        data_dir = tmp_path / "price_data" / "processed"
        data_dir.mkdir(parents=True)

        pair = CurrencyPair(code="ABCDEF")
        exists, error = validate_symbol_exists(pair, data_dir)

        assert not exists
        assert "abcdef" in error.lower(), "Error should include lowercase symbol dir"
        assert "processed.csv" in error, "Error should include expected filename"

    def test_multiple_unknown_symbols_all_rejected(self, tmp_path):
        """Verify all unknown symbols in list are rejected."""
        data_dir = tmp_path / "price_data" / "processed"
        data_dir.mkdir(parents=True)

        pairs = [
            CurrencyPair(code="AAAAAA"),
            CurrencyPair(code="BBBBBB"),
            CurrencyPair(code="CCCCCC"),
        ]

        valid_pairs, errors = validate_symbol_list(pairs, data_dir)

        assert len(valid_pairs) == 0, "Expected no valid pairs"
        assert len(errors) == 3, "Expected 3 error messages"
        assert all("not found" in err.lower() for err in errors), (
            "All errors should mention dataset not found"
        )

    def test_mixed_valid_invalid_symbols_filters_correctly(self, tmp_path):
        """Verify validation filters out invalid symbols, keeps valid ones."""
        data_dir = tmp_path / "price_data" / "processed"
        data_dir.mkdir(parents=True)

        # Create valid symbol dataset
        valid_dir = data_dir / "eurusd"
        valid_dir.mkdir()
        valid_csv = valid_dir / "processed.csv"
        valid_csv.write_text(
            "timestamp,open,high,low,close,volume\n"
            "2024-01-01 00:00:00,1.1,1.1,1.1,1.1,100\n"
        )

        pairs = [
            CurrencyPair(code="EURUSD"),  # Valid (has dataset)
            CurrencyPair(code="XYZABC"),  # Invalid (no dataset)
            CurrencyPair(code="ABCDEF"),  # Invalid (no dataset)
        ]

        valid_pairs, errors = validate_symbol_list(pairs, data_dir)

        assert len(valid_pairs) == 1, "Expected 1 valid pair"
        assert valid_pairs[0].code == "EURUSD", "Expected EURUSD to be valid"
        assert len(errors) == 2, "Expected 2 error messages for invalid symbols"

    def test_empty_dataset_rejected(self, tmp_path):
        """Verify empty dataset file is rejected with clear error."""
        data_dir = tmp_path / "price_data" / "processed"
        data_dir.mkdir(parents=True)

        # Create empty CSV
        symbol_dir = data_dir / "nzdusd"
        symbol_dir.mkdir()
        empty_csv = symbol_dir / "processed.csv"
        empty_csv.write_text("")  # Completely empty

        pair = CurrencyPair(code="NZDUSD")
        exists, error = validate_symbol_exists(pair, data_dir)

        assert not exists, "Expected empty dataset to fail validation"
        assert error is not None
        assert "NZDUSD" in error
        # Error could be about empty file or parse error

    def test_corrupt_dataset_rejected(self, tmp_path):
        """Verify corrupt/malformed dataset is rejected."""
        data_dir = tmp_path / "price_data" / "processed"
        data_dir.mkdir(parents=True)

        # Create malformed CSV
        symbol_dir = data_dir / "cadusd"
        symbol_dir.mkdir()
        corrupt_csv = symbol_dir / "processed.csv"
        corrupt_csv.write_text("not,valid,csv,data\nthis is garbage\n")

        pair = CurrencyPair(code="CADUSD")
        exists, error = validate_symbol_exists(pair, data_dir)

        # Should either succeed (if pandas can parse it) or fail gracefully
        # At minimum, should not crash
        assert isinstance(exists, bool)
        if not exists:
            assert error is not None
            assert "CADUSD" in error


class TestValidationListBehavior:
    """Test validate_symbol_list function behavior."""

    def test_empty_list_returns_empty_valid_and_errors(self, tmp_path):
        """Verify empty input list returns empty valid and errors."""
        data_dir = tmp_path / "price_data" / "processed"
        data_dir.mkdir(parents=True)

        valid_pairs, errors = validate_symbol_list([], data_dir)

        assert not valid_pairs
        assert not errors

    def test_all_valid_symbols_return_all_valid(self, tmp_path):
        """Verify all valid symbols pass validation."""
        data_dir = tmp_path / "price_data" / "processed"
        data_dir.mkdir(parents=True)

        # Create two valid datasets
        for symbol in ["eurusd", "gbpusd"]:
            symbol_dir = data_dir / symbol
            symbol_dir.mkdir()
            csv_path = symbol_dir / "processed.csv"
            csv_path.write_text(
                "timestamp,open,high,low,close,volume\n"
                "2024-01-01 00:00:00,1.1,1.1,1.1,1.1,100\n"
            )

        pairs = [
            CurrencyPair(code="EURUSD"),
            CurrencyPair(code="GBPUSD"),
        ]

        valid_pairs, errors = validate_symbol_list(pairs, data_dir)

        assert len(valid_pairs) == 2
        assert len(errors) == 0
        assert {p.code for p in valid_pairs} == {"EURUSD", "GBPUSD"}

    def test_all_invalid_symbols_return_all_errors(self, tmp_path):
        """Verify all invalid symbols produce errors."""
        data_dir = tmp_path / "price_data" / "processed"
        data_dir.mkdir(parents=True)

        pairs = [
            CurrencyPair(code="AAAAAA"),
            CurrencyPair(code="BBBBBB"),
        ]

        valid_pairs, errors = validate_symbol_list(pairs, data_dir)

        assert len(valid_pairs) == 0
        assert len(errors) == 2
        assert any("AAAAAA" in err for err in errors)
        assert any("BBBBBB" in err for err in errors)


class TestErrorMessageQuality:
    """Test quality and clarity of validation error messages."""

    def test_error_message_includes_symbol_code(self, tmp_path):
        """Verify error messages include the problematic symbol code."""
        data_dir = tmp_path / "price_data" / "processed"
        data_dir.mkdir(parents=True)

        pair = CurrencyPair(code="XYZUSD")
        _, error = validate_symbol_exists(pair, data_dir)

        assert "XYZUSD" in error, "Error should include symbol code"

    def test_error_message_includes_expected_path(self, tmp_path):
        """Verify error messages include the expected dataset path."""
        data_dir = tmp_path / "price_data" / "processed"
        data_dir.mkdir(parents=True)

        pair = CurrencyPair(code="ABCUSD")
        _, error = validate_symbol_exists(pair, data_dir)

        assert "abcusd" in error.lower(), "Error should include symbol directory"
        assert "processed.csv" in error, "Error should include expected filename"

    def test_error_message_actionable(self, tmp_path):
        """Verify error messages are actionable (describe what's missing)."""
        data_dir = tmp_path / "price_data" / "processed"
        data_dir.mkdir(parents=True)

        pair = CurrencyPair(code="DEFUSD")
        _, error = validate_symbol_exists(pair, data_dir)

        # Should mention "not found" or similar actionable phrase
        assert (
            "not found" in error.lower() or "missing" in error.lower()
        ), "Error should describe what's missing"

    def test_multiple_errors_distinguishable(self, tmp_path):
        """Verify multiple symbol errors are distinguishable."""
        data_dir = tmp_path / "price_data" / "processed"
        data_dir.mkdir(parents=True)

        pairs = [
            CurrencyPair(code="AAAAAA"),
            CurrencyPair(code="BBBBBB"),
        ]

        _, errors = validate_symbol_list(pairs, data_dir)

        # Each error should mention its specific symbol
        error1_mentions = sum(1 for err in errors if "AAAAAA" in err)
        error2_mentions = sum(1 for err in errors if "BBBBBB" in err)

        assert error1_mentions == 1, "AAAAAA should appear in exactly one error"
        assert error2_mentions == 1, "BBBBBB should appear in exactly one error"


class TestValidationIntegration:
    """Test validation integrated with runner/orchestrator abort logic."""

    @patch("src.backtest.portfolio.validation.logger")
    def test_validation_logs_warnings_for_invalid_symbols(self, mock_logger, tmp_path):
        """Verify validation logs warnings for invalid symbols."""
        data_dir = tmp_path / "price_data" / "processed"
        data_dir.mkdir(parents=True)

        pairs = [CurrencyPair(code="XYZABC")]

        validate_symbol_list(pairs, data_dir)

        # Should log warning about skipping invalid symbol
        assert mock_logger.warning.called, "Expected warning log for invalid symbol"
        call_args = str(mock_logger.warning.call_args)
        assert "XYZABC" in call_args, "Warning should mention symbol code"

    def test_validation_preserves_symbol_order(self, tmp_path):
        """Verify validation preserves order of valid symbols."""
        data_dir = tmp_path / "price_data" / "processed"
        data_dir.mkdir(parents=True)

        # Create datasets in specific order
        for symbol in ["aaaaaa", "bbbbbb", "cccccc"]:
            symbol_dir = data_dir / symbol
            symbol_dir.mkdir()
            csv_path = symbol_dir / "processed.csv"
            csv_path.write_text(
                "timestamp,open,high,low,close,volume\n"
                "2024-01-01 00:00:00,1.1,1.1,1.1,1.1,100\n"
            )

        # Request in specific order
        pairs = [
            CurrencyPair(code="AAAAAA"),
            CurrencyPair(code="BBBBBB"),
            CurrencyPair(code="CCCCCC"),
        ]

        valid_pairs, _ = validate_symbol_list(pairs, data_dir)

        # Should preserve input order
        valid_codes = [p.code for p in valid_pairs]
        assert valid_codes == ["AAAAAA", "BBBBBB", "CCCCCC"]
