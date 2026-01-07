-- Add DMG tracking columns to fleet_registry
-- =============================================

-- Add columns to track built DMG files
ALTER TABLE fleet_registry ADD COLUMN IF NOT EXISTS dmg_storage_path TEXT;
ALTER TABLE fleet_registry ADD COLUMN IF NOT EXISTS dmg_sha256 TEXT;
ALTER TABLE fleet_registry ADD COLUMN IF NOT EXISTS dmg_built_at TIMESTAMPTZ;

-- Create index for DMG lookups
CREATE INDEX IF NOT EXISTS idx_fleet_registry_dmg_path ON fleet_registry(dmg_storage_path) WHERE dmg_storage_path IS NOT NULL;

COMMENT ON COLUMN fleet_registry.dmg_storage_path IS 'Supabase Storage path to DMG file (e.g., dmg/YACHT_123/CelesteOS-YACHT_123.dmg)';
COMMENT ON COLUMN fleet_registry.dmg_sha256 IS 'SHA-256 hash of DMG file for integrity verification';
COMMENT ON COLUMN fleet_registry.dmg_built_at IS 'Timestamp when DMG was built and uploaded';
