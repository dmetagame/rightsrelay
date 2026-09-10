import { AssetToken, type AcpAgentOffering } from "@virtuals-protocol/acp-node-v2";

export const RIGHTS_REVIEW_OFFERING = "rights_review";
export class OfferingError extends Error {}

/** Select the one registered service, preserving the existing fixed-fare guard. */
export function selectRightsReviewOffering(offerings: AcpAgentOffering[], cap: bigint): AcpAgentOffering {
  const matches = offerings.filter(o => o.name === RIGHTS_REVIEW_OFFERING);
  if (matches.length !== 1) throw new OfferingError("Exactly one registered rights_review offering is required");
  const offering = matches[0];
  if (offering.requiredFunds || offering.subscriptions?.length || offering.priceType.toLowerCase() !== "fixed") {
    throw new OfferingError("Offering must be fixed-price without extra funds or subscriptions");
  }
  if (!Number.isFinite(offering.priceValue) || offering.priceValue <= 0 ||
      AssetToken.usdc(offering.priceValue, 8453).rawAmount > cap) {
    throw new OfferingError("Offering exceeds approved USDC cap");
  }
  if (!Number.isFinite(offering.slaMinutes) || offering.slaMinutes <= 0) throw new OfferingError("Invalid offering SLA");
  return offering;
}
