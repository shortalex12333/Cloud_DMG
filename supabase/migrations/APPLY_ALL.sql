-- Combined Migrations for CelesteOS DMG Distribution
-- ====================================================
-- Apply this in Supabase SQL Editor for Cloud HQ database
-- Database: qvzmkaamzaqxpzbewjxe
--
-- INSTRUCTIONS:
-- 1. Go to https://supabase.com/dashboard/project/qvzmkaamzaqxpzbewjxe/sql
-- 2. Copy this entire file
-- 3. Paste into SQL Editor
-- 4. Click "Run"

-- ============================================
-- Migration 005: Create Storage Bucket
-- ============================================

-- Create the installers bucket
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'installers',
  'installers',
  false,
  2147483648, -- 2GB
  ARRAY['application/x-apple-diskimage', 'application/octet-stream']
)
ON CONFLICT (id) DO UPDATE SET
  public = false,
  file_size_limit = 2147483648,
  allowed_mime_types = ARRAY['application/x-apple-diskimage', 'application/octet-stream'];

-- RLS Policies for storage
CREATE POLICY IF NOT EXISTS "Service role can upload DMGs"
ON storage.objects FOR INSERT
TO service_role
WITH CHECK (bucket_id = 'installers');

CREATE POLICY IF NOT EXISTS "Service role can update DMGs"
ON storage.objects FOR UPDATE
TO service_role
USING (bucket_id = 'installers');

CREATE POLICY IF NOT EXISTS "Service role can delete DMGs"
ON storage.objects FOR DELETE
TO service_role
USING (bucket_id = 'installers');

CREATE POLICY IF NOT EXISTS "Signed URLs can download DMGs"
ON storage.objects FOR SELECT
TO authenticated, anon
USING (bucket_id = 'installers');


-- ============================================
-- Migration 006: Add DMG Tracking Columns
-- ============================================

ALTER TABLE fleet_registry ADD COLUMN IF NOT EXISTS dmg_storage_path TEXT;
ALTER TABLE fleet_registry ADD COLUMN IF NOT EXISTS dmg_sha256 TEXT;
ALTER TABLE fleet_registry ADD COLUMN IF NOT EXISTS dmg_built_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_fleet_registry_dmg_path
ON fleet_registry(dmg_storage_path)
WHERE dmg_storage_path IS NOT NULL;

COMMENT ON COLUMN fleet_registry.dmg_storage_path IS 'Supabase Storage path to DMG file';
COMMENT ON COLUMN fleet_registry.dmg_sha256 IS 'SHA-256 hash of DMG file for integrity verification';
COMMENT ON COLUMN fleet_registry.dmg_built_at IS 'Timestamp when DMG was built and uploaded';


-- ============================================
-- Migration 007: Download Token System
-- ============================================

CREATE OR REPLACE FUNCTION generate_download_token(
    p_yacht_id TEXT,
    p_expires_days INTEGER DEFAULT 7,
    p_max_downloads INTEGER DEFAULT 3
)
RETURNS TABLE(
    token TEXT,
    token_hash TEXT,
    download_link TEXT,
    expires_at TIMESTAMPTZ
) AS $$
DECLARE
    v_token TEXT;
    v_token_hash TEXT;
    v_expires_at TIMESTAMPTZ;
    v_link_id UUID;
    v_base_url TEXT := 'https://qvzmkaamzaqxpzbewjxe.supabase.co/functions/v1/download';
BEGIN
    IF NOT EXISTS (SELECT 1 FROM fleet_registry WHERE yacht_id = p_yacht_id) THEN
        RAISE EXCEPTION 'Yacht % not found', p_yacht_id;
    END IF;

    v_token := encode(gen_random_bytes(32), 'hex');
    v_token_hash := encode(digest(v_token, 'sha256'), 'hex');
    v_expires_at := NOW() + (p_expires_days || ' days')::INTERVAL;

    INSERT INTO download_links (
        yacht_id,
        token_hash,
        is_activation_link,
        expires_at,
        download_count,
        max_downloads,
        created_at
    ) VALUES (
        p_yacht_id,
        v_token_hash,
        FALSE,
        v_expires_at,
        0,
        p_max_downloads,
        NOW()
    ) RETURNING id INTO v_link_id;

    RETURN QUERY SELECT
        v_token,
        v_token_hash,
        v_base_url || '?token=' || v_token AS download_link,
        v_expires_at;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION validate_download_token(
    p_token TEXT
)
RETURNS TABLE(
    valid BOOLEAN,
    message TEXT,
    yacht_id TEXT,
    download_count INTEGER,
    max_downloads INTEGER
) AS $$
DECLARE
    v_token_hash TEXT;
    v_link RECORD;
BEGIN
    v_token_hash := encode(digest(p_token, 'sha256'), 'hex');

    SELECT * INTO v_link
    FROM download_links
    WHERE token_hash = v_token_hash
      AND is_activation_link = FALSE;

    IF NOT FOUND THEN
        RETURN QUERY SELECT FALSE, 'Invalid download token'::TEXT, NULL::TEXT, NULL::INTEGER, NULL::INTEGER;
        RETURN;
    END IF;

    IF v_link.expires_at <= NOW() THEN
        RETURN QUERY SELECT FALSE, 'Download link expired'::TEXT, v_link.yacht_id, v_link.download_count, v_link.max_downloads;
        RETURN;
    END IF;

    IF v_link.download_count >= v_link.max_downloads THEN
        RETURN QUERY SELECT FALSE, 'Maximum downloads reached'::TEXT, v_link.yacht_id, v_link.download_count, v_link.max_downloads;
        RETURN;
    END IF;

    RETURN QUERY SELECT TRUE, 'Valid'::TEXT, v_link.yacht_id, v_link.download_count, v_link.max_downloads;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION increment_download_count(
    p_token TEXT,
    p_ip_address TEXT DEFAULT NULL
)
RETURNS BOOLEAN AS $$
DECLARE
    v_token_hash TEXT;
BEGIN
    v_token_hash := encode(digest(p_token, 'sha256'), 'hex');

    UPDATE download_links
    SET download_count = download_count + 1,
        last_download_at = NOW(),
        last_download_ip = COALESCE(p_ip_address, last_download_ip)
    WHERE token_hash = v_token_hash
      AND is_activation_link = FALSE;

    RETURN FOUND;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- ============================================
-- Verification Queries
-- ============================================

-- Run these after to verify:
DO $$
BEGIN
    RAISE NOTICE 'Migrations applied successfully!';
    RAISE NOTICE 'Storage bucket: %', (SELECT count(*) FROM storage.buckets WHERE id = 'installers');
    RAISE NOTICE 'DMG columns: %', (SELECT count(*) FROM information_schema.columns WHERE table_name = 'fleet_registry' AND column_name = 'dmg_storage_path');
    RAISE NOTICE 'Download token function: %', (SELECT count(*) FROM pg_proc WHERE proname = 'generate_download_token');
END $$;
