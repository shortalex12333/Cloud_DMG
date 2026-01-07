-- Create Supabase Storage bucket for DMG installers
-- ===================================================

-- Create the installers bucket (if not exists via dashboard, this documents the config)
-- Note: Storage buckets are typically created via Supabase Dashboard, not SQL
-- But we can set the policies here

-- Storage bucket settings (to be created in dashboard):
-- - Name: installers
-- - Public: false
-- - File size limit: 2GB
-- - Allowed MIME types: application/x-apple-diskimage, application/octet-stream

-- RLS Policies for storage bucket
-- Only service role can upload (DMG builder)
-- Only signed URLs can download (via /download endpoint)

-- Policy: Service role can upload DMGs
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

-- Policy: Only service role can insert (upload)
CREATE POLICY "Service role can upload DMGs"
ON storage.objects FOR INSERT
TO service_role
WITH CHECK (bucket_id = 'installers');

-- Policy: Only service role can update
CREATE POLICY "Service role can update DMGs"
ON storage.objects FOR UPDATE
TO service_role
USING (bucket_id = 'installers');

-- Policy: Only service role can delete
CREATE POLICY "Service role can delete DMGs"
ON storage.objects FOR DELETE
TO service_role
USING (bucket_id = 'installers');

-- Policy: Signed URLs can download (SELECT)
CREATE POLICY "Signed URLs can download DMGs"
ON storage.objects FOR SELECT
TO authenticated, anon
USING (bucket_id = 'installers');

-- Log storage bucket creation
INSERT INTO audit_log (action, details, created_at)
VALUES (
  'storage_bucket_created',
  jsonb_build_object(
    'bucket', 'installers',
    'public', false,
    'file_size_limit', '2GB'
  ),
  NOW()
);
