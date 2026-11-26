-- Migration: 002_reporting_schema.sql
-- Description: Create dedicated 'reporting' schema, weekly performance aggregates table,
-- and pipeline execution logs table for Nexova business stakeholders (Laura & Elena).
-- Source design specification: data/pipelines/PIPELINE_DESIGN.md

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Dedicated schema for analytical reporting, isolated from telemetry_events
CREATE SCHEMA IF NOT EXISTS reporting;

-- 1. Weekly Office & Programme Performance Table
CREATE TABLE IF NOT EXISTS reporting.weekly_office_program_performance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    office VARCHAR(20) NOT NULL,
    programme_id VARCHAR(100) NOT NULL,
    week_start DATE NOT NULL,
    total_material_cost NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    kits_delivered_count INTEGER NOT NULL DEFAULT 0,
    shortage_events_count INTEGER NOT NULL DEFAULT 0,
    cost_variance_events_count INTEGER NOT NULL DEFAULT 0,
    currency VARCHAR(3) NOT NULL,
    computed_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    run_id UUID NOT NULL,

    -- Domain & Consistency Constraints
    CONSTRAINT chk_office CHECK (office IN ('valencia', 'miami')),
    CONSTRAINT chk_currency CHECK (
        (office = 'valencia' AND currency = 'EUR') OR
        (office = 'miami' AND currency = 'USD')
    ),
    CONSTRAINT chk_non_negative_cost CHECK (total_material_cost >= 0),
    CONSTRAINT chk_non_negative_counts CHECK (
        kits_delivered_count >= 0 AND
        shortage_events_count >= 0 AND
        cost_variance_events_count >= 0
    ),

    -- Natural Unique Key Guarantee (Grano)
    CONSTRAINT uq_weekly_office_programme UNIQUE (office, programme_id, week_start)
);

-- Analytical indexes
CREATE INDEX IF NOT EXISTS idx_weekly_perf_query 
    ON reporting.weekly_office_program_performance (week_start DESC, office, programme_id);

CREATE INDEX IF NOT EXISTS idx_weekly_perf_run 
    ON reporting.weekly_office_program_performance (run_id);

-- Documentation comments
COMMENT ON SCHEMA reporting IS 'Dedicated analytical reporting schema for Nexova business KPIs.';
COMMENT ON TABLE reporting.weekly_office_program_performance IS 'Weekly consolidated business performance KPIs by office and training programme.';
COMMENT ON COLUMN reporting.weekly_office_program_performance.office IS 'Operational office location (valencia or miami).';
COMMENT ON COLUMN reporting.weekly_office_program_performance.programme_id IS 'Training programme identifier (e.g. ai-engineering-core).';
COMMENT ON COLUMN reporting.weekly_office_program_performance.week_start IS 'ISO calendar week start date (Monday at 00:00:00 UTC).';
COMMENT ON COLUMN reporting.weekly_office_program_performance.total_material_cost IS 'Sum of inbound material costs in local currency.';
COMMENT ON COLUMN reporting.weekly_office_program_performance.kits_delivered_count IS 'Count of outbound kits delivered to participants.';
COMMENT ON COLUMN reporting.weekly_office_program_performance.shortage_events_count IS 'Count of stock shortages below minimum safety threshold.';
COMMENT ON COLUMN reporting.weekly_office_program_performance.cost_variance_events_count IS 'Count of anomalous kit cost variance alerts.';
COMMENT ON COLUMN reporting.weekly_office_program_performance.currency IS 'Local operating currency: EUR for Valencia, USD for Miami.';
COMMENT ON COLUMN reporting.weekly_office_program_performance.computed_at IS 'Precise timestamp of calculation.';
COMMENT ON COLUMN reporting.weekly_office_program_performance.run_id IS 'Prefect pipeline execution run identifier.';


-- 2. Pipeline Execution Logs Table (Audit & Observability)
CREATE TABLE IF NOT EXISTS reporting.pipeline_execution_logs (
    run_id UUID PRIMARY KEY,
    flow_name VARCHAR(100) NOT NULL,
    trigger_mode VARCHAR(20) NOT NULL,
    window_start DATE NOT NULL,
    window_end DATE NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ,
    status VARCHAR(20) NOT NULL,
    checkpoint_phase VARCHAR(50) NOT NULL,
    records_extracted INTEGER NOT NULL DEFAULT 0,
    records_loaded INTEGER NOT NULL DEFAULT 0,
    error_details TEXT,
    execution_context JSONB NOT NULL DEFAULT '{}'::jsonb,

    CONSTRAINT chk_log_status CHECK (
        status IN ('RUNNING', 'COMPLETED', 'FAILED', 'SKIPPED', 'ABORTED')
    ),
    CONSTRAINT chk_log_trigger CHECK (
        trigger_mode IN ('scheduled', 'manual', 'backfill', 'late_event_recalc')
    )
);

CREATE INDEX IF NOT EXISTS idx_pipeline_logs_status_window 
    ON reporting.pipeline_execution_logs (window_start DESC, started_at DESC);

COMMENT ON TABLE reporting.pipeline_execution_logs IS 'Audit log tracking every Prefect ETL pipeline execution run.';
COMMENT ON COLUMN reporting.pipeline_execution_logs.run_id IS 'Globally unique execution identifier.';
COMMENT ON COLUMN reporting.pipeline_execution_logs.flow_name IS 'Name of the Prefect flow (weekly_business_performance_pipeline).';
COMMENT ON COLUMN reporting.pipeline_execution_logs.trigger_mode IS 'Trigger source: scheduled, manual, backfill, or late_event_recalc.';
COMMENT ON COLUMN reporting.pipeline_execution_logs.checkpoint_phase IS 'Last technical checkpoint phase reached (INIT, EXTRACTION, TRANSFORMATION, LOADING, FINALIZED).';
