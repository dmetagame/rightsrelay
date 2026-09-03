from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from collections.abc import Callable, Mapping
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from sibyl_memory_client import NotFoundError

from rightsrelay.export import ExportBlockedError, build_release_packet
from rightsrelay.gate import can_release
from rightsrelay.journal import Journal
from rightsrelay.memory import AuthorizationMemory, MemoryUnavailableError
from rightsrelay.models import ReleaseAttempt, UseAuthorization

DEFAULT_DATABASE = Path("./data/rightsrelay.sqlite")
PACKET_RELATIVE_PATH = Path("release-packets/campaign-aurora-neon-drive.json")


GrantPurchase = Callable[[], dict[str, Any]]


def _database_path() -> Path:
    configured = os.environ.get("RIGHTSRELAY_DB")
    return Path(configured).expanduser().resolve() if configured else DEFAULT_DATABASE.resolve()


def _utc_wall_clock() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _git_head() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.stdout.strip() if completed.returncode == 0 else "NOT A REPOSITORY"


def _csv_values(raw: str) -> list[str]:
    return [value.strip() for value in raw.split(",") if value.strip()]


def _merged(existing: list[str], additions: list[str]) -> list[str]:
    return list(dict.fromkeys([*existing, *additions]))


def _updated(
    authorization: UseAuthorization,
    **changes: Any,
) -> UseAuthorization:
    body = authorization.model_dump(mode="json")
    body.update(changes)
    return UseAuthorization.model_validate(body)


def _is_not_found(error: BaseException) -> bool:
    current: BaseException | None = error
    while current is not None:
        if isinstance(current, NotFoundError):
            return True
        current = current.__cause__
    return False


def _print_entity(authorization: UseAuthorization) -> None:
    print(json.dumps(authorization.model_dump(mode="json"), indent=2, sort_keys=True))


def _status(arguments: argparse.Namespace, database: Path) -> int:
    print(f"PID: {os.getpid()}")
    print(f"UTC: {_utc_wall_clock()}")
    print(f"GIT: {_git_head()}")
    memory = AuthorizationMemory(database)
    print("ENTITY:")
    try:
        _print_entity(memory.get_authorization())
    except MemoryUnavailableError as exc:
        if not _is_not_found(exc):
            raise
        print("NOT FOUND")

    extras = [
        event.get("extra")
        for event in Journal(database).read_recent(limit=arguments.last)
    ]
    print("JOURNAL EXTRAS:")
    print(json.dumps(extras, indent=2, sort_keys=True))
    return 0


def _init_aurora(_: argparse.Namespace, database: Path) -> int:
    authorization = UseAuthorization(
        asset_id="neon-drive",
        campaign_id="aurora",
        channels=["youtube"],
        paid=False,
        territories=["UK"],
        valid_from=date(2026, 9, 1),
        expires_on=date(2026, 9, 30),
        status="PENDING",
        version=1,
        last_actor="producer",
    )
    persisted = AuthorizationMemory(database).set_authorization(authorization)
    Journal(database).record(
        event="authorization.initialized",
        actor="producer",
        status=persisted.status,
        reasons=persisted.blocking_reasons,
        acp_job_id=persisted.acp_job_id,
        x402_tx=persisted.x402_tx,
    )
    print("INITIALIZED")
    _print_entity(persisted)
    return 0


def _review_limited(_: argparse.Namespace, database: Path) -> int:
    memory = AuthorizationMemory(database)
    current = memory.get_authorization()
    reviewed = _updated(
        current,
        channels=["youtube"],
        paid=False,
        territories=["UK"],
        valid_from="2026-09-01",
        expires_on="2026-09-30",
        status="CLEARED_LIMITED",
        blocking_reasons=[],
        version=current.version + 1,
        last_actor="reviewer.local",
    )
    persisted = memory.set_authorization(reviewed)
    Journal(database).record(
        event="authorization.reviewed",
        actor="reviewer.local",
        status=persisted.status,
        reasons=persisted.blocking_reasons,
        acp_job_id=persisted.acp_job_id,
        x402_tx=persisted.x402_tx,
    )
    print("REVIEWED LIMITED (local reviewer; not Virtuals ACP)")
    _print_entity(persisted)
    return 0


def _attempt(arguments: argparse.Namespace, database: Path) -> int:
    memory = AuthorizationMemory(database)
    authorization = memory.get_authorization()
    attempt = ReleaseAttempt(
        channel=arguments.channel,
        paid=arguments.paid,
        territories=_csv_values(arguments.territories),
        date=date.fromisoformat(arguments.date),
        campaign_id="aurora",
        asset_id="neon-drive",
    )
    decision = can_release(authorization, attempt)
    Journal(database).record(
        event="release.attempted",
        actor="launcher.cli",
        status=decision.status,
        reasons=decision.reasons,
        acp_job_id=authorization.acp_job_id,
        x402_tx=authorization.x402_tx,
    )
    packet_path = PACKET_RELATIVE_PATH.resolve()

    if not decision.ok:
        try:
            build_release_packet(
                memory_path=database,
                attempt=attempt,
                destination=packet_path,
            )
        except ExportBlockedError as exc:
            print("BLOCKED")
            for reason in exc.decision.reasons:
                print(f"- {reason}")
            return 1
        raise RuntimeError("gate reported blocked but export produced a packet")

    build_release_packet(
        memory_path=database,
        attempt=attempt,
        destination=packet_path,
    )
    print("CLEARED")
    print(f"PACKET: {packet_path}")
    return 0


def apply_grant(
    *,
    database: Path,
    paid: bool,
    channels: list[str],
    territories: list[str],
    expires: str,
    x402_tx: str | None = None,
    actor: str = "grant.cli",
    event: str = "authorization.grant_applied_cli",
    journal_metadata: Mapping[str, Any] | None = None,
) -> UseAuthorization:
    memory = AuthorizationMemory(database)
    current = memory.get_authorization()
    updated = _updated(
        current,
        channels=_merged(current.channels, channels),
        paid=current.paid or paid,
        territories=_merged(current.territories, territories),
        expires_on=expires,
        status="CLEARED",
        blocking_reasons=[],
        x402_tx=x402_tx or current.x402_tx,
        version=current.version + 1,
        last_actor=actor,
    )
    persisted = memory.set_authorization(updated)
    Journal(database).record(
        event=event,
        actor=actor,
        status=persisted.status,
        reasons=persisted.blocking_reasons,
        acp_job_id=persisted.acp_job_id,
        x402_tx=persisted.x402_tx,
        metadata=journal_metadata,
    )
    return persisted


def acquire_grant(
    *,
    database: Path,
    purchase: GrantPurchase | None = None,
) -> UseAuthorization:
    if purchase is None:
        from rightsrelay.x402_buyer import buy_grant

        purchase = buy_grant

    grant = purchase()
    if grant.get("asset_id") != "neon-drive" or grant.get("campaign_id") != "aurora":
        raise ValueError("x402 grant does not match campaign-aurora:neon-drive")
    transaction = grant.get("x402_tx")
    if not isinstance(transaction, str) or not transaction:
        raise ValueError("x402 grant is missing its settlement identifier")
    payment = grant.get("_payment")
    metadata = payment if isinstance(payment, dict) else {}

    return apply_grant(
        database=database,
        paid=grant.get("paid") is True,
        channels=list(grant.get("channels", [])),
        territories=list(grant.get("territories", [])),
        expires=str(grant["expires_on"]),
        x402_tx=transaction,
        actor="x402.buyer",
        event="authorization.grant_acquired_x402",
        journal_metadata=metadata,
    )


def _apply_grant(arguments: argparse.Namespace, database: Path) -> int:
    persisted = apply_grant(
        database=database,
        paid=arguments.paid,
        channels=_csv_values(arguments.channels),
        territories=_csv_values(arguments.territories),
        expires=arguments.expires,
    )
    print("GRANT APPLIED (CLI mutation; not x402)")
    _print_entity(persisted)
    return 0


def _acquire_grant(_: argparse.Namespace, database: Path) -> int:
    persisted = acquire_grant(database=database)
    print("GRANT ACQUIRED VIA X402 (rights holder: rightsrelay-demo)")
    transaction = persisted.x402_tx or ""
    if re.fullmatch(r"0x[0-9a-fA-F]{64}", transaction):
        explorer = (
            "https://basescan.org/tx/"
            if os.environ.get("RIGHTSRELAY_X402_MAINNET") == "1"
            else "https://sepolia.basescan.org/tx/"
        )
        print(f"EXPLORER: {explorer}{transaction}")
    else:
        print(f"SETTLEMENT IDENTIFIER: {transaction}")
    _print_entity(persisted)
    return 0


def _acp_review(_: argparse.Namespace, database: Path) -> int:
    from rightsrelay.acp_client import ACPReviewError, missing_acp_env, run_acp_review

    missing = missing_acp_env()
    if missing:
        print(f"ACP CONFIG MISSING: {', '.join(missing)}")
        return 2
    try:
        result = run_acp_review(memory_path=database)
    except ACPReviewError as exc:
        print(f"ACP REVIEW FAILED: {exc}")
        return 2
    except Exception as exc:
        print(f"ACP REVIEW FAILED: Virtuals ACP SDK error ({type(exc).__name__})")
        return 2
    print(f"ACP REVIEW COMPLETED: {result.phase}")
    print(f"ACP JOB ID: {result.job_id}")
    print(f"ACP CONTRACT: {result.contract_explorer_url}")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rightsrelay")
    commands = parser.add_subparsers(dest="command", required=True)

    status = commands.add_parser("status")
    status.add_argument("--last", type=int, default=10)
    status.set_defaults(handler=_status)

    commands.add_parser("init-aurora").set_defaults(handler=_init_aurora)
    commands.add_parser("review-limited").set_defaults(handler=_review_limited)

    attempt = commands.add_parser("attempt")
    attempt.add_argument("--channel", required=True)
    attempt.add_argument("--paid", action="store_true")
    attempt.add_argument("--territories", required=True)
    attempt.add_argument("--date", required=True)
    attempt.set_defaults(handler=_attempt)

    commands.add_parser("acquire-grant").set_defaults(handler=_acquire_grant)
    commands.add_parser("acp-review").set_defaults(handler=_acp_review)

    apply_grant = commands.add_parser("apply-grant")
    apply_grant.add_argument("--paid", action="store_true")
    apply_grant.add_argument("--channels", required=True)
    apply_grant.add_argument("--territories", required=True)
    apply_grant.add_argument("--expires", required=True)
    apply_grant.set_defaults(handler=_apply_grant)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    database = _database_path()
    print(f"DB: {database}")
    try:
        return arguments.handler(arguments, database)
    except MemoryUnavailableError as exc:
        if _is_not_found(exc):
            print("NOT FOUND")
            return 2
        raise
