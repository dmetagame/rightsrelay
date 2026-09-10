import asyncio
import re
from pathlib import Path

import httpx

from rightsrelay.console import create_console_app


def test_console_rejects_actions_without_operator_token(tmp_path: Path):
    app = create_console_app(database=tmp_path / "memory.sqlite", working_directory=tmp_path)

    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                     base_url="http://127.0.0.1:8080") as client:
            response = await client.post("/actions/init-aurora")
            assert response.status_code == 403
            malformed = await client.post("/actions/init-aurora", headers={
                b"X-RightsRelay-Action-Token": b"\xff"})
            assert malformed.status_code == 403
            assert not (await client.get("/status")).json()["entity_found"]

    asyncio.run(run())


def test_console_rejects_foreign_origins_hosts_and_remote_clients(tmp_path: Path):
    app = create_console_app(database=tmp_path / "memory.sqlite", working_directory=tmp_path)

    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                     base_url="http://127.0.0.1:8080") as client:
            board = await client.get("/")
            token = re.search(r'name="rightsrelay-action-token" content="([^"]+)"', board.text).group(1)
            for extra in [
                {"Origin": "https://untrusted.example"},
                {"Origin": "null"},
                {"Origin": "http://127.0.0.1:9999"},
                {"Host": "untrusted.example"},
                {"Sec-Fetch-Site": "cross-site"},
            ]:
                response = await client.post("/actions/init-aurora",
                    headers={"X-RightsRelay-Action-Token": token, **extra})
                assert response.status_code == 403, extra
            assert not (await client.get("/status")).json()["entity_found"]
            approved = await client.post("/actions/init-aurora", headers={
                "X-RightsRelay-Action-Token": token, "Origin": "http://127.0.0.1:8080"})
            assert approved.status_code == 200
            assert approved.json()["returncode"] == 0
            assert board.headers["cache-control"] == "no-store"
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, client=("203.0.113.10", 12345)),
            base_url="http://127.0.0.1:8080",
        ) as remote:
            assert (await remote.get("/")).status_code == 403
            assert (await remote.get("/status")).status_code == 403

    asyncio.run(run())


def test_operator_token_is_invalid_after_launcher_restart(tmp_path: Path):
    async def run():
        apps = [create_console_app(database=tmp_path / "memory.sqlite", working_directory=tmp_path)
                for _ in range(2)]
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=apps[0]),
                                     base_url="http://localhost:8080") as first:
            token = re.search(r'name="rightsrelay-action-token" content="([^"]+)"',
                              (await first.get("/")).text).group(1)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=apps[1]),
                                     base_url="http://localhost:8080") as second:
            assert (await second.post("/actions/init-aurora", headers={
                "X-RightsRelay-Action-Token": token})).status_code == 403
            assert not (await second.get("/status")).json()["entity_found"]
    asyncio.run(run())
