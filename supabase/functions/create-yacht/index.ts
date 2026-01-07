/**
 * /create-yacht Edge Function
 * ============================
 * Admin endpoint to create new yacht entries in fleet_registry.
 *
 * Replaces manual SQL insertion with proper validation and error handling.
 *
 * Authentication: Requires service role key (admin only)
 *
 * Request Body:
 * {
 *   "yacht_name": "M/Y Example",
 *   "yacht_model": "Sunseeker 90",
 *   "buyer_name": "John Doe",
 *   "buyer_email": "john@example.com",
 *   "yacht_id": "YACHT_12345" (optional - auto-generated if not provided)
 * }
 *
 * Response:
 * {
 *   "success": true,
 *   "yacht_id": "YACHT_12345",
 *   "yacht_id_hash": "abc123...",
 *   "created_at": "2025-11-25T..."
 * }
 */

import { serve } from "https://deno.land/std@0.208.0/http/server.ts";
import { computeYachtHash } from "../_shared/crypto.ts";
import { AuditLog, getServiceClient } from "../_shared/db.ts";
import {
  success,
  error,
  corsResponse,
  getClientInfo,
} from "../_shared/response.ts";

// Email validation regex
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

// Yacht ID validation regex (alphanumeric, dash, underscore only)
const YACHT_ID_REGEX = /^[A-Z0-9_-]+$/;

interface CreateYachtRequest {
  yacht_name: string;
  yacht_model?: string;
  buyer_name: string;
  buyer_email: string;
  yacht_id?: string;
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
    // Verify service role authentication
    const authHeader = req.headers.get("Authorization");
    if (!authHeader || !authHeader.includes("service_role")) {
      await AuditLog.log({
        action: "create_yacht_unauthorized",
        details: { auth_header: authHeader ? "present" : "missing" },
        ...clientInfo,
      });
      return error("Unauthorized - Admin access required", 401);
    }

    // Parse request body
    const body: CreateYachtRequest = await req.json();

    // Validate required fields
    const errors: string[] = [];

    if (!body.yacht_name || body.yacht_name.trim().length === 0) {
      errors.push("yacht_name is required");
    } else if (body.yacht_name.length > 100) {
      errors.push("yacht_name too long (max 100 characters)");
    }

    if (!body.buyer_name || body.buyer_name.trim().length === 0) {
      errors.push("buyer_name is required");
    } else if (body.buyer_name.length > 100) {
      errors.push("buyer_name too long (max 100 characters)");
    }

    if (!body.buyer_email || body.buyer_email.trim().length === 0) {
      errors.push("buyer_email is required");
    } else if (!EMAIL_REGEX.test(body.buyer_email)) {
      errors.push("buyer_email is not a valid email address");
    }

    if (body.yacht_model && body.yacht_model.length > 100) {
      errors.push("yacht_model too long (max 100 characters)");
    }

    // Validate or generate yacht_id
    let yachtId: string;
    if (body.yacht_id) {
      // User provided yacht_id - validate it
      if (!YACHT_ID_REGEX.test(body.yacht_id)) {
        errors.push("yacht_id must contain only A-Z, 0-9, dash, and underscore");
      } else if (body.yacht_id.length > 50) {
        errors.push("yacht_id too long (max 50 characters)");
      } else {
        yachtId = body.yacht_id.toUpperCase();
      }
    } else {
      // Auto-generate yacht_id from yacht_name + timestamp
      const safeName = body.yacht_name
        .toUpperCase()
        .replace(/[^A-Z0-9]/g, "_")
        .substring(0, 20);
      const timestamp = Date.now().toString().slice(-6);
      yachtId = `${safeName}_${timestamp}`;
    }

    if (errors.length > 0) {
      await AuditLog.log({
        action: "create_yacht_validation_failed",
        details: { errors },
        ...clientInfo,
      });
      return error(`Validation failed: ${errors.join(", ")}`, 400);
    }

    const db = getServiceClient();

    // Check if yacht_id already exists
    const { data: existingYacht } = await db
      .from("fleet_registry")
      .select("yacht_id")
      .eq("yacht_id", yachtId)
      .single();

    if (existingYacht) {
      await AuditLog.log({
        action: "create_yacht_duplicate",
        details: { yacht_id: yachtId },
        ...clientInfo,
      });
      return error(`Yacht ID '${yachtId}' already exists`, 409);
    }

    // Compute yacht_id_hash
    const yachtIdHash = await computeYachtHash(yachtId);

    // Insert into fleet_registry
    const { data: newYacht, error: insertError } = await db
      .from("fleet_registry")
      .insert({
        yacht_id: yachtId,
        yacht_id_hash: yachtIdHash,
        yacht_name: body.yacht_name.trim(),
        yacht_model: body.yacht_model?.trim() || null,
        buyer_name: body.buyer_name.trim(),
        buyer_email: body.buyer_email.toLowerCase().trim(),
        created_at: new Date().toISOString(),
        active: false,
      })
      .select()
      .single();

    if (insertError) {
      console.error("Insert error:", insertError);
      await AuditLog.log({
        action: "create_yacht_insert_failed",
        details: { error: insertError.message, yacht_id: yachtId },
        ...clientInfo,
      });
      return error(`Failed to create yacht: ${insertError.message}`, 500);
    }

    // Log successful creation
    await AuditLog.log({
      action: "create_yacht_success",
      details: {
        yacht_id: yachtId,
        yacht_name: body.yacht_name,
        buyer_email: body.buyer_email,
      },
      ...clientInfo,
    });

    return success({
      yacht_id: yachtId,
      yacht_id_hash: yachtIdHash,
      yacht_name: body.yacht_name,
      buyer_email: body.buyer_email,
      created_at: newYacht.created_at,
      message: "Yacht created successfully",
    });

  } catch (err) {
    console.error("Create yacht error:", err);

    await AuditLog.log({
      action: "create_yacht_error",
      details: { error: String(err) },
      ...clientInfo,
    });

    return error("Failed to create yacht", 500);
  }
});
