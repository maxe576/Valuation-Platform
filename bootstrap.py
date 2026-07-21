"""Secrets bootstrap — must be imported FIRST in app.py (before config.settings).

On Streamlit Community Cloud, configuration is provided via ``st.secrets`` rather
than environment variables. The engines and settings read ``os.environ``, so this
module bridges ``st.secrets`` → ``os.environ`` before Settings is constructed.
Locally (with a ``.env`` file) it is a harmless no-op.
"""
from __future__ import annotations

import os


def _load_streamlit_secrets() -> None:
    try:
        import streamlit as st

        # Accessing st.secrets raises if no secrets file exists; guard it.
        secrets = st.secrets
    except Exception:
        return

    try:
        items = dict(secrets)
    except Exception:
        return

    for key, value in items.items():
        if isinstance(value, (str, int, float)) and key not in os.environ:
            os.environ[key] = str(value)


_load_streamlit_secrets()
