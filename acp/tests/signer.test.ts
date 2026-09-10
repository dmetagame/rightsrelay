import { test } from "node:test";
import assert from "node:assert/strict";
import { generateKeyPairSync, sign, verify } from "node:crypto";
import { createKeystoreSigner } from "../signer.js";

test("SDK callback signs the exact payload using the selected public key, without forwarding secrets", async () => {
  const { privateKey, publicKey } = generateKeyPairSync("ec", { namedCurve: "prime256v1" });
  const selector = publicKey.export({ type: "spki", format: "der" }).toString("base64");
  const payload = new Uint8Array([0, 1, 127, 128, 255]);
  // External signer-process boundary only: no SDK, job, or settlement double.
  const callback = createKeystoreSigner(process.execPath, selector, (_binary, args, options) => {
    assert.deepEqual(args, ["sign", "--public-key", selector, "--payload", "00017f80ff"]);
    assert.equal(options.shell, false);
    assert.ok(Object.keys(options.env!).every(name =>
      ["PATH", "HOME", "XDG_DATA_HOME", "XDG_CONFIG_HOME", "DBUS_SESSION_BUS_ADDRESS"].includes(name)));
    return JSON.stringify({ signature: sign("sha256", payload, privateKey).toString("base64") });
  });
  assert.equal(verify("sha256", payload, publicKey, Buffer.from(await callback(payload), "base64")), true);
});

test("callback rejects a signature from another role, malformed output, and executable failures without leaking details", async () => {
  const first = generateKeyPairSync("ec", { namedCurve: "prime256v1" });
  const second = generateKeyPairSync("ec", { namedCurve: "prime256v1" });
  const selector = first.publicKey.export({ type: "spki", format: "der" }).toString("base64");
  const payload = Buffer.from("offline callback contract test");
  const wrongRole = sign("sha256", payload, second.privateKey).toString("base64");
  for (const output of [JSON.stringify({ signature: wrongRole }), '{}', '{"error":"sensitive-output"}',
    'not-json-sensitive-output', '{"signature":123}', '{"signature":"bad-base64"}']) {
    const callback = createKeystoreSigner(process.execPath, selector, () => output);
    await assert.rejects(callback(payload), { message: "Local ACP signer failed (details withheld)" });
  }
  const callback = createKeystoreSigner(process.execPath, selector, () => {
    throw new Error("sensitive executable stderr / payload");
  });
  await assert.rejects(callback(payload), { message: "Local ACP signer failed (details withheld)" });
});

test("invalid signer configuration fails before invoking any executable", () => {
  const { publicKey } = generateKeyPairSync("ec", { namedCurve: "prime256v1" });
  const selector = publicKey.export({ type: "spki", format: "der" }).toString("base64");
  const wrongCurve = generateKeyPairSync("ec", { namedCurve: "secp384r1" })
    .publicKey.export({ type: "spki", format: "der" }).toString("base64");
  for (const [binary, key] of [["relative/signer", selector], ["/missing/rightsrelay-signer", selector],
    [process.execPath, "invalid-key"], [process.execPath, wrongCurve]]) {
    assert.throws(() => createKeystoreSigner(binary!, key!, () => {
      assert.fail("invalid configuration must not run an executable");
    }), { message: "Local ACP signer configuration is invalid" });
  }
});
