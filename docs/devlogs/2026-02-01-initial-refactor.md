# Devlog: Unified CLI & CTI Restoration
**Date:** 2026-02-01  
**Author:** Dock (AI Collaborator)

## Summary
The project reached a major milestone today with the release of **v0.5.0**. This release focused on unifying the CLI experience and restoring critical prop-firm evaluation logic.

## Key Changes
- **Unified CLI**: Migrated standalone scripts (`build_dataset.py`, `scaffold_strategy.py`) into the `quantpipe` command. Users can now run `poetry run quantpipe ingest` or `scaffold` directly.
- **CTI Logic Restoration**: Re-integrated the Feature 027 evaluation logic. The system now correctly tracks "lives," promotions, and failure states for CTI 1-Step, 2-Step, and Instant challenges.
- **Improved UX**: Added interactive prompts for missing backtest flags and a concise single-line console summary for CTI evaluations to minimize terminal noise.
- **GPU Foundation**: Initiated the integration of CUDA-based acceleration via `cupy` to support large-scale dataset processing.

## Next Steps
We are moving into Issue #8 to implement deeper portfolio-level prompts and continuing to optimize the backtesting engine for high-throughput concurrent simulations.
