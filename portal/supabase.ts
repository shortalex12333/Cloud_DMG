// CelesteOS Portal - Supabase Client Configuration
// Project: qvzmkaamzaqxpzbewjxe

import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

// Client-side Supabase client (uses anon key)
export const supabase = createClient(supabaseUrl, supabaseAnonKey)

// Server-side Supabase client (uses service role - NEVER expose to frontend)
export function createServerClient() {
  const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY
  if (!serviceRoleKey) {
    throw new Error('SUPABASE_SERVICE_ROLE_KEY not configured')
  }
  return createClient(supabaseUrl, serviceRoleKey, {
    auth: {
      autoRefreshToken: false,
      persistSession: false
    }
  })
}

// Types
export interface FleetRegistry {
  yacht_id: string
  yacht_id_hash: string
  buyer_email: string | null
  buyer_name: string | null
  yacht_name: string | null
  active: boolean
  credentials_retrieved: boolean
  shared_secret: string | null
  created_at: string
  registered_at: string | null
  activated_at: string | null
}

export interface UserAccount {
  id: string
  yacht_id: string | null
  email: string
  display_name: string | null
  status: 'pending' | 'active' | 'suspended' | 'disabled'
  created_at: string
  last_login: string | null
}

export interface UserSession {
  id: string
  user_id: string
  session_token: string
  expires_at: string
  ip_address: string | null
  revoked: boolean
}

export interface TwoFACode {
  id: string
  user_id: string
  code: string
  code_hash: string
  purpose: 'login' | 'download' | 'password_reset'
  expires_at: string
  attempts: number
  used_at: string | null
}

export interface DownloadLink {
  id: string
  yacht_id: string
  yacht_id_hash: string
  download_token: string
  download_url: string
  package_name: string
  package_path: string
  package_size_bytes: number
  expires_at: string
  downloaded: boolean
  download_count: number
}
