<!--
Sync Impact Report:
- Version change: 1.8.0 → 1.9.0
- Modified principles:
  - Principle XII (NEW) - Task Tracking & Progress Requirements
- Added sections:
  - Principle XII: Task Tracking & Progress Requirements
  - Task status markers: [ ] pending, [/] in-progress, [x] complete
  - Pre-commit requirement: tasks.md MUST be updated before any commit
  - Execution order: tasks MUST be completed in sequential order unless they are marked as `[P]` for parallel execution
- Removed sections: None
- Templates requiring updates:
  ✅ plan-template.md - Compatible (references tasks.md)
  ✅ spec-template.md - Compatible (no changes needed)
  ✅ tasks-template.md - Compatible (checkbox format already used)
  ✅ agent-file-template.md - Compatible (no changes needed)
- Follow-up TODOs: None
-->

# Trading Strategies Constitution

## Core Principles

### I. Strategy-First Architecture

Every trading algorithm MUST be implemented as an independent, self-contained strategy module.
Each strategy MUST expose standardized interfaces for backtesting, live trading, and risk management.
Clear separation required between strategy logic, data handling, and execution systems.

**Rationale**: Modularity enables independent development, testing, and deployment of trading strategies while maintaining system reliability and allowing for portfolio diversification.

### II. Risk Management Integration (NON-NEGOTIABLE)

Every strategy MUST implement mandatory risk controls: position sizing, stop-loss mechanisms, drawdown limits.
Risk parameters MUST be configurable and enforceable at both strategy and portfolio levels.
No strategy may execute trades without passing risk validation checks.

**Rationale**: Financial markets carry inherent risk; systematic risk management is essential to prevent catastrophic losses and ensure long-term viability.

### III. Backtesting & Validation

All strategies MUST undergo comprehensive backtesting on historical data before live deployment.
Backtesting MUST include realistic transaction costs, slippage, and market impact modeling.
Out-of-sample validation required using walk-forward analysis or cross-validation techniques.

#### Model Evaluation Standards

- Performance metrics MUST include accuracy, precision/recall, Sharpe ratio, and maximum drawdown.
- Statistical significance of results MUST be verified (p-value < 0.05).
- Backtest equity curves MUST be reviewed for non-stationarity and overfitting indicators.

**Rationale**: Historical performance validation helps identify strategy robustness and prevents overfitting while providing confidence estimates for live trading.

### IV. Real-Time Performance Monitoring

All active strategies MUST log execution metrics, performance statistics, and risk indicators in real-time.
Monitoring MUST include automated alerts for performance degradation, risk limit breaches, or system anomalies.
Performance data MUST be structured for analysis and strategy optimization.

#### User Experience Observability

Long-running operations (backtests, data processing, signal generation) MUST provide visual progress feedback.
Progress indicators SHOULD include running tallies of key metrics (signals generated, trades executed, win/loss ratios).
Log verbosity MUST be adjustable: INFO for summaries, DEBUG for detailed traces, with visual progress replacing repetitive logging.

**Rationale**: FOREX markets operate 24/5; continuous monitoring ensures rapid response to changing conditions and maintains system health. Clear UX feedback enables efficient development workflows and troubleshooting.

### V. Data Integrity & Security

Market data feeds MUST be validated for completeness, accuracy, and timeliness before strategy execution.
All trading credentials, API keys, and sensitive configuration MUST be encrypted and access-controlled.
Trading logs MUST maintain audit trails for regulatory compliance and performance analysis.

#### Data Continuity & Gap Handling

Time series data MUST be validated for timestamp continuity and completeness.
Gap detection MUST report missing data intervals with appropriate severity (DEBUG for informational, WARNING for critical).
Gap filling strategies (synthetic candles, forward-fill, interpolation) MAY be employed when:

- Gaps are clearly marked (e.g., `is_gap` flag) to maintain transparency
- Synthetic data does NOT corrupt technical indicators (e.g., set to NaN when appropriate)
- Gap filling behavior is configurable and documented
- Original data integrity is preserved for audit purposes

**Rationale**: Trading decisions depend on accurate data; security breaches or data corruption can result in significant financial losses. Data continuity ensures strategies process complete time series without unexpected gaps that could trigger false signals.

### VI. Data Version Control and Provenance

All historical and live market data used in research, backtesting, and production MUST be traceable, reproducible, and verifiable without requiring storage of raw data in the version control system.

_Requirements:_

**Data Manifest**:
Each dataset MUST have a manifest file stored in version control (e.g., data_manifest.yaml or .json) containing:

- Source URL or provider name
- Instrument or symbol (e.g., EURUSD, US500)
- Timeframe (e.g., 1m, 15m, 1h)
- Date range covered
- Download date
- File checksum (e.g., SHA256)
- Preprocessing summary (timezone normalization, deduplication, etc.)

**Storage Policy**:
Raw data files SHOULD be stored locally or in designated external storage (e.g., /data/raw/ or cloud bucket) and excluded from Git via .gitignore.

**Integrity Verification**:
Before use in backtesting or live models, datasets MUST pass checksum verification against the manifest entry to confirm authenticity and completeness.

**Reproducibility**:
Any backtest or analysis MUST specify the data manifest version and hash used to ensure results can be independently replicated.

**Rationale**:
Maintaining lightweight metadata rather than raw data in version control ensures full reproducibility and traceability while avoiding repository bloat or performance degradation.

### VII. Model Parsimony and Interpretability

All predictive models MUST prioritize simplicity, interpretability, and statistical soundness over raw complexity.
Feature sets MUST be justified by empirical evidence or economic rationale.
Over-parameterized models or redundant indicators are prohibited unless explicitly validated by out-of-sample performance gains.

**Rationale**: Parsimonious models generalize better, reduce computational overhead, and align with disciplined quantitative methodology.

### Principle VIII: Code Quality & Documentation Standards

Code MUST be self-documenting. Every module, class, method, and function SHALL include complete docstrings (PEP 257). Type hints MUST be used for all function signatures. Code comments MUST explain "why", not "what". Line length MUST NOT exceed 88 characters (Black standard). Variable and function names MUST be descriptive and unambiguous.

**Python 3.13 Requirements:**

- MUST follow PEP 8 style guidelines
- MUST include complete docstrings (PEP 257) for all modules, classes, methods, functions
- MUST use type hints for all signatures
- Line length ≤88 characters (Black standard)
- Variable and function names MUST be descriptive and unambiguous
- Code comments MUST explain "why", not "what"

### Principle IX: Dependency Management & Reproducibility

Python projects MUST use Poetry as the package manager. The use of `requirements.txt` is prohibited except for minimal production deployments when explicitly required. All dependencies MUST be declared in `pyproject.toml` with appropriate version constraints. Lock files (`poetry.lock`) MUST be committed to version control to ensure reproducible builds. Development dependencies MUST be separated from production dependencies.

**Poetry Requirements:**

- Package manager: Poetry (mandatory)
- Configuration: `pyproject.toml` (all dependencies declared)
- Lock file: `poetry.lock` (MUST be committed)
- No `requirements.txt` except for minimal production deployments
- Development dependencies separated from production dependencies

### Principle X: Code Quality Automation & Linting

All Python code MUST be validated using automated quality tools before merge. All Markdown documentation MUST be validated for consistency and style. The codebase SHALL maintain high code quality standards through continuous linting and formatting. Quality checks MUST pass in CI/CD pipelines.

**Required Quality Tools:**

- **Black**: Code formatter (≥23.10.0)
  - Line length: 88 characters
  - MUST format all Python files
  - Configuration in `pyproject.toml`
- **Ruff**: Fast Python linter (≥0.1.0)
  - MUST run on all Python files
  - Configuration in `pyproject.toml`
  - Zero errors required for merge
- **Pylint**: Comprehensive Python linter (≥3.3.0)
  - Minimum score: 8.0/10 for new code
  - MUST fix all W1203 (logging-fstring-interpolation) warnings
  - Score improvement encouraged but not blocking
- **Markdownlint**: Markdown linter (markdownlint-cli2)
  - MUST validate all Markdown files (\*.md)
  - Configuration in `.markdownlint.json` or `.markdownlintrc`
  - Enforces consistent formatting, heading hierarchy, and style
  - Common rules: MD032 (blanks-around-lists), MD024 (no-duplicate-heading), MD031 (blanks-around-fences)
  - Warnings are informational; critical errors MUST be fixed before merge

**Mandatory Logging Standards:**

- Logging calls MUST use lazy % formatting
- F-strings in logging calls are PROHIBITED
- Example (correct): `logger.info("Processing %d items", count)`
- Example (incorrect): `logger.info(f"Processing {count} items")`
- Rationale: Lazy evaluation prevents unnecessary string formatting when log level filters the message

**Quality Workflow:**

```bash
# Format Python code
poetry run black src/ tests/

# Lint Python with ruff
poetry run ruff check src/ tests/

# Lint Python with pylint
poetry run pylint src/ --score=yes

# Lint Markdown
markdownlint-cli2 "**/*.md" "!poetry.lock"
```

All quality checks SHOULD be automated in pre-commit hooks and CI/CD pipelines.

### Principle XI: Commit Message Standards

All Git commits MUST follow a standardized semantic format to ensure traceability, clarity, and consistent project history. Commit messages SHALL link code changes to specifications and tasks, enabling efficient navigation and change tracking.

**Required Format:**

```text
<semantic-tag>(<spec-number>): <Descriptive Title> (<Task-number>)

<summary-of-changes>
```

**Acceptable Semantic Tags:**

- `docs`: Documentation changes (README, specs, guides, comments)
- `test`: Test additions or modifications (unit, integration, performance)
- `feat`: New features or functionality
- `fix`: Bug fixes or defect corrections
- `break`: Breaking changes or backward-incompatible modifications
- `chore`: Maintenance tasks (dependencies, tooling, cleanup)

**Component Definitions:**

- `<spec-number>`: Feature specification number (e.g., `008` for `008-multi-symbol`)
- `<Descriptive Title>`: Brief summary of changes (imperative mood, ≤72 characters)
- `<Task-number>`: Task identifier from tasks.md (e.g., `T046`, `T047`)
- `<summary-of-changes>`: Detailed description with bullet points for multi-part changes

**Examples:**

```text
test(008): Add unknown symbol validation tests (T046)

- Create 15 comprehensive tests across 4 test classes
- TestUnknownSymbolValidation: Single/multiple/mixed symbol scenarios
- TestValidationListBehavior: Empty list, all valid, all invalid edge cases
- All tests passing (15/15), lint score 10.00/10
```

```text
docs(008): Add CLI filtering examples to quickstart (T047)

- Document --portfolio-mode flag (independent vs portfolio)
- Add --disable-symbol examples for runtime filtering
- Include combined filtering example using all flags
- Markdown lint: 0 errors
```

```text
feat(008): Add --portfolio-mode and multi-symbol CLI flags (T041)

- Implement --portfolio-mode enumeration (independent|portfolio)
- Add validation for portfolio mode selection
- Wire portfolio mode to orchestrator/independent_runner
- Lint score: 9.92/10
```

**Rationale**: Structured commit messages provide clear change history, facilitate code review, enable efficient navigation of project evolution, and maintain traceability between specifications, tasks, and implementation. The semantic tag system enables automated changelog generation and release management.

### Principle XII: Task Tracking & Progress Requirements

All feature implementation MUST follow the task list defined in `tasks.md`. Tasks MUST be executed in sequential order unless explicitly marked as parallelizable `[P]`. The `tasks.md` file MUST be updated before any code is committed to reflect current progress.

**Task Status Markers:**

- `- [ ]` Pending: Task not yet started
- `- [/]` In Progress: Task currently being worked on
- `- [x]` Complete: Task finished and verified

**Mandatory Workflow:**

1. Before starting a task, mark it as in-progress: `- [/] T###`
2. Complete the implementation work
3. Before committing, mark the task as complete: `- [x] T###`
4. Stage BOTH the implementation files AND the updated `tasks.md`
5. Commit using the semantic format from Principle XI

**Pre-Commit Requirements:**

- The `tasks.md` file MUST be updated to reflect completed work before any `git commit`
- Tasks MUST be completed in order unless marked `[P]` (parallelizable)
- Skipping tasks or committing out-of-order is PROHIBITED without documented justification
- Phase checkpoints in `tasks.md` MUST be verified before proceeding to next phase

**Example Workflow:**

```bash
# 1. Mark task in-progress in tasks.md: "- [/] T001 ..."
# 2. Implement the task
# 3. Mark task complete in tasks.md: "- [x] T001 ..."
# 4. Stage and commit
git add .
git commit -m "feat(013): Add DEFAULT_ACCOUNT_BALANCE constant (T001)"
```

**Rationale**: Sequential task execution with mandatory progress tracking ensures orderly implementation, prevents skipped requirements, maintains clear project history, and enables accurate progress reporting. The pre-commit checkpoint prevents orphaned or undocumented changes.

## Risk Management Standards

All trading strategies MUST comply with the following risk management requirements:

- **Position Limits**: Maximum position size per currency pair and total portfolio exposure limits
- **Drawdown Controls**: Maximum daily, weekly, and monthly drawdown thresholds with automatic shutdown
- **Volatility Adjustment**: Position sizing MUST adjust based on current market volatility conditions
- **Correlation Monitoring**: Portfolio-level correlation limits to prevent over-concentration risk
- **Emergency Procedures**: Automated kill switches and manual override capabilities for crisis scenarios

## Development Workflow

Strategy development follows a structured pipeline:

1. **Research Phase**: Market analysis, signal identification, and preliminary testing
   - Research deliverables MUST include hypothesis documentation, parameter rationale, and expected risk/return profile.
   - Artifacts MUST be stored in /research/ and linked to GitHub Spec Kit issues for traceability.
2. **Implementation Phase**: Code development following strategy-first architecture principles
3. **Validation Phase**: Comprehensive backtesting and risk assessment
4. **Staging Phase**: Paper trading and real-time validation without capital risk
5. **Production Phase**: Live deployment with continuous monitoring and performance tracking

All phases MUST include peer review and compliance verification before progression.

## Governance

This constitution supersedes all other development practices and trading procedures.
All code reviews MUST verify compliance with risk management and architectural principles.
Strategy performance MUST be regularly reviewed against constitutional requirements.

Versioning Policy:

- Patch (x.y.z): minor text or clarity updates
- Minor (x.y.0): procedural or workflow changes
- Major (x.0.0): structural or principle revisions

Amendments require:

- Technical impact assessment and migration plan
- Risk committee approval for changes affecting trading or risk management
- Documentation updates across all affected systems and procedures

**Version:** 1.9.0
**Ratified:** October 25, 2025
**Last Amended:** December 19, 2025
