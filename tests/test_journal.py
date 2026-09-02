from rightsrelay.journal import Journal


def test_journal_maps_event_to_real_sibyl_fields_and_reads_it_back(tmp_path) -> None:
    journal = Journal(tmp_path / "memory.db")

    event_id = journal.record(
        event="authorization.reviewed",
        actor="reviewer.local",
        status="CLEARED_LIMITED",
        reasons=["paid media is not authorized"],
        acp_job_id="acp-job-123",
        x402_tx="0xabc123",
        ts="2026-09-02T20:00:00Z",
    )

    events = journal.read_recent(limit=1)

    assert events == [
        {
            "id": event_id,
            "ts": "2026-09-02T20:00:00Z",
            "evaluated": {
                "entity_name": "campaign-aurora:neon-drive",
                "status": "CLEARED_LIMITED",
                "reasons": ["paid media is not authorized"],
            },
            "acted": {
                "event": "authorization.reviewed",
                "actor": "reviewer.local",
            },
            "forward": {"authorization_status": "CLEARED_LIMITED"},
            "extra": {
                "event": "authorization.reviewed",
                "entity_name": "campaign-aurora:neon-drive",
                "status": "CLEARED_LIMITED",
                "reasons": ["paid media is not authorized"],
                "acp_job_id": "acp-job-123",
                "x402_tx": "0xabc123",
            },
        }
    ]
