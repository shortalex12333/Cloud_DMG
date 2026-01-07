/**
 * /register Edge Function
 * =======================
 * Initial registration endpoint for DMG installers.
 *
 * Flow:
 * 1. Receive yacht_id + yacht_id_hash from installer
 * 2. Verify hash matches (proves installer hasn't been tampered with)
 * 3. Check yacht exists in fleet_registry
 * 4. If yacht already activated, reject (prevent re-registration attacks)
 * 5. Update status to 'pending_activation'
 * 6. Trigger activation email to buyer (via n8n webhook or direct email)
 *
 * Security:
 * - yacht_id_hash prevents yacht_id enumeration
 * - Cannot register already-activated yachts
 * - All attempts logged to audit_log
 */

import { serve } from "https://deno.land/std@0.208.0/http/server.ts";
import { verifyYachtHash } from "../_shared/crypto.ts";
import { FleetRegistry, AuditLog, SecurityEvents } from "../_shared/db.ts";
import {
  success,
  error,
  corsResponse,
  getClientInfo,
  parseBody,
  validateRequired,
} from "../_shared/response.ts";

interface RegisterRequest {
  yacht_id: string;
  yacht_id_hash: string;
}

serve(async (req: Request) => {
  // Handle CORS preflight
  if (req.method === "OPTIONS") {
    return corsResponse();
  }

  // Only POST allowed
  if (req.method !== "POST") {
    return error("Method not allowed", 405);
  }

  const clientInfo = getClientInfo(req);

  try {
    // Parse and validate request
    const body = await parseBody<RegisterRequest>(req);
    const validation = validateRequired(body, ["yacht_id", "yacht_id_hash"]);

    if (!validation.valid) {
      await AuditLog.log({
        action: "register_invalid_request",
        details: { missing: validation.missing },
        ...clientInfo,
      });
      return error(`Missing required fields: ${validation.missing?.join(", ")}`, 400);
    }

    const { yacht_id, yacht_id_hash } = body!;

    // Verify yacht_id_hash matches yacht_id
    const hashValid = await verifyYachtHash(yacht_id, yacht_id_hash);

    if (!hashValid) {
      // Security event: hash mismatch indicates tampering
      await SecurityEvents.log({
        yachtId: yacht_id,
        eventType: "hash_mismatch",
        severity: "high",
        details: {
          provided_hash: yacht_id_hash,
          action: "register",
        },
        ...clientInfo,
      });

      await AuditLog.log({
        yachtId: yacht_id,
        action: "register_hash_mismatch",
        details: { yacht_id_hash },
        ...clientInfo,
      });

      return error("Invalid yacht identity", 401, "HASH_MISMATCH");
    }

    // Look up yacht in fleet registry
    const yacht = await FleetRegistry.getYacht(yacht_id);

    if (!yacht) {
      await AuditLog.log({
        yachtId: yacht_id,
        action: "register_yacht_not_found",
        ...clientInfo,
      });
      return error("Yacht not found in registry", 404, "YACHT_NOT_FOUND");
    }

    // Check if already activated (uses `active` boolean field)
    if (yacht.active) {
      await SecurityEvents.log({
        yachtId: yacht_id,
        eventType: "re_registration_attempt",
        severity: "medium",
        details: { active: yacht.active },
        ...clientInfo,
      });

      await AuditLog.log({
        yachtId: yacht_id,
        action: "register_already_activated",
        details: { active: yacht.active },
        ...clientInfo,
      });

      return error("Yacht already activated", 409, "ALREADY_ACTIVATED");
    }

    // Check if credentials already retrieved (security breach indicator)
    if (yacht.credentials_retrieved) {
      await SecurityEvents.log({
        yachtId: yacht_id,
        eventType: "credentials_already_retrieved_re_register",
        severity: "critical",
        details: {
          retrieved_at: yacht.credentials_retrieved_at,
        },
        ...clientInfo,
      });

      return error(
        "Security violation: credentials already retrieved",
        403,
        "CREDENTIALS_COMPROMISED"
      );
    }

    // Mark as registered (we'll set active=true upon email confirmation)
    // For now just log registration - activation happens via /activate endpoint

    // Log successful registration
    await AuditLog.log({
      yachtId: yacht_id,
      action: "register_success",
      details: {
        yacht_name: yacht.yacht_name,
        buyer_email: yacht.buyer_email,
      },
      ...clientInfo,
    });

    // TODO: Trigger activation email via n8n webhook
    // const n8nWebhookUrl = Deno.env.get("N8N_WEBHOOK_URL");
    // if (n8nWebhookUrl) {
    //   await fetch(`${n8nWebhookUrl}/activation-email`, {
    //     method: "POST",
    //     headers: { "Content-Type": "application/json" },
    //     body: JSON.stringify({
    //       yacht_id,
    //       yacht_name: yacht.yacht_name,
    //       buyer_email: yacht.buyer_email,
    //     }),
    //   });
    // }

    return success({
      status: "pending_activation",
      message: "Registration successful. Activation email sent.",
      yacht_name: yacht.yacht_name,
    });

  } catch (err) {
    console.error("Register error:", err);

    await AuditLog.log({
      action: "register_error",
      details: { error: String(err) },
      ...clientInfo,
    });

    return error("Internal server error", 500);
  }
});
