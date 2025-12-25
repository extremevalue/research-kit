# Research-Kit Improvement Backlog

Tracking feedback and planned improvements.

---

## Pending Improvements

### 1. Auto-update Check
**Source:** User feedback during initial testing
**Priority:** High

When running any `research` command:
- Check if a newer version is available on GitHub
- If yes, prompt user: "New version available (v1.2.0). Update now? [y/N]"
- If user accepts, run the update automatically
- Cache the check (e.g., once per day) to avoid slowing down every command

**Implementation notes:**
- Compare local `__version__` with latest GitHub release/tag
- Use `uv tool install --force` for update
- Store last check timestamp in `~/.research-kit-version-check`

---

### 2. Clean Up Root Directory Structure
**Source:** User feedback during initial testing
**Priority:** High

**Problem:** Validation runs and other folders are being created at the workspace root, making it very messy.

**Current state:**
```
research-project/
├── FOREX-FANDANGO-IS/      # Cluttering root
├── FOREX-FANDANGO-OOS/     # Cluttering root
├── SOME-OTHER-TEST/        # Cluttering root
├── ... many more ...
├── catalog/
├── validations/
└── config.json
```

**Desired state:**
```
research-project/
├── catalog/
├── validations/
│   └── STRAT-309/          # All validation work goes here
│       ├── backtest.py
│       ├── is_results.json
│       └── oos_results.json
├── data-registry/
└── config.json
```

**Two actions needed:**
1. Update research-kit to put ALL run artifacts in `validations/<ID>/` subfolder
2. Clean up existing clutter in user's workspace (one-time migration)

---

### 3. Auto-detect Workspace from Current Directory
**Source:** User feedback during initial testing
**Priority:** High

**Problem:** User gets error "Workspace not initialized" even when standing inside their workspace directory.

**Current behavior:**
- Looks for `$RESEARCH_WORKSPACE` env var
- Falls back to `~/.research-workspace`
- Ignores current directory

**Desired behavior:**
- First check if current directory IS a workspace (has `config.json` with research-kit structure)
- Walk up parent directories looking for workspace root
- Then check `$RESEARCH_WORKSPACE`
- Finally fall back to `~/.research-workspace`

This matches how tools like `git` work - they detect you're in a repo.

---

## Completed Improvements

(None yet)

---

*Add new feedback items as they come up during testing.*
