/**
 * HTTP Response Utilities for Edge Functions
 * ===========================================
 * Standardized JSON responses with CORS support.
 */

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type, x-yacht-id, x-timestamp, x-signature",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

/**
 * Success response.
 */
export function success(data: Record<string, unknown>, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      ...CORS_HEADERS,
      "Content-Type": "application/json",
    },
  });
}

/**
 * Error response.
 */
export function error(message: string, status = 400, code?: string): Response {
  const body: Record<string, unknown> = { error: message };
  if (code) body.code = code;

  return new Response(JSON.stringify(body), {
    status,
    headers: {
      ...CORS_HEADERS,
      "Content-Type": "application/json",
    },
  });
}

/**
 * Handle CORS preflight.
 */
export function corsResponse(): Response {
  return new Response(null, {
    status: 204,
    headers: CORS_HEADERS,
  });
}

/**
 * Extract client info from request.
 */
export function getClientInfo(req: Request): {
  ipAddress: string;
  userAgent: string;
} {
  return {
    ipAddress: req.headers.get("x-forwarded-for")?.split(",")[0] || "unknown",
    userAgent: req.headers.get("user-agent") || "unknown",
  };
}

/**
 * Parse JSON body safely.
 */
export async function parseBody<T>(req: Request): Promise<T | null> {
  try {
    return await req.json() as T;
  } catch {
    return null;
  }
}

/**
 * Validate required fields.
 */
export function validateRequired(
  body: Record<string, unknown> | null,
  fields: string[]
): { valid: boolean; missing?: string[] } {
  if (!body) {
    return { valid: false, missing: fields };
  }

  const missing = fields.filter(f => !body[f]);
  return {
    valid: missing.length === 0,
    missing: missing.length > 0 ? missing : undefined,
  };
}
