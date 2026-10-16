-- D-V11-1: v1.1 adds a second cohort of evaluation queries.
-- Existing rows become cohort 'v1.0'. v1.1 TUNE = all v1.0 rows;
-- v1.1 HOLDOUT = cohort 'v1.1' rows (split 'holdout').
ALTER TABLE eval_queries
    ADD COLUMN cohort TEXT NOT NULL DEFAULT 'v1.0'
    CHECK (cohort IN ('v1.0', 'v1.1'));
