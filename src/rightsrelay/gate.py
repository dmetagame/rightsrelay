from __future__ import annotations

from rightsrelay.models import GateDecision, ReleaseAttempt, UseAuthorization


def can_release(
    authorization: UseAuthorization,
    attempt: ReleaseAttempt,
) -> GateDecision:
    """Return the deterministic release decision for an authorization."""
    reasons: list[str] = []

    if attempt.campaign_id != authorization.campaign_id:
        reasons.append(
            f"campaign '{attempt.campaign_id}' does not match authorization campaign "
            f"'{authorization.campaign_id}'"
        )
    if attempt.asset_id != authorization.asset_id:
        reasons.append(
            f"asset '{attempt.asset_id}' does not match authorization asset "
            f"'{authorization.asset_id}'"
        )
    if authorization.status in {"PENDING", "BLOCKED"}:
        reasons.append(f"authorization status is {authorization.status}")
    if attempt.channel not in authorization.channels:
        reasons.append(f"channel '{attempt.channel}' is not authorized")
    if attempt.paid and not authorization.paid:
        reasons.append("paid media is not authorized")
    unauthorized_territories = sorted(
        set(attempt.territories) - set(authorization.territories)
    )
    if unauthorized_territories:
        reasons.append(
            "territories are not authorized: " + ", ".join(unauthorized_territories)
        )
    if attempt.date < authorization.valid_from:
        reasons.append(
            f"release date {attempt.date.isoformat()} is before authorization start "
            f"{authorization.valid_from.isoformat()}"
        )
    if attempt.date > authorization.expires_on:
        reasons.append(
            f"release date {attempt.date.isoformat()} is after authorization expiry "
            f"{authorization.expires_on.isoformat()}"
        )

    if reasons:
        return GateDecision(ok=False, status="BLOCKED", reasons=reasons)

    return GateDecision(
        ok=True,
        status=authorization.status,
        reasons=[],
    )
