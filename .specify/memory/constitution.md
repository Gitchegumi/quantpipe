<!--
Sync Impact Report:
- Version change: 1.2.0 → 1.3.0
- Modified principles: None
- Added sections: Principle IX - Dependency Management & Reproducibility
- Removed sections: None
- Templates requiring updates:
  ✅ plan-template.md - Compatible (references dependencies generically)
  ✅ tasks-template.md - Will reference Poetry in setup tasks
  ✅ spec-template.md - Compatible (no changes needed)
  ✅ agent-file-template.md - Already updated in v1.2.0
- Follow-up TODOs: Update any existing pyproject.toml/requirements.txt references in task templates
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

*Requirements:*

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

### VIII. Code Quality & Documentation Standards

All Python code MUST comply with PEP 8 style guidelines without exception.
Every module, class, method, and function MUST include complete docstrings following PEP 257 conventions.
Docstrings MUST document parameters, return values, exceptions raised, and provide usage examples for public APIs.

*Requirements:*

**Module-level docstrings**:
MUST appear at the top of every Python file, describing the module's purpose, key components, and any important usage notes.

**Class docstrings**:
MUST describe the class purpose, key attributes, and typical usage patterns. Include examples for complex classes.

**Function/method docstrings**:
MUST use the following format:

- Brief one-line summary
- Extended description (if needed)
- Args section listing each parameter with type and description
- Returns section describing return value and type
- Raises section documenting exceptions that may be raised
- Examples section for public APIs or complex functionality

**Type hints**:
MUST be provided for all function signatures, method parameters, and return values. Use `typing` module constructs where appropriate.

**Code formatting**:
MUST use consistent indentation (4 spaces), line length ≤88 characters (Black formatter standard), and proper whitespace per PEP 8.

**Rationale**: Comprehensive documentation ensures code maintainability, enables effective collaboration, facilitates onboarding, and aligns with professional Python development standards. Type hints combined with docstrings provide both human and machine-readable contracts.

### IX. Dependency Management & Reproducibility

All Python projects MUST use Poetry for dependency management and packaging.
The use of requirements.txt files is prohibited for dependency specification.
All dependencies MUST be declared in pyproject.toml with appropriate version constraints.

*Requirements:*

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

**Version**: 1.3.0 | **Ratified**: 2025-10-25 | **Last Amended**: 2025-10-28
