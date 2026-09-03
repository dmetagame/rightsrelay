from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from sibyl_memory_client import MemoryClient

from rightsrelay.memory import AUTHORIZATION_NAME, TENANT_ID
from rightsrelay.models import AuthorizationStatus


class Journal:
    """Structured COLD-event adapter over Sibyl Memory's real journal API."""

    def __init__(self, path: str | Path) -> None:
        self._client = MemoryClient.local(path, tenant_id=TENANT_ID)

    def record(
        self,
        *,
        event: str,
        actor: str,
        status: AuthorizationStatus,
        reasons: list[str] | None = None,
        acp_job_id: str | None = None,
        x402_tx: str | None = None,
        metadata: Mapping[str, Any] | None = None,
        ts: str | None = None,
    ) -> str:
        reason_list = list(reasons or [])
        extra: dict[str, Any] = {
            "event": event,
            "entity_name": AUTHORIZATION_NAME,
            "status": status,
            "reasons": reason_list,
        }
        if acp_job_id is not None:
            extra["acp_job_id"] = acp_job_id
        if x402_tx is not None:
            extra["x402_tx"] = x402_tx
        for key, value in (metadata or {}).items():
            if key not in extra:
                extra[key] = value

        return self._client.write_event(
            evaluated={
                "entity_name": AUTHORIZATION_NAME,
                "status": status,
                "reasons": reason_list,
            },
            acted={"event": event, "actor": actor},
            forward={"authorization_status": status},
            extra=extra,
            ts=ts,
        )

    def read_recent(self, *, limit: int = 10) -> list[dict[str, Any]]:
        return self._client.read_events(limit=limit)
