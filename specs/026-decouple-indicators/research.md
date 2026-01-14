# Research: Decouple Indicator Registration

## Research Questions

### 1. How to inject strategy-specific indicators into the calculation pipeline?

**Context**: The `calculate_indicators` function in `src/indicators/dispatcher.py` currently relies on a static `REGISTRY`. We need to pass strategy-specific definitions to it.

**Decision**: Update `calculate_indicators` to accept an optional `overrides` dictionary (already present) OR a `custom_registry` dictionary that is checked before the global registry.
_Refinement_: The existing `overrides` parameter in `calculate_indicators` serves a different purpose (parameter overrides, not function overrides). We should add a new parameter `custom_registry` or `strategy_indicators`.

**Rationale**: Explicit is better than implicit. overloading `overrides` might be confusing.
**Selected Approach**: Add `custom_registry: dict[str, Callable] | None = None` to `calculate_indicators` signature.

### 2. How to expose indicators from Strategy?

**Context**: Confirmed in Clarification Phase.
**Decision**: `get_custom_indicators(self)` instance method.
**Rationale**: Allows dynamic creation and inheritance.

## Architecture Decisions

1. **Protocol**: Strategies implement `get_custom_indicators` returning `dict[str, Callable]`.
2. **Dispatch**: `dispatcher.calculate_indicators` updated to accept `custom_registry`.
3. **Orchestrator**: `run_backtest` (or `BatchSimulation`) retrieves indicators from strategy instance and passes them into the ingestion/enrichment pipeline.

## Alternatives Considered

- **Global Registry Modification**: Strategies implicitly registering themselves on import.
  - _Rejected_: Violates side-effect free imports and isolation.
- **Decorator-based Registration**: `@register_indicator` on strategy methods.
  - _Rejected_: Harder to introspect than a simple dictionary return, less flexible for dynamic indicators.
