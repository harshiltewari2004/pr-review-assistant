-- 002: judgments.self_authored, per 02 §7 and D-P5-1.
-- 001_init.sql predates the column; D-P5-1 (2026-07-28) added it to the spec.
ALTER TABLE judgments
    ADD COLUMN IF NOT EXISTS self_authored BOOLEAN NOT NULL DEFAULT FALSE;