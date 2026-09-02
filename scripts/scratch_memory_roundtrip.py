from __future__ import annotations

import json
import sys
from pathlib import Path

from sibyl_memory_client import MemoryClient

TENANT_ID = "rightsrelay"
KIND = "UseAuthorization"
NAME = "campaign-aurora:neon-drive"

db_path = Path(sys.argv[1] if len(sys.argv) > 1 else "scratch-memory.db")
client = MemoryClient.local(db_path, tenant_id=TENANT_ID)
body = {"asset_id": "neon-drive", "status": "PENDING", "version": 1}
written = client.set_entity(KIND, NAME, body)
read_back = client.get_entity(KIND, NAME)
assert read_back["body"] == body
assert read_back["id"] == written["id"]
print(json.dumps(read_back, indent=2, sort_keys=True))
