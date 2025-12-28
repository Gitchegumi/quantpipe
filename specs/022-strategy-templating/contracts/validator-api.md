# Strategy Validator API Contract

**Feature**: 022-strategy-templating
**Date**: 2025-12-26

## Functions

### validate_strategy

Validates a strategy class or instance against the Strategy Protocol contract.

**Signature**:

```python
def validate_strategy(
    strategy: type | object,
    strict: bool = True
) -> ValidationResult:
    """
    Validate a strategy against the Strategy Protocol contract.

    Args:
        strategy: Strategy class or instance to validate
        strict: If True, raises StrategyValidationError on failure
                If False, returns ValidationResult with errors

    Returns:
        ValidationResult with is_valid, errors, and suggestions

    Raises:
        StrategyValidationError: If strict=True and validation fails
    """
```

**Validation Checks**:

1. Has `metadata` property → `StrategyMetadata`
2. Has `generate_signals(candles: list, parameters: dict) -> list` method
3. `metadata.name` is non-empty string
4. `metadata.version` is non-empty string
5. `metadata.required_indicators` is non-empty list

**Example Response (Invalid)**:

```python
ValidationResult(
    is_valid=False,
    errors=[
        "Missing required method: generate_signals",
        "metadata.required_indicators is empty"
    ],
    strategy_name="unknown",
    checked_methods=["metadata", "generate_signals"],
    suggestions=[
        "Add method: def generate_signals(self, candles: list, parameters: dict) -> list:",
        "Add at least one indicator to required_indicators"
    ]
)
```

---

## Scaffold Generator API Contract

### generate_strategy

Generates strategy files from template.

**Signature**:

```python
def generate_strategy(
    name: str,
    output_dir: Path | None = None,
    indicators: list[str] | None = None,
    author: str = "",
    description: str = ""
) -> ScaffoldResult:
    """
    Generate strategy boilerplate from template.

    Args:
        name: Strategy name (valid Python identifier)
        output_dir: Target directory (default: src/strategy/<name>/)
        indicators: Initial required indicators
        author: Optional author name
        description: Optional strategy description

    Returns:
        ScaffoldResult with created_files and success status

    Raises:
        ValueError: If name is not a valid Python identifier
        FileExistsError: If output_dir already exists
    """
```

**Generated Files**:

```text
<output_dir>/
├── __init__.py         # Module exports
├── strategy.py         # Strategy class with TODO markers
└── signal_generator.py # Signal generation helpers
```

---

## CLI Commands

### scaffold_strategy

**Command**:

```bash
poetry run python -m src.cli.scaffold_strategy <name> [options]
```

**Arguments**:

| Argument | Type   | Required | Description                             |
| -------- | ------ | -------- | --------------------------------------- |
| name     | string | Yes      | Strategy name (valid Python identifier) |

**Options**:

| Option       | Type   | Default              | Description                     |
| ------------ | ------ | -------------------- | ------------------------------- |
| --output     | path   | src/strategy/<name>/ | Output directory                |
| --indicators | list   | []                   | Comma-separated indicator names |
| --author     | string | ""                   | Author name for template        |

**Exit Codes**:

| Exit Code | Description              |
| --------- | ------------------------ |
| 0         | Success                  |
| 1         | Invalid strategy name    |
| 2         | Directory already exists |
| 3         | Template rendering error |
