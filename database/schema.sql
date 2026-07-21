-- =====================================================================
-- Valuation Platform — PostgreSQL schema (Supabase). See §25.
-- Historical valuation runs are permanent and never overwritten.
-- Apply via database/migrations/ in order, or run this file directly.
-- =====================================================================

create table if not exists companies (
    id              bigint generated always as identity primary key,
    ticker          text not null unique,
    name            text not null,
    cik             text,
    sector          text,
    industry        text,
    fiscal_year_end text,
    currency        text default 'USD',
    lifecycle       text,
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now()
);

create table if not exists filings (
    id                bigint generated always as identity primary key,
    company_id        bigint references companies(id) on delete cascade,
    accession_number  text not null,
    form_type         text not null,
    filing_date       date,
    report_date       date,
    primary_document  text,
    source_url        text,
    processing_status text default 'pending',
    unique (company_id, accession_number)
);

create table if not exists financial_facts (
    id               bigint generated always as identity primary key,
    company_id       bigint references companies(id) on delete cascade,
    filing_id        bigint references filings(id) on delete set null,
    metric           text not null,
    reported_label   text,
    value            double precision,
    unit             text default 'USD',
    currency         text default 'USD',
    period_start     date,
    period_end       date,
    fiscal_year      int,
    fiscal_period    text,
    segment          text,
    geography        text,
    xbrl_tag         text,
    xbrl_dimensions  jsonb,
    data_status      text not null default 'reported',
    confidence       text not null default 'high',
    source_url       text,
    collected_at     timestamptz default now()
);
create index if not exists idx_facts_company_metric
    on financial_facts (company_id, metric, fiscal_year, fiscal_period);

create table if not exists metric_aliases (
    id                     bigint generated always as identity primary key,
    company_id             bigint references companies(id) on delete cascade,
    raw_metric_name        text not null,
    standardized_metric_name text not null,
    alias_type             text,
    approval_status        text default 'pending',
    approved_by            text
);

create table if not exists segments (
    id                bigint generated always as identity primary key,
    company_id        bigint references companies(id) on delete cascade,
    segment_name      text not null,
    standardized_segment_name text,
    segment_type      text,
    effective_start   date,
    effective_end     date,
    analyst_approved  boolean default false
);

create table if not exists peer_sets (
    id             bigint generated always as identity primary key,
    company_id     bigint references companies(id) on delete cascade,
    name           text not null,
    description    text,
    effective_date date,
    created_by     text
);

create table if not exists peer_set_members (
    id               bigint generated always as identity primary key,
    peer_set_id      bigint references peer_sets(id) on delete cascade,
    peer_ticker      text not null,
    inclusion_reason text,
    analyst_approved boolean default false
);

create table if not exists assumption_sets (
    id              bigint generated always as identity primary key,
    company_id      bigint references companies(id) on delete cascade,
    name            text not null,
    scenario        text,
    model_version   text,
    assumptions     jsonb not null,
    created_by      text,
    approved_by     text,
    approval_status text default 'draft',
    created_at      timestamptz not null default now()
);

create table if not exists valuation_runs (
    id                bigint generated always as identity primary key,
    company_id        bigint references companies(id) on delete cascade,
    ticker            text not null,
    valuation_date    date not null,
    current_price     double precision,
    company_lifecycle text,
    assumption_set_id bigint references assumption_sets(id) on delete set null,
    bear_value        double precision,
    base_value        double precision,
    bull_value        double precision,
    blended_value     double precision,
    confidence        text,
    model_version     text,
    created_by        text,
    approval_status   text default 'draft',
    run_payload       jsonb,
    created_at        timestamptz not null default now()
);

create table if not exists method_results (
    id                bigint generated always as identity primary key,
    valuation_run_id  bigint references valuation_runs(id) on delete cascade,
    method            text not null,
    equity_value      double precision,
    per_share_value   double precision,
    raw_weight        double precision,
    confidence        text,
    normalized_weight double precision,
    assumptions       jsonb,
    results           jsonb
);

create table if not exists guidance_points (
    id              bigint generated always as identity primary key,
    company_id      bigint references companies(id) on delete cascade,
    metric          text not null,
    guidance_period text,
    low_value       double precision,
    high_value      double precision,
    midpoint        double precision,
    unit            text,
    guidance_date   date,
    source_url      text,
    data_status     text default 'reported',
    confidence      text default 'medium'
);

create table if not exists ai_analyses (
    id               bigint generated always as identity primary key,
    company_id       bigint references companies(id) on delete cascade,
    valuation_run_id bigint references valuation_runs(id) on delete set null,
    analysis_type    text,
    provider         text,
    model            text,
    prompt_version   text,
    input_sources    jsonb,
    output           jsonb,
    analyst_approved boolean default false,
    created_at       timestamptz not null default now()
);

create table if not exists manual_overrides (
    id          bigint generated always as identity primary key,
    company_id  bigint references companies(id) on delete cascade,
    table_name  text not null,
    record_id   bigint,
    field       text not null,
    old_value   text,
    new_value   text,
    reason      text,
    created_by  text,
    created_at  timestamptz not null default now()
);

create table if not exists valuation_outcomes (
    id               bigint generated always as identity primary key,
    valuation_run_id bigint references valuation_runs(id) on delete cascade,
    horizon          text,             -- '3m' | '6m' | '12m'
    observed_date    date,
    observed_price   double precision,
    total_return     double precision,
    forecast_error   double precision,
    notes            text
);
