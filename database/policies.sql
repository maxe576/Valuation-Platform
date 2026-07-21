-- =====================================================================
-- Row Level Security policies (Supabase). Phase 8.
-- The service-role key bypasses RLS and must never reach client code.
--
-- The deployed app connects with the shared "anon" role (there is no per-user
-- login gate yet), so policies apply to both `anon` and `authenticated`. This
-- suits an internal single-fund research tool: whoever can open the app can
-- read/write research data. Tighten later by adding Supabase Auth + a login
-- gate and restricting these policies to `authenticated`.
--
-- Reads and inserts are allowed; there is deliberately NO update/delete policy,
-- so historical valuation runs are append-only and cannot be altered (§25, §33).
-- =====================================================================

do $$
declare t text;
begin
  foreach t in array array[
    'companies','filings','financial_facts','metric_aliases','segments',
    'peer_sets','peer_set_members','assumption_sets','valuation_runs',
    'method_results','guidance_points','ai_analyses','manual_overrides',
    'valuation_outcomes'
  ] loop
    execute format('alter table %I enable row level security;', t);

    execute format('drop policy if exists %I on %I;', t || '_read', t);
    execute format(
      'create policy %I on %I for select to anon, authenticated using (true);',
      t || '_read', t);

    execute format('drop policy if exists %I on %I;', t || '_write', t);
    execute format(
      'create policy %I on %I for insert to anon, authenticated with check (true);',
      t || '_write', t);
  end loop;
end $$;

-- Explicit table grants (needed because "Automatically expose new tables" is
-- OFF). RLS above still gates row access; these grants just let the Data API
-- roles reach our specific tables.
grant usage on schema public to anon, authenticated;
grant select, insert on all tables in schema public to anon, authenticated;
