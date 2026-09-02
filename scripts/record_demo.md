# RightsRelay unedited demo shot list

This checkpoint demonstrates durable Sibyl recall and a hard release refusal. It
does not claim a Virtuals ACP lifecycle or an x402 payment.

## Before recording

1. Start from the repository root with the virtual environment installed.
2. Set `RIGHTSRELAY_DB` to one absolute SQLite path used by both sessions.
3. Use a new database and confirm that the release-packet destination does not
   exist. Do not delete an unfamiliar database or packet during the take.
4. Keep the wall clock and terminal visible for the entire unedited recording.

## Session 1 — producer and local reviewer

1. Run `./scripts/demo_session1.sh`.
2. The first `status` shows the process ID, UTC time, commit, database path, and
   empty authorization state.
3. `init-aurora` writes the PENDING authorization.
4. `review-limited` rewrites that entity as YouTube, organic, UK,
   `CLEARED_LIMITED`, explicitly attributed to `reviewer.local`.
5. The final `status` shows the entity and its COLD journal extras.
6. Record the printed shell PID and kill that shell on screen.

## Session 2 — fresh launcher process

1. Open a new shell with the same `RIGHTSRELAY_DB` value.
2. Run `./scripts/demo_session2.sh`.
3. `status` must recall the `CLEARED_LIMITED` entity from Session 1 without any
   chat transcript.
4. The paid Instagram request for US and UK must print `BLOCKED`, list its
   reasons, exit 1 internally, and create no release packet.
5. End on `next: acquire-grant (not wired this turn)`.

Do not show a payment, grant acquisition, ACP job, transaction hash, or green
release in this checkpoint. Those claims require live partner integrations.
