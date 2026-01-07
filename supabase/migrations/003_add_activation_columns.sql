-- Add activation token columns to download_links
-- ==============================================
-- The existing download_links table is for DMG downloads with 2FA
-- We're adding columns to also support activation tokens

-- Add activation-specific columns
ALTER TABLE download_links ADD COLUMN IF NOT EXISTS token_hash TEXT;
ALTER TABLE download_links ADD COLUMN IF NOT EXISTS is_activation_link BOOLEAN DEFAULT FALSE;
ALTER TABLE download_links ADD COLUMN IF NOT EXISTS used BOOLEAN DEFAULT FALSE;
ALTER TABLE download_links ADD COLUMN IF NOT EXISTS used_at TIMESTAMPTZ;

-- Add index for token_hash lookups
CREATE INDEX IF NOT EXISTS idx_download_links_token_hash ON download_links(token_hash);
CREATE INDEX IF NOT EXISTS idx_download_links_is_activation_link ON download_links(is_activation_link) WHERE is_activation_link = TRUE;

-- Add constraint for activation links (must have token_hash)
ALTER TABLE download_links ADD CONSTRAINT chk_activation_has_token
  CHECK (NOT is_activation_link OR token_hash IS NOT NULL);
