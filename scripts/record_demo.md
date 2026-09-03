# RightsRelay unedited demo shot list

This take demonstrates durable Sibyl recall, a hard release refusal, and a real
Base Sepolia x402 payment to RightsRelay acting as the rights holder. It does
not claim a Virtuals ACP lifecycle.

## Before recording

1. Start from the repository root with the virtual environment installed.
2. Fund the buyer address with Base Sepolia test ETH and USDC. Set
   `RIGHTSRELAY_BUYER_KEY` and set `RIGHTSRELAY_PAY_TO` to the seller address.
3. Start `./scripts/run_seller.sh` in a visible terminal. Leave its Base
   Sepolia network, x402.org facilitator, `$0.001` price, and rights-holder
   disclosure on screen.
4. Set `RIGHTSRELAY_DB` to one absolute SQLite path used by both sessions.
5. Use a new database and confirm that the release-packet destination does not
   exist. Do not delete an unfamiliar database or packet during the take.
6. Keep the wall clock and terminal visible for the entire unedited recording.

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
4. The paid Instagram request for US and UK prints `BLOCKED`, lists its reasons,
   exits 1 internally, and creates no release packet.
5. `acquire-grant` visibly shows the initial HTTP 402 and `PAYMENT-REQUIRED`,
   pays `$0.001` test USDC, retries, and shows the real `PAYMENT-RESPONSE`.
6. Show the facilitator settlement identifier. Show the Base Sepolia explorer
   URL only when the facilitator returned a transaction hash.
7. The identical paid Instagram request now prints `CLEARED` and writes the
   release packet.
8. End on `status`: show the same WARM entity with the paid Instagram/US+UK
   grant, `x402_tx`, and the COLD payment metadata.

Do not claim mainnet, ACP, or third-party rights/platform integrations. The
track is original, and `rightsrelay-demo` is the rights holder operating the
402 server.
