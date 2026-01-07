-- Activation Token Generation
-- =============================
-- Functions for generating and managing activation tokens

-- Generate activation token and store in download_links
CREATE OR REPLACE FUNCTION generate_activation_token(
    p_yacht_id TEXT,
    p_expires_hours INTEGER DEFAULT 24
)
RETURNS TABLE(token TEXT, token_hash TEXT, expires_at TIMESTAMPTZ, activation_link TEXT) AS $$
DECLARE
    v_token TEXT;
    v_token_hash TEXT;
    v_expires_at TIMESTAMPTZ;
    v_activation_link TEXT;
BEGIN
    -- Generate random 256-bit token (64 hex chars)
    v_token := encode(gen_random_bytes(32), 'hex');

    -- Hash the token for storage (SHA256)
    v_token_hash := encode(digest(v_token, 'sha256'), 'hex');

    -- Set expiration
    v_expires_at := NOW() + (p_expires_hours || ' hours')::INTERVAL;

    -- Insert into download_links
    INSERT INTO download_links (
        yacht_id,
        token_hash,
        expires_at,
        is_activation_link,
        used
    ) VALUES (
        p_yacht_id,
        v_token_hash,
        v_expires_at,
        TRUE,
        FALSE
    );

    -- Build activation link (will be replaced by actual domain in application)
    v_activation_link := 'https://qvzmkaamzaqxpzbewjxe.supabase.co/functions/v1/activate?yacht_id=' || p_yacht_id || '&token=' || v_token;

    -- Return token (ONLY TIME it's available in plaintext), hash, and link
    RETURN QUERY SELECT v_token, v_token_hash, v_expires_at, v_activation_link;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Validate activation token
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
      AND is_activation_link = TRUE
      AND used = FALSE
      AND expires_at > NOW();

    IF NOT FOUND THEN
        -- Check if token exists but is used/expired
        SELECT * INTO v_token_record
        FROM download_links
        WHERE yacht_id = p_yacht_id
          AND token_hash = v_token_hash
          AND is_activation_link = TRUE;

        IF FOUND THEN
            IF v_token_record.used THEN
                RETURN QUERY SELECT FALSE, 'Token already used'::TEXT, v_token_record.id;
            ELSIF v_token_record.expires_at <= NOW() THEN
                RETURN QUERY SELECT FALSE, 'Token expired'::TEXT, v_token_record.id;
            END IF;
        END IF;

        RETURN QUERY SELECT FALSE, 'Invalid token'::TEXT, NULL::UUID;
        RETURN;
    END IF;

    -- Token is valid
    RETURN QUERY SELECT TRUE, 'Valid token'::TEXT, v_token_record.id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Mark token as used
CREATE OR REPLACE FUNCTION mark_token_used(p_token_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE download_links
    SET used = TRUE, used_at = NOW()
    WHERE id = p_token_id;

    RETURN FOUND;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Update fleet_registry to track registration
CREATE OR REPLACE FUNCTION register_yacht(
    p_yacht_id TEXT,
    p_yacht_id_hash TEXT,
    p_registration_ip TEXT DEFAULT NULL
)
RETURNS TABLE(success BOOLEAN, message TEXT) AS $$
DECLARE
    v_yacht RECORD;
BEGIN
    -- Check if yacht exists
    SELECT * INTO v_yacht FROM fleet_registry WHERE yacht_id = p_yacht_id;

    IF NOT FOUND THEN
        RETURN QUERY SELECT FALSE, 'Yacht not found in registry'::TEXT;
        RETURN;
    END IF;

    -- Verify yacht_id_hash
    IF NOT verify_yacht_hash(p_yacht_id, p_yacht_id_hash) THEN
        RETURN QUERY SELECT FALSE, 'Invalid yacht_id_hash'::TEXT;
        RETURN;
    END IF;

    -- Check if already registered
    IF v_yacht.registered_at IS NOT NULL THEN
        -- Already registered, but allow re-registration (new email)
        -- Don't update registered_at, just IP
        UPDATE fleet_registry
        SET registration_ip = p_registration_ip
        WHERE yacht_id = p_yacht_id;

        RETURN QUERY SELECT TRUE, 'Re-registration successful'::TEXT;
        RETURN;
    END IF;

    -- Register yacht
    UPDATE fleet_registry
    SET registered_at = NOW(), registration_ip = p_registration_ip
    WHERE yacht_id = p_yacht_id;

    RETURN QUERY SELECT TRUE, 'Registration successful'::TEXT;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
