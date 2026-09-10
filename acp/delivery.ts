import { getAddress, keccak256, toHex } from "viem";

export class DeliveryEvidenceError extends Error {}

/** A caller-supplied block narrows the lookup; it never bypasses log verification. */
export function submissionBlockRange(head: bigint, supplied?: string): { fromBlock: bigint; toBlock: bigint } {
  if (supplied !== undefined) {
    if (!/^(0|[1-9][0-9]*)$/.test(supplied) || BigInt(supplied) > head)
      throw new DeliveryEvidenceError("Invalid RIGHTSRELAY_ACP_SUBMISSION_BLOCK");
    return { fromBlock: BigInt(supplied), toBlock: BigInt(supplied) };
  }
  return { fromBlock: head > 1999n ? head - 1999n : 0n, toBlock: head };
}

/** Verify the exact structured delivery against one decoded JobSubmitted log. */
export function assertSubmittedDelivery(
  jobId: bigint,
  providerAddress: string,
  serializedDeliverable: string,
  logs: readonly unknown[],
): string {
  if (logs.length !== 1) throw new DeliveryEvidenceError("Expected one submitted-delivery event");
  const log = logs[0] as {
    args?: { jobId?: unknown; provider?: unknown; deliverable?: unknown };
  };
  try {
    if (log.args?.jobId !== jobId ||
        typeof log.args.provider !== "string" ||
        getAddress(log.args.provider) !== getAddress(providerAddress) ||
        typeof log.args.deliverable !== "string" ||
        log.args.deliverable !== keccak256(toHex(serializedDeliverable))) {
      throw new DeliveryEvidenceError("Submitted delivery does not match the approved job");
    }
  } catch (error) {
    if (error instanceof DeliveryEvidenceError) throw error;
    throw new DeliveryEvidenceError("Submitted delivery evidence is invalid");
  }
  return serializedDeliverable;
}
