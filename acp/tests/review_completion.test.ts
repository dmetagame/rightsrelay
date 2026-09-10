import { test } from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { processReviewPhase } from "../review_completion.js";
import { assertSubmittedDelivery } from "../delivery.js";

// Offline transport fixture: this never registers, pays, or completes a live job.
const delivery = { entity_name: "campaign-aurora:neon-drive", version: 2,
  status: "CLEARED_LIMITED", channels: ["youtube"], paid: false,
  territories: ["UK"], expires_on: "2026-09-30" };

test("missing API delivery can be evaluated and reported completed without cached state", async () => {
  let evaluations = 0;
  const boundary = {
    apiDeliverable: null,
    recoverDelivery: async () => JSON.stringify(delivery),
    verifyDelivery: (value: unknown) => assert.deepEqual(value, delivery),
    complete: async () => { evaluations++; },
  };
  const submitted = await processReviewPhase({ ...boundary, phase: "SUBMITTED" });
  assert.equal(submitted.phase, "SUBMITTED");
  assert.equal(evaluations, 1);
  // No cached delivery is supplied: COMPLETED must also recover after restart.
  const completed = await processReviewPhase({ ...boundary, phase: "COMPLETED" });
  assert.deepEqual(completed, { phase: "COMPLETED", deliverable: delivery });
  assert.equal(evaluations, 1, "completed jobs must not be evaluated twice");
});

test("a restarted completion worker recovers evidence without evaluating again", () => {
  const result = spawnSync(process.execPath, ["--import", "tsx", "--input-type=module", "-e", `
    import { processReviewPhase } from ${JSON.stringify(new URL('../review_completion.ts', import.meta.url).href)};
    const delivery = JSON.parse(process.env.OFFLINE_DELIVERY);
    const result = await processReviewPhase({phase: 'COMPLETED', apiDeliverable: null,
      recoverDelivery: async () => JSON.stringify(delivery),
      verifyDelivery: value => { if (JSON.stringify(value) !== JSON.stringify(delivery)) throw Error('mismatch'); },
      complete: async () => { throw Error('must not re-evaluate'); }});
    console.log(JSON.stringify({pid: process.pid, ...result}));
  `], {encoding:"utf8", timeout:10000, cwd: new URL("..", import.meta.url),
    env:{PATH:process.env.PATH, OFFLINE_DELIVERY:JSON.stringify(delivery)}});
  assert.equal(result.status, 0, result.stderr);
  const recovered = JSON.parse(result.stdout);
  assert.notEqual(recovered.pid, process.pid);
  assert.equal(recovered.phase, "COMPLETED");
  assert.deepEqual(recovered.deliverable, delivery);
});

test("neither evaluation nor completion is reported when evidence or memory verification fails", async () => {
  for (const phase of ["SUBMITTED", "COMPLETED"] as const) {
    let evaluations = 0;
    const boundary = {
      phase,
      apiDeliverable: null,
      recoverDelivery: async () => assertSubmittedDelivery(78052n,
        "0xca8c2b88533d0085404ed46f4101f38997999701", JSON.stringify(delivery), []),
      verifyDelivery: (_value: unknown) => {},
      complete: async () => { evaluations++; },
    };
    await assert.rejects(processReviewPhase(boundary), /one submitted-delivery event/);
    await assert.rejects(processReviewPhase({ ...boundary,
      apiDeliverable: JSON.stringify(delivery),
      verifyDelivery: () => { throw new Error("Sibyl authorization no longer matches"); },
    }), /no longer matches/);
    await assert.rejects(processReviewPhase({ ...boundary, apiDeliverable: "invalid JSON" }));
    assert.equal(evaluations, 0);
  }
});
