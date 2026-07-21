# Deployment Guide

The platform runs three ways, in increasing order of setup:

1. **Local demo** — zero keys, fixture data (default).
2. **Local live** — real SEC data, durable local SQLite storage.
3. **Cloud** — Streamlit Community Cloud + Supabase (multi-user, persistent).

---

## 1. Local (Windows, no venv activation needed)

Avoids PowerShell execution-policy issues by calling the venv Python directly.

```powershell
cd "C:\Users\Wmaxe\Options Trader\valuation-platform"
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Run the tests (no keys, all external services mocked):

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

### Going live locally
Copy `.env.example` → `.env` and set:

```
APP_MODE=live
SEC_USER_AGENT="Your Fund Research (you@example.com)"
```

Live mode uses **SEC EDGAR** for data and a durable **SQLite** file
(`data/valuation_platform.sqlite`, gitignored) for saved valuations — no cloud
required. Add `FMP_API_KEY` / `FRED_API_KEY` only if you want those convenience
sources.

### Local AI (free)
Install [Ollama](https://ollama.com), pull a model, and the AI memo works offline:

```powershell
ollama pull llama3.1
```

Set `AI_PROVIDER=ollama` (default). If Ollama isn't running, the app falls back
to the built-in offline provider so the workflow still functions.

---

## 2. Supabase (persistence)

1. Create a project at [supabase.com](https://supabase.com).
2. In the SQL editor, run the schema then the policies:
   - `database/schema.sql`
   - `database/policies.sql`   *(enables Row Level Security; valuation runs are append-only)*
   Or apply the numbered files in `database/migrations/` in order.
3. From **Project Settings → API**, copy the **Project URL** and the **anon**
   public key. Set:
   ```
   SUPABASE_URL=...
   SUPABASE_ANON_KEY=...
   ```
4. Install the client: `pip install supabase` (add it to requirements before
   deploying).

> ⚠️ **Never** put the **service-role** key in the app, `.env` committed to git,
> or Streamlit secrets used by the browser. The app authenticates with the anon
> key so RLS applies. The service-role key bypasses RLS and is server-only.

When `SUPABASE_URL` + `SUPABASE_ANON_KEY` are set, the app uses Supabase instead
of SQLite automatically. If Supabase is unreachable it degrades to SQLite.

---

## 3. Streamlit Community Cloud

1. Push this repo to GitHub (the `.venv/`, `.env`, `data/cache/`, and
   `.streamlit/secrets.toml` are already gitignored).
2. On [share.streamlit.io](https://share.streamlit.io), create an app from the
   repo with **main file** `app.py`. Choose **Python 3.12**.
3. Add `supabase` to `requirements.txt` if using cloud persistence.
4. In **App → Settings → Secrets**, paste the contents of
   `.streamlit/secrets.toml.example` with real values. `bootstrap.py` bridges
   `st.secrets` into environment variables at startup, so the same settings work
   locally (`.env`) and in the cloud (`st.secrets`).
5. Notes:
   - Ollama is **not** reachable from Streamlit Cloud — use `AI_PROVIDER=gemini`
     with a `GEMINI_API_KEY` there.
   - Provide a descriptive `SEC_USER_AGENT`; SEC requires it.
   - FMP data redistribution/display may require a license before showing it in
     a shared deployment (§6).

---

## Secrets hygiene checklist

- [ ] `.env` and `.streamlit/secrets.toml` are gitignored (they are).
- [ ] Only the Supabase **anon** key is used client-side.
- [ ] No API keys are hard-coded anywhere (`grep` for `key=` before pushing).
- [ ] Streamlit is deployed from a clean repo with no committed secrets.
- [ ] Stack traces are not surfaced to users (logging is separate from the UI).

---

## Data & licensing notes

- **SEC EDGAR** — source of truth; free; requires a User-Agent with contact info.
- **FMP** — optional; redistribution/display may need a license.
- **FRED / Damodaran** — reference data; check terms before redistribution.
- The platform produces **research and paper valuations only** — not investment
  advice, and it never executes trades.
