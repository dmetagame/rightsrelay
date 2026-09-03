# RightsRelay unedited demo shot list

This take demonstrates a real Virtuals ACP review coordinated through Sibyl,
durable recall after process death, a hard release refusal, and a later Base
Sepolia x402 rights purchase. Record it only after both live integrations pass.

## Before recording

1. Start from the repository root with the virtual environment installed.
2. Register and fund the Virtuals sandbox buyer and provider, configure the
   `Rights review` offering, and set all five ACP variables from `.env.example`.
3. Start `./scripts/run_acp_provider.sh` in a visible terminal. Show its PID,
   `BASE_SEPOLIA_CONFIG_V2`, provider wallet, and shared database path.
4. Fund the x402 buyer address with Base Sepolia test ETH and USDC. Set
   `RIGHTSRELAY_BUYER_KEY` and set `RIGHTSRELAY_PAY_TO` to the seller address.
5. Start `./scripts/run_seller.sh` in a visible terminal. Leave its Base
   Sepolia network, x402.org facilitator, `$0.001` price, and rights-holder
   disclosure on screen.
6. Set `RIGHTSRELAY_DB` to one absolute SQLite path used by every process.
7. Use a new database and confirm that the release-packet destination does not
   exist. Do not delete an unfamiliar database or packet during the take.
8. Keep the wall clock and terminal visible for the entire unedited recording.

## Session 1 — producer and ACP reviewer

1. Run `./scripts/demo_session1.sh`.
2. The first `status` shows the process ID, UTC time, commit, database path, and
   empty authorization state.
3. `init-aurora` writes the PENDING authorization.
4. `acp-review` prints the structured entity/requested-use JSON and the real
   on-chain job ID.
5. Keep request → negotiation → escrow → provider delivery → self-evaluation
   visible. The provider terminal must show it handled the job without chat.
6. `acp-review` completes only after it checks that the WARM entity is now
   YouTube, organic, UK, `CLEARED_LIMITED`, with the same `acp_job_id`.
7. The final `status` shows the entity and its COLD `reviewer.acp` event.
8. Record the printed shell PID and kill that shell on screen.

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

If live ACP is unavailable, film `demo_session1_offline.sh` only as the Sibyl
memory proof and omit the Virtuals claim. Do not claim mainnet or third-party
rights/platform integrations. The track is original, and `rightsrelay-demo` is
the rights holder operating the later 402 server.
