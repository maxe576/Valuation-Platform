"""Custom CSS to bring the Streamlit app close to the 'Vantage' mockup.

Injected once per run. Targets Streamlit's stable data-testid selectors to style
metrics as institutional cards, tighten spacing, apply the teal accent, and give
tables/expanders/tabs a cleaner, research-desk feel.
"""
from __future__ import annotations

import streamlit as st

_CSS = """
<style>
:root{
  --accent:#46c7b8; --accent-2:#2f9e91; --ink:#0d1219; --surface:#141c26;
  --surface-2:#1a2430; --border:#26333f; --muted:#8a99ab; --faint:#5f6f81;
}
/* App ground + width */
.stApp{ background:var(--ink); }
.block-container{ padding-top:2.4rem; padding-bottom:3rem; max-width:1320px; }
[data-testid="stHeader"]{ background:transparent; }

/* Headings */
h1,h2,h3{ letter-spacing:-.01em; font-weight:680; }
h1{ font-size:1.7rem; }
[data-testid="stCaptionContainer"]{ color:var(--muted); }

/* Metric cards → institutional tiles */
[data-testid="stMetric"]{
  background:var(--surface); border:1px solid var(--border); border-radius:12px;
  padding:14px 16px;
}
[data-testid="stMetricLabel"] p{
  text-transform:uppercase; letter-spacing:.07em; font-size:.7rem;
  font-weight:600; color:var(--faint);
}
[data-testid="stMetricValue"]{
  font-variant-numeric:tabular-nums; font-weight:700; letter-spacing:-.01em;
}

/* Sidebar */
[data-testid="stSidebar"]{ background:#101821; border-right:1px solid var(--border); }
[data-testid="stSidebar"] [data-testid="stMetric"]{ background:var(--surface-2); }

/* Buttons — teal primary */
.stButton>button, .stDownloadButton>button, .stFormSubmitButton>button{
  border-radius:8px; border:1px solid var(--border); font-weight:600;
}
.stButton>button[kind="primary"], .stFormSubmitButton>button[kind="primary"]{
  background:var(--accent); border-color:var(--accent); color:#06110f;
}
.stButton>button[kind="primary"]:hover, .stFormSubmitButton>button[kind="primary"]:hover{
  background:var(--accent-2); border-color:var(--accent-2); color:#06110f;
}
.stButton>button:hover{ border-color:var(--accent); color:var(--accent); }

/* Tabs */
.stTabs [data-baseweb="tab-list"]{ gap:2px; border-bottom:1px solid var(--border); }
.stTabs [data-baseweb="tab"]{ font-weight:600; }
.stTabs [aria-selected="true"]{ color:var(--accent); }

/* Dataframes + expanders */
[data-testid="stDataFrame"]{ border:1px solid var(--border); border-radius:10px; }
[data-testid="stExpander"] details{
  border:1px solid var(--border); border-radius:10px; background:var(--surface);
}
[data-testid="stExpander"] summary:hover{ color:var(--accent); }

/* Inputs */
[data-testid="stTextInput"] input, [data-testid="stNumberInput"] input{
  font-variant-numeric:tabular-nums;
}

/* Alerts a touch tighter */
[data-testid="stAlert"]{ border-radius:10px; }
</style>
"""


def inject() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
