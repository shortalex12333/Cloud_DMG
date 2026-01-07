/**
 * /check-activation Edge Function
 * ================================
 * Polling endpoint for activation status.
 *
 * CRITICAL SECURITY:
 * - shared_secret is returned EXACTLY ONCE
 * - credentials_retrieved flag is set atomically
 * - Second call NEVER returns secret (returns already_retrieved)
 * - All access attempts logged
 *
 * Flow:
 * 1. Installer polls this endpoint after registration
 * 2. Returns "pending" until owner clicks activation link
 * 3. Once activated, returns shared_secret ONE TIME
 * 4. Subsequent calls return "already_retrieved" with NO secret
 *
 * States:
 * - pending: Waiting for owner activation
 * - active: Activated, shared_secret returned (first call only)
 * - already_retrieved: Secret was already delivered
 * - error: Invalid yacht or security violation
 */

import { serve } from "https://deno.land/std@0.208.0/http/server.ts";
import { FleetRegistry, AuditLog, SecurityEvents, getServiceClient } from "../_shared/db.ts";
import {
  success,
  error,
  corsResponse,
  getClientInfo,
  parseBody,
  validateRequired,
} from "../_shared/response.ts";

interface CheckActivationRequest {
  yacht_id: string;
}

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
    // Parse and validate request
    const body = await parseBody<CheckActivationRequest>(req);
    const validation = validateRequired(body, ["yacht_id"]);

    if (!validation.valid) {
      return error("Missing yacht_id", 400);
    }

    const { yacht_id } = body!;

    // Get yacht from registry
    const yacht = await FleetRegistry.getYacht(yacht_id);

    if (!yacht) {
      await AuditLog.log({
        yachtId: yacht_id,
        action: "check_activation_not_found",
        ...clientInfo,
      });
      return error("Yacht not found", 404);
    }

    // Check current status (using `active` boolean field)
    if (!yacht.active) {
      // Still waiting for owner to activate
      await AuditLog.log({
        yachtId: yacht_id,
        action: "check_activation_pending",
        ...clientInfo,
      });

      return success({
        status: "pending",
        message: "Waiting for owner activation",
      });
    }

    // Yacht is active - check if credentials already retrieved
    if (yacht.credentials_retrieved) {
          // SECURITY: Second retrieval attempt
          await SecurityEvents.log({
            yachtId: yacht_id,
            eventType: "duplicate_credential_retrieval",
            severity: "high",
            details: {
              first_retrieved_at: yacht.credentials_retrieved_at,
              current_ip: clientInfo.ipAddress,
            },
            ...clientInfo,
          });

          await AuditLog.log({
            yachtId: yacht_id,
            action: "check_activation_already_retrieved",
            details: { first_retrieved_at: yacht.credentials_retrieved_at },
            ...clientInfo,
          });

          // NEVER return secret on second attempt
          return success({
            status: "already_retrieved",
            message: "Credentials were already retrieved. Contact support if this is unexpected.",
          });
        }

        // CRITICAL: Atomic retrieval - mark as retrieved BEFORE returning secret
        // This uses a database function to ensure atomicity
        const db = getServiceClient();

        // Call retrieve_credentials function (returns null if already retrieved)
        const { data: retrieveResult, error: retrieveError } = await db.rpc(
          "retrieve_credentials",
          { p_yacht_id: yacht_id }
        );

        if (retrieveError) {
          console.error("Retrieve credentials error:", retrieveError);
          throw retrieveError;
        }

        // Check if retrieval was successful
        if (!retrieveResult || retrieveResult.length === 0) {
          // Race condition: another request got it first
          await SecurityEvents.log({
            yachtId: yacht_id,
            eventType: "credential_retrieval_race",
            severity: "medium",
            ...clientInfo,
          });

          return success({
            status: "already_retrieved",
            message: "Credentials were already retrieved.",
          });
        }

        const result = retrieveResult[0];

        if (result.status === "already_retrieved") {
          return success({
            status: "already_retrieved",
            message: "Credentials were already retrieved.",
          });
        }

        // SUCCESS: Return shared_secret ONE TIME
        await AuditLog.log({
          yachtId: yacht_id,
          action: "credentials_retrieved_success",
          details: { retrieved_at: result.retrieved_at },
          ...clientInfo,
        });

    return success({
      status: "active",
      shared_secret: result.shared_secret,
      retrieved_at: result.retrieved_at,
      message: "Credentials retrieved. Store securely in Keychain.",
    });

  } catch (err) {
    console.error("Check activation error:", err);

    await AuditLog.log({
      action: "check_activation_error",
      details: { error: String(err) },
      ...clientInfo,
    });

    return error("Internal server error", 500);
  }
});
