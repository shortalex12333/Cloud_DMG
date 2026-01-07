/**
 * Shared Cryptographic Utilities for Edge Functions
 * =================================================
 * Server-side HMAC verification and secret generation.
 * Uses Web Crypto API (native to Deno/Edge Functions).
 */

/**
 * Generate cryptographically secure shared secret.
 * 256-bit (32 bytes) = 64 hex characters
 */
export function generateSharedSecret(): string {
  const bytes = new Uint8Array(32);
  crypto.getRandomValues(bytes);
  return Array.from(bytes).map(b => b.toString(16).padStart(2, '0')).join('');
}

/**
 * Generate secure download token.
 */
export function generateDownloadToken(): string {
  const bytes = new Uint8Array(32);
  crypto.getRandomValues(bytes);
  return Array.from(bytes).map(b => b.toString(16).padStart(2, '0')).join('');
}

/**
 * Compute SHA256 hash of yacht_id.
 */
export async function computeYachtHash(yachtId: string): Promise<string> {
  const encoder = new TextEncoder();
  const data = encoder.encode(yachtId);
  const hashBuffer = await crypto.subtle.digest('SHA-256', data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

/**
 * Verify yacht_id_hash matches yacht_id.
 * Uses constant-time comparison to prevent timing attacks.
 */
export async function verifyYachtHash(yachtId: string, providedHash: string): Promise<boolean> {
  const expected = await computeYachtHash(yachtId);
  return constantTimeCompare(expected.toLowerCase(), providedHash.toLowerCase());
}

/**
 * Verify HMAC-SHA256 request signature.
 *
 * @param sharedSecret - Yacht's shared_secret from database
 * @param payload - Request body as object
 * @param signature - X-Signature header value
 * @param timestamp - X-Timestamp header value
 * @param maxDrift - Maximum allowed timestamp drift in seconds (default: 300 = 5 minutes)
 */
export async function verifyRequestSignature(
  sharedSecret: string,
  payload: Record<string, unknown>,
  signature: string,
  timestamp: string,
  maxDrift: number = 300
): Promise<{ valid: boolean; error?: string }> {
  // Validate timestamp format
  const ts = parseInt(timestamp, 10);
  if (isNaN(ts)) {
    return { valid: false, error: "Invalid timestamp format" };
  }

  // Check timestamp drift
  const now = Math.floor(Date.now() / 1000);
  if (Math.abs(now - ts) > maxDrift) {
    return { valid: false, error: "Timestamp outside acceptable window" };
  }

  // Compute expected signature
  // Canonical format: timestamp:{"key":"value",...} (sorted, no spaces)
  const canonical = `${ts}:${JSON.stringify(payload, Object.keys(payload).sort())}`;

  // Convert hex secret to bytes
  const keyBytes = hexToBytes(sharedSecret);

  // Import key for HMAC
  const key = await crypto.subtle.importKey(
    "raw",
    keyBytes,
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );

  // Compute HMAC
  const encoder = new TextEncoder();
  const signatureBuffer = await crypto.subtle.sign(
    "HMAC",
    key,
    encoder.encode(canonical)
  );

  const expected = Array.from(new Uint8Array(signatureBuffer))
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');

  // Constant-time comparison
  if (!constantTimeCompare(signature.toLowerCase(), expected.toLowerCase())) {
    return { valid: false, error: "Invalid signature" };
  }

  return { valid: true };
}

/**
 * Sign a response payload for client verification.
 */
export async function signResponse(
  sharedSecret: string,
  responseBody: string,
  timestamp: number
): Promise<string> {
  const canonical = `${timestamp}:${responseBody}`;
  const keyBytes = hexToBytes(sharedSecret);

  const key = await crypto.subtle.importKey(
    "raw",
    keyBytes,
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );

  const encoder = new TextEncoder();
  const signatureBuffer = await crypto.subtle.sign(
    "HMAC",
    key,
    encoder.encode(canonical)
  );

  return Array.from(new Uint8Array(signatureBuffer))
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');
}

/**
 * Convert hex string to Uint8Array.
 */
function hexToBytes(hex: string): Uint8Array {
  const bytes = new Uint8Array(hex.length / 2);
  for (let i = 0; i < hex.length; i += 2) {
    bytes[i / 2] = parseInt(hex.substring(i, i + 2), 16);
  }
  return bytes;
}

/**
 * Constant-time string comparison to prevent timing attacks.
 */
function constantTimeCompare(a: string, b: string): boolean {
  if (a.length !== b.length) {
    return false;
  }

  let result = 0;
  for (let i = 0; i < a.length; i++) {
    result |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }

  return result === 0;
}
