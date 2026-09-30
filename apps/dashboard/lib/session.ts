/**
 * Signed session cookie for the dashboard's own login (separate from the
 * API key Candor's backend uses for write endpoints — this gates a human,
 * that gates a calling service). Implemented with Web Crypto (SubtleCrypto)
 * only, so the same code runs unmodified in both the Edge middleware
 * runtime and the Node runtime used by Server Actions.
 */

export const SESSION_COOKIE = "candor_session";

const SESSION_MAX_AGE_MS = 12 * 60 * 60 * 1000; // 12 hours

const encoder = new TextEncoder();

async function getKey(secret: string): Promise<CryptoKey> {
  return crypto.subtle.importKey(
    "raw",
    encoder.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign", "verify"],
  );
}

function toHex(buffer: ArrayBuffer): string {
  return Array.from(new Uint8Array(buffer))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

function requireSecret(): string {
  const secret = process.env.SESSION_SECRET;
  if (!secret) {
    throw new Error("SESSION_SECRET is not set");
  }
  return secret;
}

export async function createSessionToken(username: string): Promise<string> {
  const secret = requireSecret();
  const payload = `${username}.${Date.now()}`;
  const key = await getKey(secret);
  const signature = await crypto.subtle.sign("HMAC", key, encoder.encode(payload));
  return `${payload}.${toHex(signature)}`;
}

export async function verifySessionToken(token: string | undefined): Promise<boolean> {
  if (!token) return false;

  const secret = process.env.SESSION_SECRET;
  if (!secret) return false;

  const parts = token.split(".");
  if (parts.length !== 3) return false;

  const [username, issuedAtRaw, signatureHex] = parts;
  const payload = `${username}.${issuedAtRaw}`;

  const key = await getKey(secret);
  const expectedSignature = await crypto.subtle.sign("HMAC", key, encoder.encode(payload));
  const expectedHex = toHex(expectedSignature);

  if (expectedHex.length !== signatureHex.length) return false;
  let mismatch = 0;
  for (let i = 0; i < expectedHex.length; i += 1) {
    mismatch |= expectedHex.charCodeAt(i) ^ signatureHex.charCodeAt(i);
  }
  if (mismatch !== 0) return false;

  const issuedAt = Number(issuedAtRaw);
  if (Number.isNaN(issuedAt) || Date.now() - issuedAt > SESSION_MAX_AGE_MS) return false;

  return true;
}
