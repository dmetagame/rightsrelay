from __future__ import annotations

import pytest

from rightsrelay.acp_client import ACPReviewError, run_acp_review


def test_acp_review_requires_explicit_mainnet_transaction_approval(tmp_path, monkeypatch):
    monkeypatch.delenv("RIGHTSRELAY_ACP_ALLOW_TRANSACTIONS", raising=False)
    with pytest.raises(ACPReviewError, match="transactions are disabled"):
        run_acp_review(memory_path=tmp_path / "absent.sqlite")
    assert not (tmp_path / "absent.sqlite").exists()
