-- =====================================================================
-- Row Level Security policies (Supabase). Wired up in Phase 8.
-- The service-role key bypasses RLS and must never reach client code.
-- Starting posture: any authenticated user may read/write research data;
-- roles (analyst vs. admin) are refined in Phase 8.
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

    execute format(
      'drop policy if exists %I on %I;', t || '_auth_read', t);
    execute format(
      'create policy %I on %I for select to authenticated using (true);',
      t || '_auth_read', t);

    execute format(
      'drop policy if exists %I on %I;', t || '_auth_write', t);
    execute format(
      'create policy %I on %I for insert to authenticated with check (true);',
      t || '_auth_write', t);
  end loop;
end $$;

-- Valuation runs are append-only: no UPDATE/DELETE policy is granted, so
-- historical records cannot be altered by application users (§25, §33).
