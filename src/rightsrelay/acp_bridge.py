"""Local JSON-only bridge for ACP. No signer keys or conversation input."""
from __future__ import annotations

import json
import sys

from rightsrelay.acp_client import SERVICE_REQUIREMENT, assert_memory_matches_delivery
from rightsrelay.acp_provider import apply_limited_grant
from rightsrelay.memory import AuthorizationMemory


def main() -> int:
    try:
        mode, database = sys.argv[1:]
        request = json.load(sys.stdin)
        if mode == "inspect":
            authorization = AuthorizationMemory(database).get_authorization()
            result = {"status": authorization.status, "acp_job_id": authorization.acp_job_id,
                      "requirement": SERVICE_REQUIREMENT}
        elif mode == "validate":
            if json.dumps(request.get("requirement"), sort_keys=True) != json.dumps(SERVICE_REQUIREMENT, sort_keys=True):
                raise ValueError("request outside the fixed review scope")
            authorization = AuthorizationMemory(database).get_authorization()
            job_id = str(request["job_id"])
            if not (authorization.status == "PENDING" and authorization.acp_job_id is None):
                if not (authorization.status == "CLEARED_LIMITED" and authorization.acp_job_id == job_id):
                    raise ValueError("memory belongs to another review or paid grant")
            result = {"ok": True}
        elif mode in {"apply", "verify"}:
            job_id = str(request["job_id"])
            if not job_id.isascii() or not job_id.isdigit() or int(job_id) <= 0:
                raise ValueError("invalid onchain job ID")
            if mode == "apply":
                result = apply_limited_grant(memory_path=database, acp_job_id=job_id)
            else:
                assert_memory_matches_delivery(
                    memory_path=database, job_id=int(job_id), deliverable=request["deliverable"],
                )
                result = {"ok": True}
        else:
            raise ValueError("unknown ACP memory operation")
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception as exc:
        # No exception values: upstream SDKs can include credential-bearing requests.
        print(json.dumps({"error": f"ACP memory operation failed ({type(exc).__name__})"}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
