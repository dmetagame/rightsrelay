from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    from sibyl_memory_client import MemoryClient
except ImportError:  # pragma: no cover - exercised by deletion-test monkeypatch
    MemoryClient = None  # type: ignore[assignment,misc]

from rightsrelay.models import ReleaseAttempt, UseAuthorization

TENANT_ID = "rightsrelay"
AUTHORIZATION_KIND = "UseAuthorization"
AUTHORIZATION_NAME = "campaign-aurora:neon-drive"
CURRENT_ATTEMPT_KEY = "current-release-attempt"


class MemoryUnavailableError(RuntimeError):
    """Raised when authorization memory cannot be created, read, or written."""


class AuthorizationMemory:
    """Fail-closed access to RightsRelay's single authorization entity."""

    def __init__(self, path: str | Path) -> None:
        if MemoryClient is None:
            raise MemoryUnavailableError("Sibyl MemoryClient is unavailable")
        try:
            self._client = MemoryClient.local(path, tenant_id=TENANT_ID)
        except Exception as exc:
            raise MemoryUnavailableError("Sibyl memory could not be opened") from exc

    def set_authorization(self, authorization: UseAuthorization) -> UseAuthorization:
        try:
            row = self._client.set_entity(
                AUTHORIZATION_KIND,
                AUTHORIZATION_NAME,
                authorization.model_dump(mode="json"),
            )
            return self._authorization_from_row(row)
        except Exception as exc:
            raise MemoryUnavailableError("authorization could not be persisted") from exc

    def get_authorization(self) -> UseAuthorization:
        try:
            row = self._client.get_entity(
                AUTHORIZATION_KIND,
                AUTHORIZATION_NAME,
            )
            return self._authorization_from_row(row)
        except Exception as exc:
            raise MemoryUnavailableError("authorization could not be recalled") from exc

    def set_current_attempt(self, attempt: ReleaseAttempt) -> None:
        try:
            self._client.set_state(
                CURRENT_ATTEMPT_KEY,
                attempt.model_dump(mode="json"),
            )
        except Exception as exc:
            raise MemoryUnavailableError("current release attempt could not be persisted") from exc

    @staticmethod
    def _authorization_from_row(row: dict[str, Any]) -> UseAuthorization:
        body = row.get("body")
        if not isinstance(body, dict):
            raise MemoryUnavailableError("authorization memory has an invalid body")
        return UseAuthorization.model_validate(body)
