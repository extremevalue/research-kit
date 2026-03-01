# Claude Code Context for research-kit

## Critical: This is the SOURCE REPO

This is the **research-kit source code repository** - the tool itself, not a user workspace.

### Two separate contexts exist:

1. **This repo** (`/Users/t/_repos/extremevalue/research-kit`):
   - The Python package source code
   - Where we fix bugs, implement features, write tests
   - Changes here affect the `research` CLI tool

2. **User workspaces** (e.g., `/Users/t/_repos/my-research`):
   - Instantiated by running `research init`
   - Where a *separate* Claude instance runs as a "user" testing the tool
   - Contains strategies, validations, learnings, etc.

### Rules for this session:

- **DO NOT** run `research` commands targeting user workspaces like `my-research`
- **DO** work on source code in `research_system/`, `tests/`, etc.
- **DO** run unit tests with `pytest`
- **DO** check implementation status in source files

### Current Testing Session

See `TESTING_SESSION_STATUS.md` for:
- What's been done and tested
- Bugs fixed and issues opened
- Next steps in the testing plan
- Commands to give the test Claude instance

### Pipeline Commands

The pipeline commands are:
- `ingest` - Ingest strategies from inbox (TESTED - working)
- `verify` - Verify strategy specifications (next to test)
- `validate` - Run backtests
- `learn` - Extract learnings from results
- `ideate` - Generate new strategy ideas

### Pre-Production Checklist

Before considering this production-ready:

- [ ] **Workspace migration**: Need `research migrate workspace` command to convert legacy format (`config.json` + `catalog/entries/*.json`) to V4 format (`research-kit.yaml` + `strategies/{status}/*.yaml`). Users should NOT have to blow away their workspace and start over when upgrading.

### Development workflow

```bash
# Run tests
pytest tests/

# Install in dev mode
pip install -e .

# Check a specific module
python -c "from research_system.validation import v4_runner; print(v4_runner)"
```
