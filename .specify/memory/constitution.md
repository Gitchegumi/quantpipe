<!--
Sync Impact Report:
- Version change: 1.4.0 → 1.5.0
- Modified principles: Principle X - Code Quality Automation & Linting (added markdownlint requirement)
- Added sections: Markdownlint quality tool in Principle X
- Removed sections: None
- Templates requiring updates:
  ✅ plan-template.md - Compatible (already references code quality)
  ✅ tasks-template.md - Should include markdownlint validation tasks
  ✅ spec-template.md - Compatible (no changes needed)
  ✅ agent-file-template.md - Already updated in v1.2.0
- Follow-up TODOs: 
  - Ensure all Markdown files pass markdownlint validation
  - Configure markdownlint rules in .markdownlint.json or .markdownlintrc
  - Add markdownlint to quality workflow
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

**Rationale**: FOREX markets operate 24/5; continuous monitoring ensures rapid response to changing conditions and maintains system health.

### V. Data Integrity & Security

Market data feeds MUST be validated for completeness, accuracy, and timeliness before strategy execution.
All trading credentials, API keys, and sensitive configuration MUST be encrypted and access-controlled.
Trading logs MUST maintain audit trails for regulatory compliance and performance analysis.

**Rationale**: Trading decisions depend on accurate data; security breaches or data corruption can result in significant financial losses.

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

**Python 3.11 Requirements:**

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
  - MUST validate all Markdown files (*.md)
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

### IX. Dependency Management & Reproducibility

All Python projects MUST use Poetry for dependency management and packaging.
The use of requirements.txt files is prohibited for dependency specification.
All dependencies MUST be declared in pyproject.toml with appropriate version constraints.

_Requirements:_

**Poetry Configuration**:
Every Python project MUST contain a pyproject.toml file managed by Poetry, including:

- Project metadata (name, version, description, authors)
- Python version constraint
- Runtime dependencies with semantic versioning constraints
- Development dependencies (testing, linting, formatting tools)
- Build system configuration

**Dependency Lock File**:
The poetry.lock file MUST be committed to version control to ensure deterministic builds and reproducible environments across all development and production systems.

**Virtual Environment Management**:
Poetry MUST be used to create and manage project-specific virtual environments. Manual venv creation or system-wide package installation is prohibited.

**Dependency Updates**:
Dependency version updates MUST be performed using `poetry update` with review of changes in poetry.lock before committing.

**Installation Commands**:
Development setup MUST use `poetry install` to create reproducible environments. Production deployment MUST use `poetry install --only main` to exclude development dependencies.

**Rationale**: Poetry provides deterministic dependency resolution, lock file management, and integrated virtual environment handling, ensuring reproducible builds and eliminating dependency conflicts. This standardization simplifies onboarding, reduces environment-related issues, and aligns with modern Python packaging best practices.

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

### Milestone Commit Messages

After completing any development milestone (feature implementation, code quality improvements, constitution amendments, etc.), a concise commit message MUST be provided that summarizes all changes made during that milestone.

**Commit Message Requirements:**

- Use conventional commit format: `type(scope): brief description`
- Include key metrics or file counts when relevant (e.g., "16 files", "score improved 8.78→9.68")
- List major changes as bullet points in the commit body
- Cover all significant modifications in a single coherent message
- Keep descriptions concise but informative
- Combine related changes into one commit when appropriate

**Example:**

```md
feat(quality): enforce lazy logging and add constitution Principle X

- Fix 62 logging calls: f-strings → lazy % formatting (16 files)
- Eliminate W1203 warnings, improve pylint 8.78→9.68/10
- Constitution v1.4.0: formalize Black/Ruff/Pylint requirements
- Mandate lazy % logging, prohibit f-strings in logging calls
- Update copilot-instructions.md with quality standards
```

**Rationale**: Structured commit messages provide clear change history, facilitate code review, and enable efficient navigation of project evolution. Milestone-based commits ensure related changes are grouped logically rather than scattered across multiple small commits.

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

**Version:** 1.5.0
**Ratified:** October 25, 2025
**Last Amended:** October 30, 2025
