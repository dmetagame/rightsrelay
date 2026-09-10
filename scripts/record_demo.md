# RightsRelay — 4:00 unedited take

Use one absolute `RIGHTSRELAY_DB` path in every process. Start the x402 seller
before recording. Start the ACP provider only after its wallet IDs, public signer
selectors, official signer-binary path, explicit mainnet transaction approval,
and approved USDC cap are set. The exact registered service is `rights_review`.
ACP is Base mainnet; the later x402 purchase remains Base Sepolia. Keep a terminal
beside the board so the real process kill is visible.

## Shot list

**0:00–0:20 — provenance and empty state**

- Run `./scripts/demo_session1.sh` for live ACP, or
  `./scripts/demo_session1_offline.sh` when ACP registration is unavailable.
- Open `http://127.0.0.1:8080`. Hold the updating UTC clock, commit hash,
  launcher PID, database path, entity name, and `packet: none`. An empty database
  correctly shows `BLOCKED` (missing authorization); Init Aurora makes it `PENDING`.

**0:20–1:10 — write and review**

- Click **Init Aurora**.
- With live ACP, click **ACP review** and keep the real job/escrow output visible.
- Without live ACP prerequisites, click **Review (offline)** and say exactly:
  “Reviewer is local this take; completed Base mainnet ACP proof is job 78052,
  using the same Sibyl write path.” Never imply that the local review created
  an ACP job.

**1:10–1:20 — limited authorization**

- Hold `CLEARED_LIMITED`, YouTube, paid no, UK, September 30, the journal row,
  and the real `acp_job_id` or `none`.

**1:20–1:30 — real process death**

- In the visible terminal run `kill <LAUNCHER_PID>` using the PID on the board.
- Show that the console process stops. This is not a UI reset.
- Hold the disconnected board's `UNVERIFIED` state and stopped clock.

**1:30–1:50 — fresh launcher recall**

- Run `./scripts/demo_session2.sh` and reload the board (the new process rotates
  its local action token; an old page cannot authorize actions).
- Hold the different launcher PID and the same recalled `CLEARED_LIMITED`
  entity. There is no chat transcript.

**1:50–2:20 — hard block**

- Click **Attempt paid IG US+UK**.
- Hold the red `BLOCKED` state, channel/paid/US reasons, and `packet: none`.

**2:20–3:10 — scoped x402 purchase**

- Click **Acquire grant (x402)**.
- Keep the command output visible through HTTP 402, payment, paid retry, and
  HTTP 200. Show the actual settlement identifier. A BaseScan transaction link
  appears only if the facilitator returned a real transaction hash.
- Hold the updated paid/Instagram/US+UK authorization.

**3:10–3:30 — identical request clears**

- Click **Attempt again**. This is the same paid Instagram US+UK attempt.
- Hold the green `CLEARED` state and the written release-packet path.

**3:30–4:00 — proof frame**

- End on the authorization scope, final journal rows, real `acp_job_id` or
  `none`, actual `x402_tx` or settlement identifier, and packet path.
- If the take uses the offline reviewer, show completed ACP job `78052`
  separately as dated partner evidence; do not present the offline button as
  the live job lifecycle.
- Say: “RightsRelay is release operations, not legal advice. We own Neon Drive,
  operate its demo rights-holder endpoint, and this payment is Base Sepolia.”
