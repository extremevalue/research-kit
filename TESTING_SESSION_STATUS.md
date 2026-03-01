# Testing Session Status - 2026-01-27

## What We've Done

### Bugs Fixed (all merged to main)
1. **#166** - Added missing `scripts.status`, `scripts.develop`, `scripts.ingest` packages to pyproject.toml
2. **#168** - Fixed `--workspace` flag not being honored by V4 commands
3. **#169** - Added common LLM data requirement variations to QC_NATIVE_SPECIAL (options_chains, moving_averages, etc.)
4. **Version sync** - Fixed `__version__` in `research_system/__init__.py` (was 0.1.0, now 4.0.0)

### Issues Opened (for later)
- **#170** - `research catalog recheck` command to re-evaluate blocked entries
- **#171** - Detect and warn about multiple research-kit installations

### Testing Progress

**Ingest command: WORKING**
- Tested with 25 source files from `~/test-strategies/`
- Results after all fixes:
  - 21 accepted → `strategies/pending/`
  - 3 archived (too vague, specificity < 4)
  - 1 rejected (hard red flag: "no_losing_periods")
  - **0 BLOCKED** - QC-native pattern matching now works correctly

## Where We Are

Successfully completed **ingest** phase of the V4 pipeline. Ready to test the next phase.

## Next Steps

Test the remaining V4 pipeline commands in order:

1. **`research verify STRAT-XXX`** - Verify strategy specifications
   - Pick one of the 21 pending strategies
   - Check if verification passes

2. **`research validate STRAT-XXX`** - Run walk-forward validation (backtesting)
   - This may require backtest results or generate config

3. **`research learn STRAT-XXX`** - Extract learnings from results

4. **`research ideate`** - Generate new strategy ideas

## Test Workspace

- Location: `~/_repos/my-research/`
- Source files: `~/test-strategies/` (copy back to inbox if needed to re-test)
- 21 strategies in `strategies/pending/` ready for verification

## Commands for Other Claude Instance

To continue testing, tell the other Claude:

```
research catalog list
```

Then pick a strategy and run:

```
research verify STRAT-001
```

## Notes

- The other Claude instance should use `research` from `~/.local/bin/research` (symlinked to Python 3.14 installation)
- Version should show `research 4.0.0`
- If issues occur, can reinstall with: `pip install --user --upgrade --force-reinstall git+https://github.com/extremevalue/research-kit.git`
