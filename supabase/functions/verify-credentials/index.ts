/**
 * /verify-credentials Edge Function
 * ==================================
 * Verifies HMAC-signed requests from installed agents.
 *
 * All subsequent API calls after activation use this pattern:
 * - Client signs request body with HMAC-SHA256(payload, shared_secret)
 * - Headers: X-Yacht-ID, X-Timestamp, X-Signature
 * - Server verifies signature using stored shared_secret
 *
 * This endpoint is used for:
 * 1. Initial credential verification after Keychain storage
 * 2. Health checks to confirm agent is still authorized
 * 3. As a template for all authenticated endpoints
 *
 * Security:
 * - Timestamp must be within 5 minutes (replay attack prevention)
 * - Signature uses constant-time comparison (timing attack prevention)
 * - Failed attempts logged with rate limiting consideration
 */

import { serve } from "https://deno.land/std@0.208.0/http/server.ts";
import { verifyRequestSignature } from "../_shared/crypto.ts";
import { FleetRegistry, AuditLog, SecurityEvents } from "../_shared/db.ts";
import {
  success,
  error,
  corsResponse,
  getClientInfo,
  parseBody,
} from "../_shared/response.ts";

serve(async (req: Request) => {
  // Handle CORS preflight
  if (req.method === "OPTIONS") {
    return corsResponse();
  }

  if (req.method !== "POST") {
    return error("Method not allowed", 405);
  }

  const clientInfo = getClientInfo(req);

  try {
    // Extract authentication headers
    const yachtId = req.headers.get("X-Yacht-ID");
    const timestamp = req.headers.get("X-Timestamp");
    const signature = req.headers.get("X-Signature");

    if (!yachtId || !timestamp || !signature) {
      await AuditLog.log({
        action: "verify_missing_headers",
        details: {
          has_yacht_id: !!yachtId,
          has_timestamp: !!timestamp,
          has_signature: !!signature,
        },
        ...clientInfo,
      });

      return error("Missing authentication headers", 401, "MISSING_AUTH");
    }

    // Parse request body
    const body = await parseBody<Record<string, unknown>>(req);

    if (!body) {
      return error("Invalid request body", 400);
    }

    // Get yacht from registry
    const yacht = await FleetRegistry.getYacht(yachtId);

    if (!yacht) {
      await AuditLog.log({
        yachtId,
        action: "verify_yacht_not_found",
        ...clientInfo,
      });

      // Don't reveal yacht existence
      return error("Authentication failed", 401, "AUTH_FAILED");
    }

    // Check yacht has been activated
    if (!yacht.shared_secret) {
      await AuditLog.log({
        yachtId,
        action: "verify_not_activated",
        ...clientInfo,
      });

      return error("Yacht not activated", 401, "NOT_ACTIVATED");
    }

    // Verify HMAC signature
    const verification = await verifyRequestSignature(
      yacht.shared_secret,
      body,
      signature,
      timestamp
    );

    if (!verification.valid) {
      // Log security event for failed verification
      await SecurityEvents.log({
        yachtId,
        eventType: "signature_verification_failed",
        severity: "medium",
        details: {
          error: verification.error,
          timestamp,
          action: body.action,
        },
        ...clientInfo,
      });

      await AuditLog.log({
        yachtId,
        action: "verify_signature_failed",
        details: { error: verification.error },
        ...clientInfo,
      });

      return error("Authentication failed", 401, "AUTH_FAILED");
    }

    // Signature verified - update last seen
    await FleetRegistry.updateStatus(yachtId, "operational");

    await AuditLog.log({
      yachtId,
      action: "verify_success",
      details: { requested_action: body.action },
      ...clientInfo,
    });

    // Return success with yacht info
    return success({
      status: "verified",
      yacht_id: yachtId,
      yacht_name: yacht.yacht_name,
      yacht_active: yacht.active,
      message: "Credentials verified successfully",
    });

  } catch (err) {
    console.error("Verify credentials error:", err);

    await AuditLog.log({
      action: "verify_error",
      details: { error: String(err) },
      ...clientInfo,
    });

    return error("Internal server error", 500);
  }
});
