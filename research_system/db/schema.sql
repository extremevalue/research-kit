-- Research-Kit v2.0 Database Schema
-- SQLite database for queryable catalog data

-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

INSERT INTO schema_version (version, description) VALUES (1, 'Initial v2.0 schema');

-- Catalog entries
CREATE TABLE IF NOT EXISTS entries (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL CHECK (type IN ('STRAT', 'IDEA', 'IND', 'TOOL', 'LEARN', 'DATA', 'OBS')),
    name TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'UNTESTED' CHECK (status IN ('UNTESTED', 'VALIDATED', 'INVALIDATED', 'BLOCKED', 'ARCHIVED')),
    tier INTEGER CHECK (tier IN (1, 2, 3)),
    strategy_type TEXT,
    definition_hash TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,

    -- Lineage tracking
    parent_id TEXT REFERENCES entries(id),
    source_document TEXT,

    -- Blocking info
    blocking_reason TEXT,
    blocked_at TIMESTAMP,

    -- Archive info
    archived_reason TEXT,
    archived_at TIMESTAMP,
    canonical_id TEXT REFERENCES entries(id)  -- Points to the canonical entry if this is archived
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_entries_status ON entries(status);
CREATE INDEX IF NOT EXISTS idx_entries_type ON entries(type);
CREATE INDEX IF NOT EXISTS idx_entries_parent ON entries(parent_id);
CREATE INDEX IF NOT EXISTS idx_entries_created ON entries(created_at);

-- Strategy definitions (JSON stored separately for human readability)
-- This table stores metadata; actual JSON is in strategies/*.json files
CREATE TABLE IF NOT EXISTS strategy_files (
    entry_id TEXT PRIMARY KEY REFERENCES entries(id),
    file_path TEXT NOT NULL,
    definition_hash TEXT NOT NULL,
    last_synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Validation results
CREATE TABLE IF NOT EXISTS validations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id TEXT NOT NULL REFERENCES entries(id),
    validation_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Version tracking
    definition_hash TEXT NOT NULL,
    code_hash TEXT NOT NULL,

    -- Status
    status TEXT NOT NULL CHECK (status IN ('PASSED', 'FAILED', 'ERROR', 'BLOCKED')),
    confidence TEXT CHECK (confidence IN ('HIGH', 'MEDIUM', 'LOW')),

    -- Aggregate metrics
    mean_sharpe REAL,
    sharpe_std REAL,
    sharpe_95_ci_low REAL,
    sharpe_95_ci_high REAL,
    mean_cagr REAL,
    mean_max_drawdown REAL,
    worst_drawdown REAL,
    consistency_score REAL,
    p_value REAL,
    p_value_adjusted REAL,

    -- Full result JSON
    result_json TEXT,

    -- Notes
    notes TEXT,
    blocking_reason TEXT
);

CREATE INDEX IF NOT EXISTS idx_validations_entry ON validations(entry_id);
CREATE INDEX IF NOT EXISTS idx_validations_status ON validations(status);
CREATE INDEX IF NOT EXISTS idx_validations_sharpe ON validations(mean_sharpe);

-- Walk-forward window results
CREATE TABLE IF NOT EXISTS window_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    validation_id INTEGER NOT NULL REFERENCES validations(id),
    window_id INTEGER NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,

    -- Metrics
    cagr REAL,
    sharpe REAL,
    sortino REAL,
    max_drawdown REAL,
    win_rate REAL,
    profit_factor REAL,
    trades INTEGER,
    volatility REAL,

    -- Benchmark comparison
    benchmark_cagr REAL,
    benchmark_sharpe REAL,

    -- Regime tags
    regime_direction TEXT CHECK (regime_direction IN ('bull', 'bear', 'sideways')),
    regime_volatility TEXT CHECK (regime_volatility IN ('low', 'normal', 'high')),
    regime_rates TEXT CHECK (regime_rates IN ('rising', 'flat', 'falling')),
    regime_sector TEXT,
    regime_cap TEXT CHECK (regime_cap IN ('large', 'small', 'mixed'))
);

CREATE INDEX IF NOT EXISTS idx_window_validation ON window_results(validation_id);
CREATE INDEX IF NOT EXISTS idx_window_regime_dir ON window_results(regime_direction);
CREATE INDEX IF NOT EXISTS idx_window_regime_vol ON window_results(regime_volatility);

-- Regime performance aggregates (pre-computed for fast queries)
CREATE TABLE IF NOT EXISTS regime_performance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id TEXT NOT NULL REFERENCES entries(id),
    validation_id INTEGER NOT NULL REFERENCES validations(id),

    -- Regime dimension
    dimension TEXT NOT NULL CHECK (dimension IN ('direction', 'volatility', 'rates', 'sector', 'cap')),
    regime TEXT NOT NULL,

    -- Aggregated metrics
    mean_sharpe REAL,
    mean_cagr REAL,
    n_windows INTEGER,
    win_rate REAL
);

CREATE INDEX IF NOT EXISTS idx_regime_entry ON regime_performance(entry_id);
CREATE INDEX IF NOT EXISTS idx_regime_dimension ON regime_performance(dimension, regime);

-- Proposal queue
CREATE TABLE IF NOT EXISTS proposals (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL CHECK (type IN (
        'composite_strategy',
        'enhancement_leverage',
        'enhancement_options',
        'enhancement_futures',
        'enhancement_sizing',
        'data_acquisition',
        'new_strategy',
        'refined_hypothesis'
    )),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'deferred')),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT NOT NULL,

    title TEXT NOT NULL,
    description TEXT,

    -- Review
    reviewed_at TIMESTAMP,
    reviewed_by TEXT,
    review_notes TEXT,
    decision TEXT,

    -- Outcome
    resulting_entry_id TEXT REFERENCES entries(id),

    -- Full proposal JSON
    proposal_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_proposals_status ON proposals(status);
CREATE INDEX IF NOT EXISTS idx_proposals_type ON proposals(type);
CREATE INDEX IF NOT EXISTS idx_proposals_created ON proposals(created_at);

-- Observations from validations
CREATE TABLE IF NOT EXISTS observations (
    id TEXT PRIMARY KEY,
    source_validation_id INTEGER REFERENCES validations(id),
    source_strategy_id TEXT NOT NULL REFERENCES entries(id),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    observation_type TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    finding TEXT NOT NULL,
    implication TEXT,

    -- Full observation JSON
    observation_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_observations_strategy ON observations(source_strategy_id);
CREATE INDEX IF NOT EXISTS idx_observations_type ON observations(observation_type);

-- Tags for entries (many-to-many)
CREATE TABLE IF NOT EXISTS entry_tags (
    entry_id TEXT NOT NULL REFERENCES entries(id),
    tag TEXT NOT NULL,
    PRIMARY KEY (entry_id, tag)
);

CREATE INDEX IF NOT EXISTS idx_tags_tag ON entry_tags(tag);

-- Entry relationships (for composite strategies, enhancements, etc.)
CREATE TABLE IF NOT EXISTS entry_relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_entry_id TEXT NOT NULL REFERENCES entries(id),
    to_entry_id TEXT NOT NULL REFERENCES entries(id),
    relationship_type TEXT NOT NULL CHECK (relationship_type IN (
        'derived_from',
        'enhances',
        'combines_with',
        'references',
        'observation_of'
    )),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_relationships_from ON entry_relationships(from_entry_id);
CREATE INDEX IF NOT EXISTS idx_relationships_to ON entry_relationships(to_entry_id);
CREATE INDEX IF NOT EXISTS idx_relationships_type ON entry_relationships(relationship_type);

-- Views for common queries

-- View: All validated strategies with their best performing regime
CREATE VIEW IF NOT EXISTS validated_strategies AS
SELECT
    e.id,
    e.name,
    e.strategy_type,
    v.mean_sharpe,
    v.mean_cagr,
    v.consistency_score,
    v.p_value_adjusted,
    v.validation_timestamp
FROM entries e
JOIN validations v ON e.id = v.entry_id
WHERE e.status = 'VALIDATED'
AND v.id = (
    SELECT MAX(v2.id) FROM validations v2 WHERE v2.entry_id = e.id
);

-- View: Regime performance summary
CREATE VIEW IF NOT EXISTS regime_summary AS
SELECT
    dimension,
    regime,
    COUNT(DISTINCT entry_id) as strategy_count,
    AVG(mean_sharpe) as avg_sharpe,
    AVG(mean_cagr) as avg_cagr
FROM regime_performance
GROUP BY dimension, regime;

-- View: Pending proposals by type
CREATE VIEW IF NOT EXISTS pending_proposals AS
SELECT
    type,
    COUNT(*) as count,
    MIN(created_at) as oldest
FROM proposals
WHERE status = 'pending'
GROUP BY type;
