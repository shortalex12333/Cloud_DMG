-- Fix validate_activation_token to return only one row
-- =====================================================

CREATE OR REPLACE FUNCTION validate_activation_token(
    p_yacht_id TEXT,
    p_token TEXT
)
RETURNS TABLE(valid BOOLEAN, message TEXT, token_id UUID) AS $$
DECLARE
    v_token_hash TEXT;
    v_token_record RECORD;
BEGIN
    -- Hash the provided token
    v_token_hash := encode(digest(p_token, 'sha256'), 'hex');

    -- Find matching token
    SELECT * INTO v_token_record
    FROM download_links
    WHERE yacht_id = p_yacht_id
      AND token_hash = v_token_hash
      AND is_activation_link = TRUE;

    -- No token found at all
    IF NOT FOUND THEN
        RETURN QUERY SELECT FALSE, 'Invalid token'::TEXT, NULL::UUID;
        RETURN;
    END IF;

    -- Token exists, check if already used
    IF v_token_record.used THEN
        RETURN QUERY SELECT FALSE, 'Token already used'::TEXT, v_token_record.id;
        RETURN;
    END IF;

    -- Token exists, check if expired
    IF v_token_record.expires_at <= NOW() THEN
        RETURN QUERY SELECT FALSE, 'Token expired'::TEXT, v_token_record.id;
        RETURN;
    END IF;

    -- Token is valid and unused and not expired
    RETURN QUERY SELECT TRUE, 'Valid token'::TEXT, v_token_record.id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
