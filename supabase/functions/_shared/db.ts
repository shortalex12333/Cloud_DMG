/**
 * Database Client for Edge Functions
 * ===================================
 * Supabase client with service role for privileged operations.
 */

import { createClient, SupabaseClient } from "https://esm.sh/@supabase/supabase-js@2";

let _client: SupabaseClient | null = null;

/**
 * Get Supabase client with service role (bypasses RLS).
 */
export function getServiceClient(): SupabaseClient {
  if (_client) return _client;

  const supabaseUrl = Deno.env.get("SUPABASE_URL");
  const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");

  if (!supabaseUrl || !serviceKey) {
    throw new Error("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY");
  }

  _client = createClient(supabaseUrl, serviceKey, {
    auth: {
      autoRefreshToken: false,
      persistSession: false,
    },
  });

  return _client;
}

/**
 * Fleet Registry operations.
 */
export const FleetRegistry = {
  /**
   * Get yacht by ID.
   */
  async getYacht(yachtId: string) {
    const db = getServiceClient();
    const { data, error } = await db
      .from("fleet_registry")
      .select("*")
      .eq("yacht_id", yachtId)
      .single();

    if (error && error.code !== "PGRST116") {
      throw error;
    }
    return data;
  },

  /**
   * Get yacht by ID hash.
   */
  async getYachtByHash(yachtIdHash: string) {
    const db = getServiceClient();
    const { data, error } = await db
      .from("fleet_registry")
      .select("*")
      .eq("yacht_id_hash", yachtIdHash)
      .single();

    if (error && error.code !== "PGRST116") {
      throw error;
    }
    return data;
  },

  /**
   * Update yacht active state and last seen.
   * (Schema uses `active` boolean, not `status` string)
   */
  async setActive(yachtId: string, active: boolean) {
    const db = getServiceClient();
    const { error } = await db
      .from("fleet_registry")
      .update({ active, last_seen_at: new Date().toISOString() })
      .eq("yacht_id", yachtId);

    if (error) throw error;
  },

  /**
   * Store shared secret and activate yacht.
   */
  async storeSharedSecret(yachtId: string, sharedSecret: string) {
    const db = getServiceClient();
    const { error } = await db
      .from("fleet_registry")
      .update({
        shared_secret: sharedSecret,
        active: true,
        activated_at: new Date().toISOString(),
      })
      .eq("yacht_id", yachtId);

    if (error) throw error;
  },

  /**
   * Mark credentials as retrieved (one-time operation).
   */
  async markCredentialsRetrieved(yachtId: string) {
    const db = getServiceClient();
    const { error } = await db
      .from("fleet_registry")
      .update({
        credentials_retrieved: true,
        credentials_retrieved_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      })
      .eq("yacht_id", yachtId);

    if (error) throw error;
  },
};

/**
 * Audit logging.
 */
export const AuditLog = {
  /**
   * Log an event.
   */
  async log(params: {
    yachtId?: string;
    action: string;
    details?: Record<string, unknown>;
    ipAddress?: string;
    userAgent?: string;
  }) {
    const db = getServiceClient();
    const { error } = await db.from("audit_log").insert({
      yacht_id: params.yachtId,
      action: params.action,
      details: params.details || {},
      ip_address: params.ipAddress,
      user_agent: params.userAgent,
      created_at: new Date().toISOString(),
    });

    if (error) {
      console.error("Audit log error:", error);
    }
  },
};

/**
 * Security events.
 */
export const SecurityEvents = {
  /**
   * Log a security event.
   */
  async log(params: {
    yachtId?: string;
    eventType: string;
    severity: "low" | "medium" | "high" | "critical";
    details?: Record<string, unknown>;
    ipAddress?: string;
  }) {
    const db = getServiceClient();
    const { error } = await db.from("security_events").insert({
      yacht_id: params.yachtId,
      event_type: params.eventType,
      severity: params.severity,
      details: params.details || {},
      ip_address: params.ipAddress,
      created_at: new Date().toISOString(),
    });

    if (error) {
      console.error("Security event log error:", error);
    }
  },
};
