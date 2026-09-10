import { test } from "node:test";
import assert from "node:assert/strict";
import { assertSubmittedDelivery, DeliveryEvidenceError, submissionBlockRange } from "../delivery.js";

const reviewer = "0xca8c2b88533d0085404ed46f4101f38997999701";
const deliverable = JSON.stringify({
  channels: ["youtube"],
  entity_name: "campaign-aurora:neon-drive",
  expires_on: "2026-09-30",
  paid: false,
  status: "CLEARED_LIMITED",
  territories: ["UK"],
  version: 2,
});
const liveHash = "0x74d28ea02f01179fa849cd66479bb64d05f7c3f50e0049de8fe6ff054af393d7";
const matching = { args: { jobId: 78052n, provider: reviewer, deliverable: liveHash } };

test("an explicit historical submission block permits bounded recovery after a long restart", () => {
  assert.deepEqual(submissionBlockRange(60000000n, "51120400"),
    { fromBlock: 51120400n, toBlock: 51120400n });
  assert.deepEqual(submissionBlockRange(60000000n),
    { fromBlock: 59998001n, toBlock: 60000000n });
  for (const value of ["", "-1", "1.5", "Infinity", "60000001", "001"])
    assert.throws(() => submissionBlockRange(60000000n, value), DeliveryEvidenceError);
});

test("missing API delivery is recovered only from one matching onchain submission", () => {
  assert.equal(assertSubmittedDelivery(78052n, reviewer, deliverable, [matching]), deliverable);

  for (const evidence of [
    [],
    [matching, matching],
    [{ args: { ...matching.args, jobId: 78053n } }],
    [{ args: { ...matching.args, provider: "0xfd6a60eb9e7acd3bbb613fe932dcdd76861f7882" } }],
    [{ args: { ...matching.args, deliverable: `0x${"00".repeat(32)}` } }],
  ]) {
    assert.throws(
      () => assertSubmittedDelivery(78052n, reviewer, deliverable, evidence),
      DeliveryEvidenceError,
    );
  }
});
