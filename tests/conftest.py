"""Pytest configuration and fixtures."""

import json
import pytest
import tempfile
from pathlib import Path


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_workspace(temp_dir):
    """Create a temporary workspace for testing."""
    from research_system.core.workspace import Workspace

    ws = Workspace(temp_dir)
    ws.init(name="Test Workspace")
    return ws


@pytest.fixture
def sample_catalog_entry():
    """Sample catalog entry for testing."""
    return {
        "id": "IND-001",
        "name": "Test Indicator",
        "type": "indicator",
        "status": "UNTESTED",
        "created_at": "2025-01-01T00:00:00Z",
        "source": {
            "files": ["archive/test.py"],
            "ingested_at": "2025-01-01T00:00:00Z"
        },
        "summary": "A test indicator for unit testing",
        "tags": ["test", "indicator"]
    }


@pytest.fixture
def sample_hypothesis():
    """Sample hypothesis for testing."""
    return {
        "component_id": "IND-001",
        "statement": "This indicator predicts market direction with statistically significant accuracy above random chance",
        "falsifiable_test": "Alpha > 1% with p < 0.01 over IS period",
        "data_requirements": ["spy_prices"],
        "created_at": "2025-01-01T00:00:00Z",
        "is_period": {
            "start": "2005-01-01",
            "end": "2019-12-31"
        },
        "oos_period": {
            "start": "2020-01-01",
            "end": "2024-12-31"
        },
        "success_criteria": {
            "min_alpha": 0.01,
            "min_sharpe_improvement": 0.10,
            "max_drawdown": -0.25,
            "min_signals": 100
        },
        "parameters": {
            "lookback": 20,
            "threshold": 0.5
        }
    }


@pytest.fixture
def sample_backtest_results():
    """Sample backtest results for testing."""
    return {
        "sharpe_ratio": 0.85,
        "alpha": 0.025,
        "cagr": 0.12,
        "max_drawdown": -0.18,
        "win_rate": 0.58,
        "total_trades": 150,
        "total_days": 252 * 15,
        "start_date": "2005-01-01",
        "end_date": "2019-12-31"
    }


@pytest.fixture
def sample_data_source():
    """Sample data source for testing."""
    return {
        "id": "spy_prices",
        "name": "SPY Daily Prices",
        "data_type": "price_data",
        "description": "Daily OHLCV data for SPY ETF",
        "availability": {
            "qc_native": {
                "available": True,
                "key": "Equity/USA/spy"
            }
        },
        "coverage": {
            "start": "1993-01-29",
            "end": "present"
        }
    }
