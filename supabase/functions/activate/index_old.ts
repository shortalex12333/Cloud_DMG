/**
 * /activate Edge Function
 * ========================
 * Activation endpoint called when owner clicks email link.
 *
 * Flow:
 * 1. Owner receives activation email with link containing token
 * 2. Owner clicks link -> /activate?token=xxx
 * 3. Server validates token, generates shared_secret
 * 4. Updates yacht status to 'active'
 * 5. Agent's next poll to /check-activation receives secret
 *
 * Token Security:
 * - Tokens are 256-bit random, stored hashed in database
 * - Single-use, expire after 24 hours
 * - IP logged for security audit
 */

import { serve } from "https://deno.land/std@0.208.0/http/server.ts";
import { generateSharedSecret, computeYachtHash } from "../_shared/crypto.ts";
import { FleetRegistry, AuditLog, SecurityEvents, getServiceClient } from "../_shared/db.ts";
import {
  success,
  error,
  corsResponse,
  getClientInfo,
} from "../_shared/response.ts";

serve(async (req: Request) => {
  // Handle CORS preflight
  if (req.method === "OPTIONS") {
    return corsResponse();
  }

  // Support both GET (email link) and POST (API call)
  const clientInfo = getClientInfo(req);

  try {
    let token: string | null = null;
    let yachtId: string | null = null;

    if (req.method === "GET") {
      // From email link: /activate?token=xxx&yacht_id=xxx
      const url = new URL(req.url);
      token = url.searchParams.get("token");
      yachtId = url.searchParams.get("yacht_id");
    } else if (req.method === "POST") {
      const body = await req.json();
      token = body.token;
      yachtId = body.yacht_id;
    } else {
      return error("Method not allowed", 405);
    }

    if (!token || !yachtId) {
      await AuditLog.log({
        action: "activate_missing_params",
        details: { has_token: !!token, has_yacht_id: !!yachtId },
        ...clientInfo,
      });
      return error("Missing token or yacht_id", 400);
    }

    // Get yacht from registry
    const yacht = await FleetRegistry.getYacht(yachtId);

    if (!yacht) {
      await AuditLog.log({
        yachtId,
        action: "activate_yacht_not_found",
        ...clientInfo,
      });
      return error("Invalid activation link", 404);
    }

    // Check current status (using `active` boolean field)
    if (yacht.active) {
      await AuditLog.log({
        yachtId,
        action: "activate_already_active",
        ...clientInfo,
      });

      // Return success page for already-activated yachts
      if (req.method === "GET") {
        return new Response(
          generateActivationPage(yacht.yacht_name, "already_active"),
          { headers: { "Content-Type": "text/html" } }
        );
      }
      return success({
        status: "already_active",
        message: "This yacht is already activated.",
      });
    }

    // Validate activation token
    const db = getServiceClient();

    // Check download_links table for valid token
    const tokenHash = await computeYachtHash(token); // Hash token for comparison

    const { data: tokenData, error: tokenError } = await db
      .from("download_links")
      .select("*")
      .eq("yacht_id", yachtId)
      .eq("token_hash", tokenHash)
      .eq("used", false)
      .gte("expires_at", new Date().toISOString())
      .single();

    // If no token record, check if it's a simple yacht_id match (dev mode)
    // In production, always require token
    const isDev = Deno.env.get("ENVIRONMENT") === "development";

    if (tokenError || !tokenData) {
      if (!isDev) {
        await SecurityEvents.log({
          yachtId,
          eventType: "invalid_activation_token",
          severity: "high",
          details: { token_hash: tokenHash.substring(0, 16) },
          ...clientInfo,
        });

        await AuditLog.log({
          yachtId,
          action: "activate_invalid_token",
          ...clientInfo,
        });

        return error("Invalid or expired activation link", 401);
      }
      // Dev mode: allow activation without token
      console.log("DEV MODE: Allowing activation without token validation");
    } else {
      // Mark token as used
      await db
        .from("download_links")
        .update({ used: true, used_at: new Date().toISOString() })
        .eq("id", tokenData.id);
    }

    // Generate shared_secret
    const sharedSecret = generateSharedSecret();

    // Call activate_yacht database function
    const { data: activateResult, error: activateError } = await db.rpc(
      "activate_yacht",
      {
        p_yacht_id: yachtId,
        p_shared_secret: sharedSecret,
      }
    );

    if (activateError) {
      console.error("Activate yacht error:", activateError);
      throw activateError;
    }

    // Log successful activation
    await AuditLog.log({
      yachtId,
      action: "activate_success",
      details: {
        yacht_name: yacht.yacht_name,
        buyer_email: yacht.buyer_email,
      },
      ...clientInfo,
    });

    // Return success
    if (req.method === "GET") {
      return new Response(
        generateActivationPage(yacht.yacht_name, "success"),
        { headers: { "Content-Type": "text/html" } }
      );
    }

    return success({
      status: "activated",
      message: "Yacht successfully activated. The installer will complete automatically.",
      yacht_name: yacht.yacht_name,
    });

  } catch (err) {
    console.error("Activate error:", err);

    await AuditLog.log({
      action: "activate_error",
      details: { error: String(err) },
      ...clientInfo,
    });

    return error("Activation failed", 500);
  }
});

/**
 * Generate HTML page for email link clicks.
 */
function generateActivationPage(yachtName: string, status: "success" | "already_active" | "error"): string {
  const messages = {
    success: {
      title: "Activation Successful",
      body: `<strong>${yachtName}</strong> has been activated successfully.<br><br>
             Return to your Mac - the CelesteOS installer will complete automatically.`,
      color: "#10b981",
    },
    already_active: {
      title: "Already Activated",
      body: `<strong>${yachtName}</strong> is already activated.<br><br>
             If you're having issues, contact support.`,
      color: "#f59e0b",
    },
    error: {
      title: "Activation Failed",
      body: `Something went wrong activating <strong>${yachtName}</strong>.<br><br>
             Please try again or contact support.`,
      color: "#ef4444",
    },
  };

  const msg = messages[status];

  return `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>CelesteOS - ${msg.title}</title>
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      margin: 0;
      color: #e2e8f0;
    }
    .container {
      background: rgba(30, 41, 59, 0.8);
      border-radius: 16px;
      padding: 48px;
      text-align: center;
      max-width: 480px;
      box-shadow: 0 25px 50px rgba(0, 0, 0, 0.5);
      border: 1px solid rgba(148, 163, 184, 0.1);
    }
    .icon {
      font-size: 64px;
      margin-bottom: 24px;
    }
    h1 {
      color: ${msg.color};
      margin: 0 0 16px;
      font-size: 28px;
    }
    p {
      color: #94a3b8;
      line-height: 1.6;
      margin: 0;
    }
    .logo {
      opacity: 0.5;
      margin-top: 32px;
      font-size: 14px;
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="icon">${status === "success" ? "✓" : status === "already_active" ? "ℹ" : "✕"}</div>
    <h1>${msg.title}</h1>
    <p>${msg.body}</p>
    <p class="logo">CelesteOS</p>
  </div>
</body>
</html>`;
}
