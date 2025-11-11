# Clarification Questions: Optimize & Decouple Ingestion Process

## Question 1: Columnar Backend Enforcement

**Context**: The specification lists a need for columnar acceleration but leaves open whether it is mandatory or should gracefully fall back.

**What we need to know**: Should ingestion FAIL if the preferred columnar backend (e.g., Arrow dtype backend) is unavailable, or transparently fall back to a slower path?

**Suggested Answers**:

| Option | Answer | Implications |
|--------|--------|--------------|
| A | Mandatory: fail fast if backend unavailable | Guarantees performance but reduces portability; setup friction. |
| B | Optional fallback with warning | Wider compatibility; performance variance must be documented and benchmark dual-path. |
| C | Configurable: default fallback, allow strict mode | Flexible; slightly more configuration complexity. |
| Custom | Provide your own answer | Specify exact policy (e.g., warn + metrics logging). |

**Your choice**: B  

## Question 2: Indicator Registration Model

**Context**: Indicator enrichment currently unspecified: static list or pluggable discovery.

**What we need to know**: How should indicators be discoverable/configurable?

**Suggested Answers**:

| Option | Answer | Implications |
|--------|--------|--------------|
| A | Static curated list in code | Lowest complexity; requires code changes for additions. |
| B | Pluggable registry (manual registration API) | Moderate extensibility; simple to test; minimal reflection. |
| C | Dynamic plugin discovery (filesystem/entry points) | High extensibility; more complexity and potential security review. |
| Custom | Provide your own answer | Define hybrid (e.g., static core + optional registry). |

**Your choice**: B  

## Question 3: Stretch Performance Target

**Context**: Required ≤2:00 runtime; potential aspirational ≤90s mentioned.

**What we need to know**: Should an aspirational stretch target be formally tracked in success criteria and planning?

**Suggested Answers**:

| Option | Answer | Implications |
|--------|--------|--------------|
| A | Yes: adopt formal stretch ≤90s | Adds secondary benchmark; may increase optimization scope/time. |
| B | No: focus only on ≤2:00 requirement | Keeps scope tight; avoids premature optimization work. |
| C | Conditional: add stretch after meeting ≤2:00 in baseline PR | Phased optimization; clear gate before extra effort. |
| Custom | Provide your own answer | Specify alternative thresholds/conditions. |

**Your choice**: A  
