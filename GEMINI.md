# trading-strategies Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-11-12

## Active Technologies

- Python 3.11 + pandas, numpy, polars, pytest (011-optimize-batch-simulation)

## Project Structure

```text
src/
tests/
```

## Commands

cd src; pytest; ruff check .

## Code Style

Python 3.11: Follow standard conventions

## Recent Changes

- 023-session-blackouts: Added `src/risk/blackout/` module for news and session blackout filtering
- 011-optimize-batch-simulation: Added Python 3.11 + pandas, numpy, polars, pytest

<!-- MANUAL ADDITIONS START -->

- This project runs using poetry.
- The terminal is powershell. Do not use bash commands such as `&&`. If you want to link multiple commands, use `;` instead.
- Don't add files to the git commit until you are ready to commit and push.
- Don't run `git add <file>` after every single change. Wait until you are ready to commit and push.
<!-- MANUAL ADDITIONS END -->
