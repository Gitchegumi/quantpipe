"""
Test fixture file integrity and structure validation.

This module validates that all test fixtures in tests/fixtures/ conform to
expected schemas, have valid data, and match their manifest specifications.

Principle VIII: Complete docstrings for test modules.
Principle X: Black/Ruff/Pylint compliant.
"""

import csv
from pathlib import Path
from typing import Any

import pytest
import yaml


FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
MANIFEST_PATH = FIXTURES_DIR / "manifest.yaml"


def load_manifest() -> dict[str, Any]:
    """
    Load and parse the fixture manifest YAML file.

    Returns:
        Parsed manifest dictionary containing fixture metadata.

    Raises:
        FileNotFoundError: If manifest.yaml does not exist.
        yaml.YAMLError: If manifest.yaml is malformed.
    """
    if not MANIFEST_PATH.exists():
        pytest.fail(f"Manifest file not found: {MANIFEST_PATH}")

    with open(MANIFEST_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


class TestFixtureManifest:
    """Validate fixture manifest structure and completeness."""

    def test_manifest_exists(self):
        """
        Given fixtures directory,
        When checking for manifest.yaml,
        Then file should exist.
        """
        assert MANIFEST_PATH.exists(), f"Missing manifest: {MANIFEST_PATH}"

    def test_manifest_is_valid_yaml(self):
        """
        Given manifest.yaml file,
        When parsing as YAML,
        Then should parse without errors.
        """
        manifest = load_manifest()
        assert "fixtures" in manifest, "Manifest missing 'fixtures' key"
        assert isinstance(manifest["fixtures"], list), "'fixtures' must be a list"

    def test_all_manifest_fixtures_have_required_fields(self):
        """
        Given manifest fixture entries,
        When validating structure,
        Then each entry should have required fields.
        """
        manifest = load_manifest()
        required_fields = {
            "id",
            "filename",
            "scenario_type",
            "row_count",
            "seed",
            "indicators_covered",
            "created",
            "notes",
        }

        for fixture in manifest["fixtures"]:
            fixture_id = fixture.get("id", "UNKNOWN")
            missing = required_fields - set(fixture.keys())
            assert not missing, (
                f"Fixture '{fixture_id}' missing required fields: {missing}"
            )

    def test_all_manifest_files_exist(self):
        """
        Given manifest fixture entries,
        When checking filesystem,
        Then all referenced files should exist.
        """
        manifest = load_manifest()

        for fixture in manifest["fixtures"]:
            fixture_id = fixture["id"]
            filename = fixture["filename"]
            filepath = FIXTURES_DIR / filename

            assert filepath.exists(), (
                f"Fixture '{fixture_id}' references missing file: {filename}"
            )


class TestFixtureFileStructure:
    """Validate fixture CSV files have correct structure."""

    @pytest.fixture
    def manifest_fixtures(self) -> list[dict[str, Any]]:
        """Load all fixture definitions from manifest."""
        manifest = load_manifest()
        return manifest["fixtures"]

    def test_all_fixtures_are_valid_csv(self, manifest_fixtures):
        """
        Given fixture CSV files,
        When parsing as CSV,
        Then all should parse without errors.
        """
        for fixture in manifest_fixtures:
            filepath = FIXTURES_DIR / fixture["filename"]

            # Skip empty fixtures
            if fixture["row_count"] == 0:
                continue

            with open(filepath, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            assert len(rows) > 0, f"Fixture {fixture['filename']} has no data rows"

    def test_fixtures_have_required_columns(self, manifest_fixtures):
        """
        Given fixture CSV files,
        When checking headers,
        Then should have timestamp/timestamp_utc, open, high, low, close (volume optional).
        """
        required_columns_base = {"open", "high", "low", "close"}

        for fixture in manifest_fixtures:
            filepath = FIXTURES_DIR / fixture["filename"]

            # Skip empty fixtures
            if fixture["row_count"] == 0:
                continue

            with open(filepath, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                headers = set(reader.fieldnames or [])

            # Must have base columns
            missing_base = required_columns_base - headers
            assert not missing_base, (
                f"Fixture {fixture['filename']} missing columns: {missing_base}"
            )

            # Must have at least one timestamp column
            has_timestamp = (
                "timestamp" in headers or "timestamp_utc" in headers
            )
            assert has_timestamp, (
                f"Fixture {fixture['filename']} missing timestamp column "
                f"(needs 'timestamp' or 'timestamp_utc')"
            )

    def test_fixtures_row_counts_match_manifest(self, manifest_fixtures):
        """
        Given fixture files and manifest row counts,
        When comparing actual vs declared counts,
        Then should match (±1 for header tolerance).
        """
        for fixture in manifest_fixtures:
            filepath = FIXTURES_DIR / fixture["filename"]
            declared_count = fixture["row_count"]

            # Empty fixtures
            if declared_count == 0:
                with open(filepath, encoding="utf-8") as f:
                    content = f.read().strip()
                # Allow header-only or completely empty
                assert content in ("", "timestamp_utc,open,high,low,close,volume"), (
                    f"Empty fixture {fixture['filename']} should be empty or header-only"
                )
                continue

            with open(filepath, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                actual_count = len(list(reader))

            assert actual_count == declared_count, (
                f"Fixture {fixture['filename']}: "
                f"manifest says {declared_count} rows, file has {actual_count}"
            )


class TestFixtureDataValidity:
    """Validate fixture data values are correct and consistent."""

    @pytest.fixture
    def manifest_fixtures(self) -> list[dict[str, Any]]:
        """Load all fixture definitions from manifest."""
        manifest = load_manifest()
        return manifest["fixtures"]

    def test_ohlc_values_are_numeric(self, manifest_fixtures):
        """
        Given fixture OHLC columns,
        When validating data types,
        Then all values should be parseable as floats.
        """
        for fixture in manifest_fixtures:
            filepath = FIXTURES_DIR / fixture["filename"]

            # Skip empty fixtures
            if fixture["row_count"] == 0:
                continue

            with open(filepath, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for i, row in enumerate(reader, start=1):
                    for col in ["open", "high", "low", "close"]:
                        try:
                            float(row[col])
                        except (ValueError, KeyError) as e:
                            pytest.fail(
                                f"Fixture {fixture['filename']} row {i}: "
                                f"Invalid {col} value: {e}"
                            )

    def test_ohlc_relationships_are_valid(self, manifest_fixtures):
        """
        Given fixture OHLC data,
        When validating bar integrity,
        Then high >= low, high >= open, high >= close, low <= open, low <= close.
        """
        for fixture in manifest_fixtures:
            filepath = FIXTURES_DIR / fixture["filename"]

            # Skip empty fixtures
            if fixture["row_count"] == 0:
                continue

            with open(filepath, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for i, row in enumerate(reader, start=1):
                    high = float(row["high"])
                    low = float(row["low"])
                    open_price = float(row["open"])
                    close = float(row["close"])

                    # High must be highest
                    assert high >= low, (
                        f"Fixture {fixture['filename']} row {i}: high < low"
                    )
                    assert high >= open_price, (
                        f"Fixture {fixture['filename']} row {i}: high < open"
                    )
                    assert high >= close, (
                        f"Fixture {fixture['filename']} row {i}: high < close"
                    )

                    # Low must be lowest
                    assert low <= open_price, (
                        f"Fixture {fixture['filename']} row {i}: low > open"
                    )
                    assert low <= close, (
                        f"Fixture {fixture['filename']} row {i}: low > close"
                    )

    def test_volume_column_is_optional(self, manifest_fixtures):
        """
        Given fixture CSV files,
        When checking for volume column,
        Then should handle both presence and absence gracefully.
        """
        for fixture in manifest_fixtures:
            filepath = FIXTURES_DIR / fixture["filename"]

            # Skip empty fixtures
            if fixture["row_count"] == 0:
                continue

            with open(filepath, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                headers = set(reader.fieldnames or [])

            # Volume is optional, but if present should be numeric
            if "volume" in headers:
                with open(filepath, encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for i, row in enumerate(reader, start=1):
                        try:
                            float(row["volume"])
                        except ValueError as e:
                            pytest.fail(
                                f"Fixture {fixture['filename']} row {i}: "
                                f"Invalid volume value: {e}"
                            )


class TestFixtureScenarioCoverage:
    """Validate fixtures cover all required test scenarios."""

    def test_has_uptrend_fixture(self):
        """
        Given fixture manifest,
        When checking scenario types,
        Then should have at least one uptrend/trend fixture.
        """
        manifest = load_manifest()
        scenario_types = {f["scenario_type"] for f in manifest["fixtures"]}

        assert "trend" in scenario_types or "uptrend" in scenario_types, (
            "Missing uptrend/trend fixture for bullish signal testing"
        )

    def test_has_downtrend_fixture(self):
        """
        Given fixture manifest,
        When checking scenario types,
        Then should have at least one downtrend fixture.
        """
        manifest = load_manifest()
        scenario_types = {f["scenario_type"] for f in manifest["fixtures"]}

        assert "downtrend" in scenario_types, (
            "Missing downtrend fixture for bearish signal testing"
        )

    def test_has_flat_fixture(self):
        """
        Given fixture manifest,
        When checking scenario types,
        Then should have flat/low-volatility fixture.
        """
        manifest = load_manifest()
        scenario_types = {f["scenario_type"] for f in manifest["fixtures"]}

        assert "flat" in scenario_types, (
            "Missing flat fixture for false-signal prevention testing"
        )

    def test_has_spike_outlier_fixture(self):
        """
        Given fixture manifest,
        When checking scenario types,
        Then should have spike/outlier fixture for volatility testing.
        """
        manifest = load_manifest()
        scenario_types = {f["scenario_type"] for f in manifest["fixtures"]}

        assert "spike" in scenario_types, (
            "Missing spike/outlier fixture for ATR/volatility testing"
        )

    def test_has_minimum_fixtures(self):
        """
        Given fixture manifest,
        When checking total count,
        Then should have at least 5 fixtures for comprehensive testing.
        """
        manifest = load_manifest()
        assert len(manifest["fixtures"]) >= 5, (
            f"Expected at least 5 fixtures, found {len(manifest['fixtures'])}"
        )
