-- Migration 0001 — initial schema.
-- Run order: apply this, then policies.sql (Phase 8) once auth is enabled.
-- This migration simply sources the canonical schema; keep future changes as
-- new numbered migrations rather than editing this file.

\i schema.sql
