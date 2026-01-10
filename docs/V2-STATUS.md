# V2 Development Status

**Last Updated:** 2026-01-10
**Status:** Phase 2 Complete

## Overview

The v2 system is a complete rebuild of the research validation framework with:
- Proper Pydantic schemas with validation
- SQLite-based catalog management
- Template-driven code generation for QuantConnect
- Walk-forward validation support
- No hardcoded dates in generated code

## Architecture

```
research_system/
├── schemas/           # Pydantic data models (Phase 1 - COMPLETE)
│   ├── common.py      # Shared enums (SignalType, UniverseType, etc.)
│   ├── strategy.py    # StrategyDefinition with hash computation
│   ├── validation.py  # Walk-forward validation results
│   ├── regime.py      # Market regime analysis
│   └── proposal.py    # Multi-strategy proposals
│
├── db/                # Data layer (Phase 1 - COMPLETE)
│   ├── connection.py  # SQLite connection management
│   └── catalog_manager.py  # CRUD for strategies with FTS5 search
│
└── codegen/           # Code generation (Phase 2 - COMPLETE)
    ├── engine.py      # Jinja2 template engine
    ├── generator.py   # CodeGenerator with catalog integration
    ├── cli.py         # Typer CLI (research-codegen)
    ├── filters.py     # Custom Jinja2 filters
    └── templates/     # Strategy templates
        ├── base.j2                  # Base QCAlgorithm structure
        ├── momentum_rotation.j2     # Relative momentum
        ├── mean_reversion.j2        # Z-score mean reversion
        ├── trend_following.j2       # MA crossover
        ├── dual_momentum.j2         # Absolute + relative
        └── breakout.j2              # Channel breakout
```

## Completed Work

### Phase 1: Schemas & Data Layer (Issues #73-#81)
- [x] #73 - Strategy schema with Pydantic
- [x] #74 - Validation result schema
- [x] #75 - SQLite catalog with FTS5 search
- [x] #76 - Golden tests for schema stability
- [x] #77-#81 - Additional schema improvements

### Phase 2: Code Generation (Issues #82-#85)
- [x] #82 - Template structure (5 strategy types)
- [x] #83 - Template engine with validation
- [x] #84 - Code generator CLI with catalog integration
- [x] #85 - Golden tests for code generation

## Test Coverage

```
219 tests passing
92.50% coverage (90% minimum required)

Coverage by module:
- schemas/         100%
- db/              93-97%
- codegen/         68-100%
```

## CLI Commands

### Code Generation CLI

```bash
# Generate code from catalog entry
research-codegen generate STRAT-001 --output ./output/strategy.py

# Validate generated code
research-codegen validate STRAT-001

# Generate demo code (no catalog needed)
research-codegen demo momentum_rotation
research-codegen demo mean_reversion
research-codegen demo trend_following
research-codegen demo dual_momentum
research-codegen demo breakout

# List available templates
research-codegen list-templates
```

### Key Features

1. **No Hardcoded Dates**: All generated code excludes SetStartDate/SetEndDate - dates are controlled by the walk-forward framework

2. **Deterministic Output**: Same strategy definition always produces identical code

3. **Validation Checks**:
   - Valid Python syntax
   - No hardcoded dates (regex validation)
   - Required imports present
   - Proper class structure
   - Warmup period set

## Strategy Definition Schema

```python
StrategyDefinition(
    tier=1,  # 1-3, complexity level
    metadata=StrategyMetadata(
        id="STRAT-001",
        name="My Strategy",
        description="...",
        tags=["momentum", "rotation"],
    ),
    strategy_type="momentum_rotation",  # Template selection
    universe=UniverseConfig(
        type=UniverseType.FIXED,
        symbols=["SPY", "TLT", "GLD"],
        defensive_symbols=["SHY"],
    ),
    signal=SignalConfig(
        type=SignalType.RELATIVE_MOMENTUM,
        lookback_days=126,
        selection_n=2,
    ),
    position_sizing=PositionSizingConfig(
        method=PositionSizingMethod.EQUAL_WEIGHT,
        leverage=1.0,
    ),
    rebalance=RebalanceConfig(
        frequency=RebalanceFrequency.MONTHLY,
    ),
)
```

## Remaining Work

### Pending (Require User Action)
- [ ] #70 - Create GitHub project board
- [ ] #72 - Configure branch protection rules

### Future Phases (Not Started)
- Phase 3: Walk-forward validation framework
- Phase 4: Regime analysis integration
- Phase 5: V1 to V2 migration tools

## File Locations

| Component | Location |
|-----------|----------|
| Schemas | `research_system/schemas/` |
| Database | `research_system/db/` |
| Code Generation | `research_system/codegen/` |
| Templates | `research_system/codegen/templates/` |
| Tests | `tests_v2/` |
| Golden Files | `tests_v2/fixtures/golden/` |

## Development Setup

```bash
# Clone and install
git clone https://github.com/extremevalue/research-kit.git
cd research-kit
pip install -e ".[dev]"

# Run tests
pytest tests_v2/ -v

# Run with coverage
pytest tests_v2/ --cov=research_system.schemas --cov=research_system.db --cov=research_system.codegen

# Type checking
mypy research_system/schemas research_system/db research_system/codegen

# Linting
ruff check .
ruff format .
```

## CI/CD

GitHub Actions workflow runs on every PR:
- Tests on Python 3.10, 3.11, 3.12
- Ruff linting and formatting
- Mypy type checking
- 90% coverage requirement

## Notes for Resuming Work

1. **All Phase 2 PRs merged**: #86, #87, #88, #89
2. **Main branch is up to date**: Pull before starting new work
3. **Golden files exist**: Located in `tests_v2/fixtures/golden/codegen/`
4. **V1 code is excluded from linting**: See `pyproject.toml` exclude list

## Quick Reference

```bash
# Check current issues
gh issue list --repo extremevalue/research-kit

# View a specific issue
gh issue view 85

# Run the codegen demo
cd /path/to/research-kit
.venv/bin/research-codegen demo momentum_rotation
```
