import { test } from "node:test";
import assert from "node:assert/strict";
import type { AcpAgentOffering } from "@virtuals-protocol/acp-node-v2";
import { selectRightsReviewOffering } from "../offering.js";

// Registry input fixture, not a job or a fabricated settlement.
const registered: AcpAgentOffering = {
  name: "rights_review", priceType: "fixed", priceValue: 0.01,
  slaMinutes: 20, requiredFunds: false, subscriptions: [],
  description: "Review the shared Sibyl authorization", requirements: {}, deliverable: {},
  isHidden: false, isPrivate: false,
};

test("selects the exact registered rights_review offering and rejects the old label or ambiguous registration", () => {
  const oldName = { ...registered, name: "Rights review" };
  assert.equal(selectRightsReviewOffering([oldName, registered], 10000n), registered);
  for (const offerings of [[], [oldName], [registered, { ...registered }]]) {
    assert.throws(() => selectRightsReviewOffering(offerings, 10000n), /Exactly one registered rights_review/);
  }
});

test("exact-name matching preserves fee cap, fixed price, no extra funds, and valid SLA restrictions", () => {
  for (const change of [
    { priceValue: 0.02 }, { priceValue: NaN }, { priceValue: 0 }, { priceValue: -1 },
    { priceType: "percentage" }, { requiredFunds: true }, { slaMinutes: 0 },
    { subscriptions: [{ packageId: 5, name: "out of scope", price: 1, duration: 7 }] },
  ]) {
    assert.throws(() => selectRightsReviewOffering([{ ...registered, ...change }], 10000n));
  }
});
