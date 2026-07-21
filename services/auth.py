"""Authentication (§3, §8).

Supabase Auth when configured; a single local analyst otherwise so the app is
fully usable offline. The service-role key is never used here — only the anon key
via the standard client, so Row Level Security applies.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from config.logging import get_logger
from config.settings import SETTINGS

log = get_logger("auth")


@dataclass
class User:
    email: str
    id: Optional[str] = None
    is_local: bool = False


LOCAL_USER = User(email="local analyst", id="local", is_local=True)


class AuthManager:
    def __init__(self, client=None) -> None:
        self._client = client
        self._user: Optional[User] = None if SETTINGS.supabase_enabled else LOCAL_USER

    @property
    def enabled(self) -> bool:
        return SETTINGS.supabase_enabled

    def _get_client(self):
        if self._client is None:
            from supabase import create_client

            self._client = create_client(
                SETTINGS.supabase_url, SETTINGS.supabase_anon_key
            )
        return self._client

    def sign_in(self, email: str, password: str) -> User:
        if not self.enabled:
            self._user = LOCAL_USER
            return self._user
        res = self._get_client().auth.sign_in_with_password(
            {"email": email, "password": password}
        )
        self._user = User(email=email, id=getattr(res.user, "id", None))
        return self._user

    def sign_out(self) -> None:
        if self.enabled and self._client is not None:
            try:
                self._client.auth.sign_out()
            except Exception as exc:  # noqa: BLE001
                log.warning("sign_out failed: %s", exc)
        self._user = None if self.enabled else LOCAL_USER

    def current_user(self) -> Optional[User]:
        return self._user
