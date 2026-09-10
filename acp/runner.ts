/** ACP-only transport. The deterministic authorization lives exclusively in Python/Sibyl. */
import { spawnSync } from "node:child_process";
import { setTimeout as delay } from "node:timers/promises";
import { base } from "@account-kit/infra";
import {
  AcpAgent, AssetToken, JobSession, JobStatus, PrivyAlchemyEvmProviderAdapter,
} from "@virtuals-protocol/acp-node-v2";
import { createPublicClient, getAddress, http, parseAbiItem, zeroAddress } from "viem";
import { assertSubmittedDelivery, submissionBlockRange } from "./delivery.js";
import { createKeystoreSigner } from "./signer.js";
import { processReviewPhase } from "./review_completion.js";
import { RIGHTS_REVIEW_OFFERING as offeringName, OfferingError, selectRightsReviewOffering } from "./offering.js";

// Do not forward raw SDK logging: errors may contain signing requests or tokens.
console.log = () => {};
console.warn = () => {};
console.error = () => {};
const emit = (data: object) => process.stdout.write(JSON.stringify(data) + "\n");
const progress = (stage: string) => emit({ type: "progress", stage });
class RelayError extends Error {}
function fail(message: string): never { throw new RelayError(message); }
const chainId = 8453;

function env(name: string): string {
  return process.env[name] || fail(`Missing ${name}`);
}
function positive(name: string, fallback?: string): number {
  const value = Number(process.env[name] ?? fallback);
  if (!Number.isFinite(value) || value <= 0) fail(`Invalid ${name}`);
  return value;
}
function memory(mode: string, request: object = {}): any {
  const cleanEnv = Object.fromEntries(
    ["PATH", "HOME", "PYTHONPATH"].filter(k => process.env[k]).map(k => [k, process.env[k]!]),
  );
  const result = spawnSync(env("RIGHTSRELAY_PYTHON"),
    ["-m", "rightsrelay.acp_bridge", mode, process.argv[3]],
    { input: JSON.stringify(request), encoding: "utf8", env: cleanEnv, timeout: 15000, maxBuffer: 65536 });
  if (result.error || result.status !== 0) fail("Sibyl memory refused the ACP operation");
  return JSON.parse(result.stdout);
}
function validId(id: string): void {
  if (!/^[1-9][0-9]*$/.test(id)) fail("Invalid onchain job ID");
}
async function main(): Promise<void> {
  // This guard precedes SDK initialization, authentication, and any transaction.
  if (process.env.RIGHTSRELAY_ACP_ALLOW_TRANSACTIONS !== "1") fail("ACP mainnet transactions are disabled");
  const role = process.argv[2];
  if (!['buyer', 'provider'].includes(role) || !process.argv[3]) fail("Expected buyer|provider and database path");
  const buyerAddress = getAddress(env("BUYER_AGENT_WALLET_ADDRESS"));
  const sellerAddress = getAddress(env("SELLER_AGENT_WALLET_ADDRESS"));
  if (buyerAddress === sellerAddress) fail("Buyer and provider wallets must differ");
  const capValue = positive("RIGHTSRELAY_ACP_MAX_USDC");
  const cap = AssetToken.usdc(capValue, chainId).rawAmount;
  if (cap <= 0n) fail("USDC cap is below token precision");
  const timeout = positive("RIGHTSRELAY_ACP_TIMEOUT_SECONDS", "300") * 1000;
  const poll = positive("RIGHTSRELAY_ACP_POLL_SECONDS", "5") * 1000;
  const initial = memory("inspect");
  const prefix = role === "buyer" ? "BUYER" : "SELLER";
  const provider = await PrivyAlchemyEvmProviderAdapter.create({
    walletAddress: role === "buyer" ? buyerAddress : sellerAddress,
    walletId: env(`${prefix}_WALLET_ID`),
    signFn: createKeystoreSigner(env("RIGHTSRELAY_ACP_SIGNER_BINARY"), env(`${prefix}_SIGNER_PUBLIC_KEY`)),
    chains: [base],
  });
  const agent = await AcpAgent.create({ evmProvider: provider });
  const client = agent.getClient(chainId);
  const contract = client.getContractAddress(chainId);
  const explorer = `https://basescan.org/address/${getAddress(contract)}`;
  progress(`Base mainnet (${chainId}); ACP contract ${explorer}`);
  const me = await agent.getAddress();
  if (getAddress(me) !== (role === "buyer" ? buyerAddress : sellerAddress)) fail("SDK wallet mismatch");
  let stopping = false;
  const shutdown = () => { stopping = true; };
  process.once("SIGTERM", shutdown);
  process.once("SIGINT", shutdown);
  try {
    const seller = await agent.getAgentByWalletAddress(sellerAddress);
    if (!seller || getAddress(seller.walletAddress) !== sellerAddress) fail("Reviewer registration not found");
    const offering = selectRightsReviewOffering(seller.offerings, cap);
    const fare = AssetToken.usdc(offering.priceValue, chainId);
    progress(`Registered ${offeringName} price: ${offering.priceValue} USDC; cap: ${capValue} USDC (gas separate)`);
    // SDK hydration is read-only. No automatic handler can spend on unrelated jobs.
    await agent.start();

    async function readSession(id: string): Promise<JobSession> {
      validId(id);
      const session = agent.getSession(chainId, id) ?? new JobSession(
        agent, [me], id, chainId, role === "buyer" ? ["client", "evaluator"] : ["provider"],
      );
      await session.fetchJob();
      return session;
    }
    async function checkJob(session: JobSession) {
      const job = await client.getJob(chainId, BigInt(session.jobId));
      if (!job || getAddress(job.client) !== buyerAddress || getAddress(job.provider) !== sellerAddress ||
          getAddress(job.evaluator) !== buyerAddress || job.description !== offeringName ||
          getAddress(job.hook) !== zeroAddress) fail("Onchain job is outside the approved review scope");
      if (job.budget < 0n || job.budget > cap || (job.budget !== 0n && job.budget !== fare.rawAmount)) {
        fail("Onchain budget differs from the approved registered fare");
      }
      const offchain = session.job!;
      if (offchain.getFundRequestIntent() || offchain.getFundTransferIntent() || offchain.clientSubscription ||
          getAddress(offchain.hookAddress) !== zeroAddress) fail("Extra funds/hooks are outside scope");
      return job;
    }
    async function checkRequirement(id: string): Promise<boolean> {
      // Only structured ACP requirements enter the memory bridge. Never pass a
      // room transcript, free text, toContext(), or toMessages() to the reviewer.
      const entries = await agent.getTransport().getHistory(chainId, id);
      const requests = entries.filter(e => e.kind === "message" && e.contentType === "requirement" &&
        getAddress(e.from) === buyerAddress);
      if (!requests.length) return false; // Registry indexing can lag job creation.
      for (const entry of requests) {
        if (entry.kind !== "message" || entry.packageId !== undefined) fail("Subscriptions are outside scope");
        memory("validate", { job_id: id, requirement: JSON.parse(entry.content) });
      }
      return true;
    }
    async function recoverSubmittedDelivery(id: string): Promise<string> {
      const expected = memory("delivery", { job_id: id });
      const serialized = JSON.stringify(expected);
      const rpc = createPublicClient({
        chain: base,
        transport: http(base.rpcUrls.default.http[0], { timeout: 15000, retryCount: 2 }),
      });
      const head = await rpc.getBlockNumber();
      const logs = await rpc.getLogs({
        address: getAddress(contract),
        event: parseAbiItem(
          "event JobSubmitted(uint256 indexed jobId, address indexed provider, bytes32 deliverable)",
        ),
        args: { jobId: BigInt(id) },
        ...submissionBlockRange(head, process.env.RIGHTSRELAY_ACP_SUBMISSION_BLOCK || undefined),
      });
      if (!logs.length) fail("No submission event in lookup window; for an older job set RIGHTSRELAY_ACP_SUBMISSION_BLOCK to its verified submission block");
      return assertSubmittedDelivery(BigInt(id), sellerAddress, serialized, logs);
    }

    if (role === "provider") {
      progress(`Provider ready; pid ${process.pid}; shared Sibyl entity only`);
      const finished = new Set<string>();
      while (!stopping) {
        const active = await agent.getApi().getActiveJobs();
        for (const record of active) {
          if (record.chainId !== chainId || finished.has(record.onChainJobId)) continue;
          const session = await readSession(record.onChainJobId);
          const offchain = session.job!;
          if (getAddress(offchain.clientAddress) !== buyerAddress || getAddress(offchain.providerAddress) !== sellerAddress ||
              offchain.description !== offeringName) continue;
          const job = await checkJob(session);
          if ([JobStatus.COMPLETED, JobStatus.REJECTED, JobStatus.EXPIRED].includes(job.status)) {
            finished.add(session.jobId); continue;
          }
          if (job.status === JobStatus.OPEN || job.status === JobStatus.FUNDED) {
            if (!await checkRequirement(session.jobId)) continue;
          }
          if (job.status === JobStatus.OPEN && job.budget === 0n) {
            await session.setBudget(fare);
            progress(`Job ${session.jobId}: negotiated ${offering.priceValue} USDC escrow`);
          } else if (job.status === JobStatus.FUNDED) {
            const deliverable = memory("apply", { job_id: session.jobId });
            await session.submit(JSON.stringify(deliverable));
            progress(`Job ${session.jobId}: Sibyl CLEARED_LIMITED; structured delivery submitted`);
          }
        }
        await delay(poll);
      }
      return;
    }

    let id = process.env.RIGHTSRELAY_ACP_RESUME_JOB_ID;
    const active = await agent.getApi().getActiveJobs();
    // Conservative: do not pile up jobs or silently spend on a resumed job.
    if (!id && active.some(j => j.chainId === chainId)) fail("Active Base job exists; inspect it and explicitly set RIGHTSRELAY_ACP_RESUME_JOB_ID");
    if (!id) {
      if (initial.status !== "PENDING" || initial.acp_job_id !== null) fail("Initialize PENDING memory before a new review");
      progress("Request: campaign-aurora:neon-drive; YouTube organic UK");
      id = (await agent.createJobFromOffering(chainId, offering, sellerAddress,
        initial.requirement, { evaluatorAddress: buyerAddress })).toString();
      progress(`Job ${id}: created; self-evaluation enabled`);
    }
    validId(id);
    const deadline = Date.now() + timeout;
    let funded = false;
    let evaluated = false;
    while (!stopping && Date.now() < deadline) {
      const session = await readSession(id);
      const job = await checkJob(session);
      if (!await checkRequirement(id)) { await delay(poll); continue; }
      if (job.status === JobStatus.OPEN && job.budget > 0n && !funded) {
        // Pass the checked amount explicitly; the contract checks expectedBudget.
        await session.fund(fare);
        funded = true;
        progress(`Job ${id}: ${offering.priceValue} USDC escrow funded`);
      } else if ((job.status === JobStatus.SUBMITTED && !evaluated) || job.status === JobStatus.COMPLETED) {
        const result = await processReviewPhase({
          phase: job.status === JobStatus.COMPLETED ? "COMPLETED" : "SUBMITTED",
          apiDeliverable: session.job!.deliverable,
          recoverDelivery: async () => {
            const recovered = await recoverSubmittedDelivery(id);
            progress(`Job ${id}: API delivery missing; onchain hash verified`);
            return recovered;
          },
          verifyDelivery: deliverable => { memory("verify", { job_id: id, deliverable }); },
          complete: () => session.complete("Self-evaluation: delivery equals the persisted Sibyl authorization"),
        });
        if (result.phase === "COMPLETED") {
          emit({ type: "result", job_id: id, phase: "COMPLETED", contract_explorer_url: explorer, deliverable: result.deliverable });
          return;
        }
        evaluated = true;
        progress(`Job ${id}: memory verified; evaluation accepted`);
      } else if ([JobStatus.REJECTED, JobStatus.EXPIRED].includes(job.status)) {
        fail(`Job ${id} rejected or expired; no successful review claimed`);
      }
      await delay(poll);
    }
    fail(`Job ${id}: stopped or timed out; inspect escrow before resuming`);
  } finally {
    await agent.stop();
  }
}

main().catch(error => {
  emit({ type: "progress", stage: error instanceof RelayError || error instanceof OfferingError ? error.message : "ACP SDK operation failed (sensitive details withheld)" });
  process.exitCode = 2;
});
