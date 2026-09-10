import { execFileSync, type ExecFileSyncOptionsWithStringEncoding } from "node:child_process";
import { createPublicKey, verify } from "node:crypto";
import { accessSync, constants, statSync } from "node:fs";
import { isAbsolute } from "node:path";

type SignerProcess = (
  binary: string, args: string[], options: ExecFileSyncOptionsWithStringEncoding,
) => string;

/** Official acp-cli signer protocol; private keys remain in local storage. */
export function createKeystoreSigner(
  binary: string, publicKey: string, execute: SignerProcess = execFileSync,
): (payload: Uint8Array) => Promise<string> {
  let verificationKey;
  try {
    if (!isAbsolute(binary) || !statSync(binary).isFile()) throw new Error();
    accessSync(binary, constants.X_OK);
    const der = Buffer.from(publicKey, "base64");
    if (der.toString("base64") !== publicKey) throw new Error();
    verificationKey = createPublicKey({ key: der, type: "spki", format: "der" });
    if (verificationKey.asymmetricKeyType !== "ec" ||
        verificationKey.asymmetricKeyDetails?.namedCurve !== "prime256v1") throw new Error();
  } catch {
    throw new Error("Local ACP signer configuration is invalid");
  }
  const environment = Object.fromEntries(
    ["PATH", "HOME", "XDG_DATA_HOME", "XDG_CONFIG_HOME", "DBUS_SESSION_BUS_ADDRESS"]
      .filter(name => process.env[name] !== undefined).map(name => [name, process.env[name]!]),
  );
  return async payload => {
    try {
      const result = JSON.parse(execute(binary,
        ["sign", "--public-key", publicKey, "--payload", Buffer.from(payload).toString("hex")],
        { encoding: "utf8", shell: false, stdio: ["ignore", "pipe", "pipe"],
          env: environment, timeout: 10000, maxBuffer: 8192 }));
      if (!result || result.error || typeof result.signature !== "string") throw new Error();
      const signature = Buffer.from(result.signature, "base64");
      if (signature.toString("base64") !== result.signature ||
          !verify("sha256", payload, verificationKey, signature)) throw new Error();
      return result.signature;
    } catch {
      // exec errors can contain raw argv/payload/stdout/stderr. Never preserve a cause.
      throw new Error("Local ACP signer failed (details withheld)");
    }
  };
}
