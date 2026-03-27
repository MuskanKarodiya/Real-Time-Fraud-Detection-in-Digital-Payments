-- Retraining Log Schema - Week 4 Day 4
--
-- This table tracks all automated retraining runs with their outcomes.
-- Reference: project_guide.md Week 4 - Automated Retraining Pipeline

-- Create retraining_log table
CREATE TABLE IF NOT EXISTS retraining_log (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(50) UNIQUE NOT NULL,
    triggered_by VARCHAR(50) NOT NULL,           -- 'drift', 'scheduled', 'manual'
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    status VARCHAR(20) NOT NULL,                 -- 'running', 'completed', 'failed', 'rejected'
    data_rows INTEGER,
    data_window_days INTEGER,

    -- Model metrics
    roc_auc FLOAT,
    precision FLOAT,
    recall FLOAT,
    f1_score FLOAT,

    -- Comparison with baseline
    baseline_roc_auc FLOAT,
    baseline_precision FLOAT,
    baseline_recall FLOAT,

    -- Validation result
    validation_passed BOOLEAN,
    promoted BOOLEAN DEFAULT FALSE,
    new_model_version VARCHAR(50),

    -- Error tracking
    error_message TEXT,

    -- Additional metadata
    metadata JSONB,

    created_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_retraining_run_id ON retraining_log(run_id);
CREATE INDEX IF NOT EXISTS idx_retraining_status ON retraining_log(status);
CREATE INDEX IF NOT EXISTS idx_retraining_triggered_by ON retraining_log(triggered_by);
CREATE INDEX IF NOT EXISTS idx_retraining_started_at ON retraining_log(started_at DESC);

-- Add comments for documentation
COMMENT ON TABLE retraining_log IS 'Tracks all automated model retraining runs';
COMMENT ON COLUMN retraining_log.run_id IS 'Unique identifier for each retraining run';
COMMENT ON COLUMN retraining_log.triggered_by IS 'What triggered the retraining: drift, scheduled, or manual';
COMMENT ON COLUMN retraining_log.status IS 'Current status: running, completed, failed, or rejected';
COMMENT ON COLUMN retraining_log.promoted IS 'Whether the new model was promoted to production';
COMMENT ON COLUMN retraining_log.validation_passed IS 'Whether the new model passed validation criteria';
