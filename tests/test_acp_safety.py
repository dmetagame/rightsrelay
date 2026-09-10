from __future__ import annotations

import os
import subprocess
import sys

import pytest

from rightsrelay.acp_client import ACPReviewError, run_acp_review


def test_acp_review_requires_explicit_mainnet_transaction_approval(tmp_path, monkeypatch):
    monkeypatch.delenv("RIGHTSRELAY_ACP_ALLOW_TRANSACTIONS", raising=False)
    with pytest.raises(ACPReviewError, match="transactions are disabled"):
        run_acp_review(memory_path=tmp_path / "absent.sqlite")
    assert not (tmp_path / "absent.sqlite").exists()


def test_acp_review_accepts_public_signer_configuration_but_still_requires_memory(tmp_path, monkeypatch):
    from rightsrelay.memory import MemoryUnavailableError

    monkeypatch.setenv("RIGHTSRELAY_ACP_ALLOW_TRANSACTIONS", "1")
    for name, value in {
        "BUYER_AGENT_WALLET_ADDRESS": "0xfd6a60eb9e7acd3bbb613fe932dcdd76861f7882",
        "SELLER_AGENT_WALLET_ADDRESS": "0xca8c2b88533d0085404ed46f4101f38997999701",
        "BUYER_WALLET_ID": "buyer-wallet",
        "SELLER_WALLET_ID": "reviewer-wallet",
        "BUYER_SIGNER_PUBLIC_KEY": "public-selector-only",
        "SELLER_SIGNER_PUBLIC_KEY": "public-selector-only",
        "RIGHTSRELAY_ACP_SIGNER_BINARY": "/missing/signer-must-not-run",
    }.items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv("BUYER_SIGNER_PRIVATE_KEY", raising=False)
    monkeypatch.delenv("SELLER_SIGNER_PRIVATE_KEY", raising=False)
    with pytest.raises(MemoryUnavailableError, match="authorization could not be recalled"):
        run_acp_review(memory_path=tmp_path / "absent.sqlite")


def test_provider_public_config_still_refuses_missing_memory_before_signing(tmp_path):
    environment = {
        "PATH": os.environ["PATH"],
        "RIGHTSRELAY_ACP_ALLOW_TRANSACTIONS": "1",
        "RIGHTSRELAY_ACP_MAX_USDC": "0.01",
        "RIGHTSRELAY_DB": str(tmp_path / "absent.sqlite"),
        "BUYER_AGENT_WALLET_ADDRESS": "0xfd6a60eb9e7acd3bbb613fe932dcdd76861f7882",
        "SELLER_AGENT_WALLET_ADDRESS": "0xca8c2b88533d0085404ed46f4101f38997999701",
        "SELLER_WALLET_ID": "reviewer-wallet",
        "SELLER_SIGNER_PUBLIC_KEY": "public-selector-only",
        "RIGHTSRELAY_ACP_SIGNER_BINARY": "/missing/signer-must-not-run",
    }
    result = subprocess.run([sys.executable, "-m", "rightsrelay.acp_provider"],
                            env=environment, capture_output=True, text=True, timeout=20)
    assert result.returncode == 2
    assert "Sibyl memory refused the ACP operation" in result.stdout
    assert result.stderr == ""
