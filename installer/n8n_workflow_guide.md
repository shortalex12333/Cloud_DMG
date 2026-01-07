# n8n Workflow Integration Guide
## CelesteOS DMG Registration & Activation

This guide explains how to integrate the activation token system with your n8n `/register` workflow.

## Database Functions

First, apply the `002_activation_tokens.sql` migration:

1. Go to Supabase Dashboard → SQL Editor
2. Paste the contents of `supabase/migrations/002_activation_tokens.sql`
3. Execute the SQL

This creates four functions:
- `generate_activation_token(yacht_id, expires_hours)` - Generates token and stores in DB
- `validate_activation_token(yacht_id, token)` - Validates tokens
- `mark_token_used(token_id)` - Marks token as used after activation
- `register_yacht(yacht_id, yacht_id_hash, registration_ip)` - Updates registration timestamp

## n8n `/register` Workflow Changes

### Current Flow:
```
Webhook → Validate → Update DB → Send Email → Response
```

### Updated Flow:
```
Webhook → Validate → Register Yacht → Generate Token → Send Email with Token → Response
```

### Step-by-Step Implementation:

#### 1. Add "Register Yacht" Postgres Node
**After validation, before sending email:**

- **Node Name**: Register Yacht in DB
- **Operation**: Execute Query
- **Query**:
  ```sql
  SELECT * FROM register_yacht(
    '{{ $json.yacht_id }}',
    '{{ $json.yacht_id_hash }}',
    '{{ $json.request_ip }}'
  );
  ```

This function:
- Updates `registered_at` timestamp
- Stores `registration_ip`
- Returns success/failure

#### 2. Add "Generate Activation Token" Postgres Node
**After registration succeeds:**

- **Node Name**: Generate Activation Token
- **Operation**: Execute Query
- **Query**:
  ```sql
  SELECT * FROM generate_activation_token(
    '{{ $json.yacht_id }}',
    24
  );
  ```

This function returns:
```json
{
  "token": "64-char-hex-string (PLAINTEXT, ONLY TIME VISIBLE)",
  "token_hash": "SHA256 hash stored in DB",
  "expires_at": "2025-11-25T17:07:03.564743Z",
  "activation_link": "https://qvzmkaamzaqxpzbewjxe.supabase.co/functions/v1/activate?yacht_id=XXX&token=YYY"
}
```

#### 3. Update Email Template
**In the Outlook node, use the activation_link:**

```html
<p>Dear Yacht Owner,</p>

<p>Thank you for installing CelesteOS for yacht <strong>{{ $json.yacht_name }}</strong>.</p>

<p>To complete activation, please click the link below within 24 hours:</p>

<p><a href="{{ $node["Generate Activation Token"].json.activation_link }}">
   Activate CelesteOS
</a></p>

<p>Or copy this link to your browser:</p>
<p>{{ $node["Generate Activation Token"].json.activation_link }}</p>

<p>This link expires in 24 hours and can only be used once.</p>

<p>After activation, your installer will complete automatically.</p>

<p>Best regards,<br>CelesteOS Team</p>
```

#### 4. Update Response
**Final response node:**

```javascript
return {
  success: true,
  yacht_id: $json.yacht_id,
  activation_link: $node["Generate Activation Token"].json.activation_link,
  message: "Registration successful. Check your email for activation link.",
  status: "pending_activation"
};
```

## Security Measures

### Token Security:
1. **One-Time Use**: Token marked as `used=true` after activation
2. **Expiration**: Default 24 hours, configurable
3. **Hashed Storage**: Only SHA256 hash stored in DB, plaintext never logged
4. **Unique**: Each registration gets fresh token
5. **Yacht-Bound**: Token only valid for specific yacht_id

### Flow Security:
1. `yacht_id_hash` validated before registration
2. `registration_ip` logged for audit trail
3. Activation IP logged separately in `activation_ip`
4. All events logged to `audit_log` and `security_events`

## Testing the Workflow

### Test Registration:
```bash
curl -X POST "https://api.celeste7.ai/webhook/register" \
  -H "Content-Type: application/json" \
  -d '{
    "yacht_id": "TEST_YACHT_004",
    "yacht_id_hash": "COMPUTED_HASH"
  }'
```

Expected response:
```json
{
  "success": true,
  "yacht_id": "TEST_YACHT_004",
  "activation_link": "https://qvzmkaamzaqxpzbewjxe.supabase.co/functions/v1/activate?yacht_id=TEST_YACHT_004&token=LONG_HEX_STRING",
  "message": "Registration successful. Check your email for activation link.",
  "status": "pending_activation"
}
```

### Test Activation (simulate email click):
```bash
curl "https://qvzmkaamzaqxpzbewjxe.supabase.co/functions/v1/activate?yacht_id=TEST_YACHT_004&token=TOKEN_FROM_EMAIL" \
  -H "Authorization: Bearer YOUR_ANON_KEY"
```

Expected response (HTML page):
- ✓ Activation Successful page
- Database updated: `active=true`, `shared_secret` generated

### Test Credential Retrieval (agent polling):
```bash
curl -X POST "https://qvzmkaamzaqxpzbewjxe.supabase.co/functions/v1/check-activation" \
  -H "Authorization: Bearer YOUR_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"yacht_id":"TEST_YACHT_004"}'
```

Expected response (first time):
```json
{
  "status": "active",
  "shared_secret": "256-bit-hex-string",
  "message": "Activation complete"
}
```

Expected response (second time):
```json
{
  "status": "already_retrieved",
  "message": "Credentials already retrieved"
}
```

## Database Queries for Debugging

### Check registration status:
```sql
SELECT yacht_id, registered_at, activated_at, active, credentials_retrieved
FROM fleet_registry
WHERE yacht_id = 'TEST_YACHT_004';
```

### Check activation tokens:
```sql
SELECT yacht_id, token_hash, is_activation_link, used, expires_at, created_at
FROM download_links
WHERE yacht_id = 'TEST_YACHT_004';
```

### Check audit log:
```sql
SELECT action, details, ip_address, created_at
FROM audit_log
WHERE yacht_id = 'TEST_YACHT_004'
ORDER BY created_at DESC;
```

## Error Handling

### Token Expired:
- User clicks link after 24 hours
- **Solution**: Call `/register` again to generate new token

### Token Already Used:
- User clicks link twice
- **Solution**: Check `fleet_registry.active`, if true they're already activated

### Yacht Not Found:
- Invalid yacht_id in link
- **Solution**: Check `fleet_registry` for yacht existence

### Invalid Hash:
- Tampered yacht_id_hash
- **Solution**: Security event logged, registration blocked

## Integration with DMG Installer

The Python installer (`lib/installer.py`) already implements:

1. **Registration**: Calls n8n `/register`
2. **Polling**: Calls Supabase `/check-activation` every 5 seconds
3. **One-Time Retrieval**: Stores `shared_secret` in macOS Keychain
4. **HMAC Signing**: All subsequent API calls signed with stored secret

No changes needed to the installer code - it will work seamlessly with this token system.

## Next Steps

1. Apply `002_activation_tokens.sql` migration
2. Update n8n `/register` workflow with token generation
3. Test full flow end-to-end
4. Verify security measures (one-time retrieval, expiration, etc.)
5. Build first production DMG with real yacht
