import { test } from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const runner = fileURLToPath(new URL("../runner.ts", import.meta.url));
function run(environment: NodeJS.ProcessEnv) {
  return spawnSync(process.execPath, ["--import", "tsx", runner, "buyer", "/tmp/rightsrelay-never-created.sqlite"], {
    encoding: "utf8", timeout: 20000, env: { PATH: process.env.PATH, ...environment },
  });
}

test("direct Node entrypoint refuses transactions before SDK authentication", () => {
  const result = run({});
  assert.equal(result.status, 2);
  assert.match(result.stdout, /mainnet transactions are disabled/);
});

test("approved mode still requires explicit wallet configuration", () => {
  const result = run({ RIGHTSRELAY_ACP_ALLOW_TRANSACTIONS: "1" });
  assert.equal(result.status, 2);
  assert.match(result.stdout, /Missing BUYER_AGENT_WALLET_ADDRESS/);
});

test("mainnet mode refuses a missing or invalid monetary cap before wallet creation", () => {
  for (const cap of [undefined, "NaN", "Infinity", "0", "-1"]) {
    const result = run({
      RIGHTSRELAY_ACP_ALLOW_TRANSACTIONS: "1",
      BUYER_AGENT_WALLET_ADDRESS: "0xfd6a60eb9e7acd3bbb613fe932dcdd76861f7882",
      SELLER_AGENT_WALLET_ADDRESS: "0xca8c2b88533d0085404ed46f4101f38997999701",
      ...(cap === undefined ? {} : { RIGHTSRELAY_ACP_MAX_USDC: cap }),
    });
    assert.equal(result.status, 2);
    assert.match(result.stdout, /Invalid RIGHTSRELAY_ACP_MAX_USDC/);
  }
});
