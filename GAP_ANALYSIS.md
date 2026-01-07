# CelesteOS DMG Distribution - Complete Gap Analysis
**Date**: 2025-11-25
**Status**: Pre-Production Review

This document traces through the complete user experience for both system administrators and yacht owners, identifying missing components, untested areas, and required changes before production deployment.

---

## Journey 1: System Administrator / Builder Flow

### Step 1: Create Yacht Entry in Database
**What Should Happen:**
- Admin creates a new yacht record in `fleet_registry` table
- Yacht record includes: yacht_id, yacht_name, yacht_model, buyer_name, buyer_email
- System generates yacht_id_hash automatically

**Current State:**
- ❌ **NO ADMIN INTERFACE EXISTS**
- ❌ **NO API ENDPOINT FOR YACHT CREATION**
- ⚠️ Manual SQL insertion required

**How It Works Now:**
```sql
-- Admin must manually run SQL:
INSERT INTO fleet_registry (
  yacht_id, yacht_id_hash, yacht_name, yacht_model,
  buyer_name, buyer_email, created_at
) VALUES (
  'YACHT_12345',
  encode(digest('YACHT_12345', 'sha256'), 'hex'),
  'M/Y Example',
  'Sunseeker 90',
  'John Doe',
  'john@example.com',
  NOW()
);
```

**GAPS:**
1. No web UI for yacht creation
2. No REST API endpoint
3. No validation of yacht_id uniqueness
4. No validation of email format
5. No automation for yacht_id generation
6. Manual hash computation error-prone

**NEEDED:**
- [ ] Create `/api/yachts/create` endpoint (POST)
- [ ] Add web UI or admin dashboard
- [ ] Auto-generate yacht_id from yacht_name + timestamp
- [ ] Validate all fields before insertion
- [ ] Return yacht_id_hash for DMG builder

---

### Step 2: Build DMG for Yacht
**What Should Happen:**
- Admin runs: `python3 build_dmg.py --yacht-id YACHT_12345`
- Script queries fleet_registry for yacht metadata
- Generates DMG with embedded manifest
- Stores DMG in Supabase Storage

**Current State:**
- ✅ `build_dmg.py` script exists
- ❌ **NEVER TESTED END-TO-END**
- ⚠️ Requires manual parameters (doesn't query database)
- ❌ **NO SUPABASE STORAGE UPLOAD**

**How It Works Now:**
```bash
# Admin must manually provide all fields:
cd /Users/celeste7/Documents/CelesteOS-Cloud/installer/build
python3 build_dmg.py \
  --yacht-id YACHT_12345 \
  --yacht-name "M/Y Example" \
  --buyer-email "john@example.com"

# DMG created locally in:
# ~/Documents/CelesteOS-Cloud/installer/build/output/CelesteOS-YACHT_12345.dmg
```

**GAPS:**
1. Script doesn't query fleet_registry
2. No validation that yacht_id exists in database
3. No automatic Supabase Storage upload
4. No S3 bucket/storage bucket configured
5. PyInstaller never tested on this codebase
6. No check if DMG already exists for yacht
7. No versioning system for DMGs
8. **CRITICAL**: Agent source path hardcoded to `/Users/celeste7/Documents/PYTHON_LOCAL_CLOUD_PMS`
9. No verification that `celesteos_daemon.py` exists
10. No validation of manifest integrity after build

**NEEDED:**
- [ ] Modify script to query fleet_registry by yacht_id
- [ ] Add Supabase Storage upload after DMG creation
- [ ] Create "installers" bucket in Supabase Storage
- [ ] Test PyInstaller build with actual agent code
- [ ] Add versioning (e.g., `CelesteOS-YACHT_12345-v1.0.0.dmg`)
- [ ] Configure agent source path via environment variable
- [ ] Add post-build integrity verification

---

### Step 3: Upload DMG to Supabase Storage
**What Should Happen:**
- DMG automatically uploaded to Supabase Storage bucket "installers"
- Path: `dmg/{yacht_id}/CelesteOS-{yacht_id}.dmg`
- Storage bucket has public access disabled
- Only download via signed URLs

**Current State:**
- ❌ **STORAGE BUCKET DOES NOT EXIST**
- ❌ **NO UPLOAD CODE IN build_dmg.py**
- ❌ **STORAGE POLICIES NOT CONFIGURED**

**GAPS:**
1. No "installers" storage bucket created
2. No RLS policies on storage bucket
3. No upload function in DMG builder
4. No verification DMG was uploaded successfully
5. No storage quota monitoring
6. No cleanup of old DMG versions

**NEEDED:**
- [ ] Create storage bucket via Supabase dashboard:
  ```sql
  -- In Supabase Storage, create bucket "installers"
  -- Set: Public access = OFF
  ```
- [ ] Add RLS policy for storage:
  ```sql
  CREATE POLICY "DMG download via signed URL only"
  ON storage.objects FOR SELECT
  USING (bucket_id = 'installers' AND auth.role() = 'service_role');
  ```
- [ ] Add upload code to build_dmg.py:
  ```python
  def _upload_to_storage(self):
      supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
      with open(self.dmg_path, 'rb') as f:
          supabase.storage.from_('installers').upload(
              f'dmg/{self.config.yacht_id}/CelesteOS-{self.config.yacht_id}.dmg',
              f,
              {'content-type': 'application/x-apple-diskimage'}
          )
  ```

---

### Step 4: Generate Download Token
**What Should Happen:**
- Admin creates download token for yacht owner
- Token stored in `download_links` table with expiry
- Admin sends download link via email: `https://qvzmkaamzaqxpzbewjxe.supabase.co/functions/v1/download?token=xxx`

**Current State:**
- ✅ Database function `generate_activation_token()` exists
- ❌ **NO FUNCTION FOR DOWNLOAD TOKENS**
- ⚠️ `download_links` table has mixed purpose (activation + download)
- ❌ **NO ADMIN INTERFACE TO GENERATE TOKENS**

**GAPS:**
1. No separate function for download tokens vs activation tokens
2. `download_links` table conflates two purposes:
   - DMG download tokens (for getting the DMG file)
   - Activation tokens (for activating after installation)
3. No API endpoint to generate download token
4. No email template for download link
5. Download tokens not automatically created on DMG build

**NEEDED:**
- [ ] Create `generate_download_token()` database function:
  ```sql
  CREATE OR REPLACE FUNCTION generate_download_token(
    p_yacht_id TEXT,
    p_expires_days INTEGER DEFAULT 7
  )
  RETURNS TABLE(token TEXT, download_link TEXT) AS $$
  -- Similar to activation token but for download_links
  -- Set is_activation_link = FALSE
  $$;
  ```
- [ ] Add `/api/download-tokens/create` endpoint
- [ ] Option 1: Auto-generate download token on DMG build
- [ ] Option 2: Admin manually generates via dashboard
- [ ] Create email template with download link

**QUESTIONS FOR USER:**
- Should download token be auto-generated when DMG is built?
- Or should admin manually trigger download token creation?
- How should yacht owner receive the download link initially?

---

### Step 5: Deliver DMG to Yacht Owner
**What Should Happen:**
- Yacht owner receives email with download link
- Clicks link → redirected to /download endpoint
- Validates token → serves DMG via signed URL
- DMG downloads to owner's Mac

**Current State:**
- ✅ `/download` Edge Function exists
- ❌ **NEVER TESTED**
- ❌ **NO EMAIL TEMPLATE FOR DOWNLOAD LINK**
- ❌ **NO STORAGE BUCKET (DMG has nowhere to download from)**

**GAPS:**
1. No test of /download endpoint
2. No email workflow for sending download link
3. Signed URL generation untested (needs storage bucket)
4. No fallback if DMG not found in storage
5. No progress indicator for large DMG downloads
6. No verification hash for download integrity

**NEEDED:**
- [ ] Test /download endpoint with real token
- [ ] Create download link email template
- [ ] Add n8n workflow for sending download link
- [ ] Test signed URL generation from storage
- [ ] Add SHA256 hash to download page for verification
- [ ] Test download with large DMG (~500MB typical)

---

## Journey 2: Yacht Owner / Installer Flow

### Step 6: Download and Mount DMG
**What Should Happen:**
- Owner clicks download link in email
- Browser downloads `CelesteOS-YACHT_12345.dmg`
- Owner double-clicks DMG to mount
- DMG contains: CelesteOS.app and symlink to Applications

**Current State:**
- ⚠️ Dependent on Step 5 completion
- ❌ **NO DMG EVER BUILT FOR TESTING**
- ❌ **DMG STRUCTURE UNTESTED**

**GAPS:**
1. DMG never created end-to-end
2. App bundle structure untested
3. PyInstaller bundling never tested
4. macOS Gatekeeper warnings not addressed
5. No code signing (will show "untrusted developer")
6. No notarization (will be blocked on macOS 13+)

**NEEDED:**
- [ ] **CRITICAL**: Build test DMG with real data
- [ ] Test mounting on clean Mac
- [ ] Address Gatekeeper warnings (requires code signing)
- [ ] Document workaround for unsigned app (System Settings → Privacy)

---

### Step 7: Copy App to Applications
**What Should Happen:**
- Owner drags CelesteOS.app to Applications folder
- App is copied (not moved) to /Applications/CelesteOS.app
- Manifest file is preserved inside app bundle

**Current State:**
- ⚠️ Standard macOS behavior (should work)
- ❌ **NEVER TESTED**

**GAPS:**
1. No verification that manifest survives copy
2. No check that app permissions are preserved
3. No validation app is in /Applications (could be run from anywhere)

**NEEDED:**
- [ ] Test full drag-and-drop process
- [ ] Verify manifest integrity after copy
- [ ] Consider LaunchDaemon/LaunchAgent for auto-start

---

### Step 8: Launch CelesteOS.app
**What Should Happen:**
- Owner double-clicks CelesteOS.app
- macOS prompts for permissions (Full Disk Access, etc.)
- App launches in background (LSUIElement: true)
- Shows installation UI or menu bar icon

**Current State:**
- ❌ **COMPLETE UNKNOWN - NO APP EVER BUILT**
- ❌ **NO UI IMPLEMENTATION**
- ⚠️ Agent code exists but never bundled with PyInstaller

**GAPS:**
1. **CRITICAL**: No GUI implementation
2. No indication to user that app is running
3. No progress display during installation
4. No error messages if installation fails
5. Agent likely expects different file structure than PyInstaller provides
6. Resource paths may be broken in bundle
7. No logging visible to user
8. No "installation in progress" notification

**NEEDED:**
- [ ] **CRITICAL**: Implement installation UI
  - Option 1: Menu bar app with status icon
  - Option 2: Modal window with progress bar
  - Option 3: System notifications
- [ ] Update agent code for PyInstaller bundle paths
- [ ] Test resource loading from bundle
- [ ] Add user-visible logging (e.g., ~/Library/Logs/CelesteOS/)
- [ ] Add "Installation starting..." notification

---

### Step 9: App Initialization
**What Should Happen:**
- App runs: `InstallConfig.load_embedded()`
- Loads manifest from: `CelesteOS.app/Contents/Resources/install_manifest.json`
- Verifies manifest integrity (yacht_id_hash check)
- Initializes crypto identity
- Checks Keychain for existing credentials

**Current State:**
- ✅ Code exists in `lib/installer.py`
- ❌ **NEVER TESTED IN PYINSTALLER BUNDLE**
- ⚠️ Resource path may be wrong

**GAPS:**
1. Resource path assumes standard Python file structure
2. PyInstaller uses different paths:
   - Dev: `Path(__file__).parent.parent / 'Resources'`
   - Bundle: `sys._MEIPASS / 'Resources'` or similar
3. Fallback path (`~/.celesteos/install_manifest.json`) never populated
4. No error message if manifest not found
5. Integrity check will fail if manifest tampered (good) but no user feedback

**NEEDED:**
- [ ] Fix resource path for PyInstaller:
  ```python
  @classmethod
  def load_embedded(cls) -> 'InstallConfig':
      if getattr(sys, 'frozen', False):
          # Running in PyInstaller bundle
          bundle_dir = Path(sys._MEIPASS)
      else:
          # Running in development
          bundle_dir = Path(__file__).parent.parent

      manifest_path = bundle_dir / 'Resources' / 'install_manifest.json'
      ...
  ```
- [ ] Test manifest loading in built app
- [ ] Add user-visible error if manifest missing
- [ ] Log integrity check results

---

### Step 10: Registration with n8n
**What Should Happen:**
- App calls: `orchestrator.register()`
- Sends POST to `https://api.celeste7.ai/webhook/register`
- Payload: `{"yacht_id": "...", "yacht_id_hash": "..."}`
- n8n receives request, validates, generates activation token
- n8n sends activation email via Microsoft Outlook
- App receives success response

**Current State:**
- ✅ n8n workflow file created (`cloud_workflow_v3_with_tokens.json`)
- ❌ **WORKFLOW NOT IMPORTED TO n8n**
- ❌ **WORKFLOW NEVER TESTED END-TO-END**
- ⚠️ Outlook integration exists but activation email not tested

**GAPS:**
1. Workflow not imported into n8n
2. Token generation node never executed
3. Email sending never tested with real activation link
4. Email deliverability unknown (SPF/DKIM/DMARC)
5. "From" address (noreply@celeste7.ai) may not be configured
6. Email might go to spam
7. No retry logic if n8n is down
8. No timeout handling in agent
9. No user notification that email was sent

**NEEDED:**
- [ ] **CRITICAL**: Import workflow to n8n
- [ ] Configure Microsoft Outlook credentials
- [ ] Verify "From" address is authorized
- [ ] Test email delivery to real inbox
- [ ] Check spam score
- [ ] Test with Gmail, Outlook, Apple Mail
- [ ] Add retry logic to agent (3 attempts, 5s apart)
- [ ] Show user: "Check your email at: buyer@example.com"

---

### Step 11: Yacht Owner Receives Activation Email
**What Should Happen:**
- Owner receives email with subject: "Activate CelesteOS for YACHT_12345"
- Email contains:
  - Yacht name
  - Activation button with link
  - Plain text link as fallback
  - Warning: expires in 24 hours, single-use
- Owner clicks link or button

**Current State:**
- ✅ Email template exists in workflow
- ❌ **EMAIL NEVER ACTUALLY SENT**
- ⚠️ Template looks good (professional HTML)

**GAPS:**
1. Email never sent in testing
2. Activation link not tested (full URL format unknown)
3. Link format should be:
   `https://qvzmkaamzaqxpzbewjxe.supabase.co/functions/v1/activate?token=xxx&yacht_id=YACHT_12345`
4. But actual format from `generate_activation_token()` is:
   `https://qvzmkaamzaqxpzbewjxe.supabase.co/functions/v1/activate?token=xxx&yacht_id=YACHT_12345`
5. ✅ **This matches!** No gap here.
6. Email client compatibility untested (HTML rendering)
7. Mobile email client display untested
8. Link click tracking not implemented

**NEEDED:**
- [ ] Send real test email to multiple email clients
- [ ] Test HTML rendering in: Gmail, Outlook, Apple Mail, iOS Mail
- [ ] Verify button click works on mobile
- [ ] Test plain text link fallback
- [ ] Consider adding SendGrid/Mailgun for better deliverability

---

### Step 12: Agent Polls for Activation
**What Should Happen:**
- While owner checks email, agent polls:
  `POST /check-activation {"yacht_id": "..."}`
- Every 5 seconds
- Max 1 hour timeout
- Shows progress to user: "Waiting for activation... 00:05"

**Current State:**
- ✅ Code exists in `lib/installer.py`
- ✅ `/check-activation` endpoint tested and working
- ❌ **NEVER TESTED IN REAL APP**
- ❌ **NO USER FEEDBACK MECHANISM**

**GAPS:**
1. Polling loop never executed in real environment
2. No progress display to user
3. No indication that email was sent or where
4. User might close app during polling (app needs to persist)
5. No background operation (app might be killed by macOS)
6. 5-second poll interval might be too aggressive (rate limiting?)
7. 1-hour timeout might be too short (owner away from computer)

**NEEDED:**
- [ ] Show modal window: "Waiting for activation..."
- [ ] Display countdown timer
- [ ] Show buyer email address
- [ ] Add "Resend Email" button
- [ ] Persist state if app is closed (LaunchAgent?)
- [ ] Consider push notification instead of polling
- [ ] Increase timeout to 24 hours (same as token expiry)
- [ ] Add rate limiting protection (exponential backoff)

---

### Step 13: Owner Clicks Activation Link
**What Should Happen:**
- Email client opens browser to:
  `https://qvzmkaamzaqxpzbewjxe.supabase.co/functions/v1/activate?token=xxx&yacht_id=xxx`
- `/activate` Edge Function receives request
- Validates token using `validate_activation_token()`
- Marks token as used
- Calls `activate_yacht()` to generate shared_secret
- Updates `fleet_registry`: `active=true`, `activated_at=NOW()`
- Returns HTML success page

**Current State:**
- ✅ `/activate` Edge Function exists and tested
- ✅ Database functions work correctly
- ✅ HTML success page renders properly
- ✅ Token validation works
- ✅ One-time use enforced

**GAPS:**
1. **MINOR**: Success page has no "close this window" instruction
2. **MINOR**: No redirect back to app (not possible without custom URL scheme)
3. No tracking if user actually saw the page
4. No analytics/monitoring on activation success rate

**NEEDED:**
- [ ] Add to success page: "You can close this window"
- [ ] Optional: Add custom URL scheme (celesteos://) to redirect back to app
- [ ] Add analytics event for activation success
- [ ] Monitor activation success rate in dashboard

---

### Step 14: Agent Receives Shared Secret
**What Should Happen:**
- Next poll to `/check-activation` returns:
  ```json
  {
    "status": "active",
    "shared_secret": "abc123...",
    "message": "Yacht activated"
  }
  ```
- Agent stores secret in macOS Keychain
- Secret never retrieved again (security)

**Current State:**
- ✅ `/check-activation` returns secret correctly
- ✅ One-time retrieval enforced (tested)
- ✅ Keychain storage code exists
- ❌ **KEYCHAIN STORAGE NEVER TESTED**

**GAPS:**
1. Keychain storage (`security` command) never executed in real environment
2. Keychain access might require user permission prompt
3. No error handling if Keychain storage fails
4. No verification that secret was stored successfully
5. No fallback if Keychain unavailable
6. Second poll correctly returns "already_retrieved" ✅
7. But agent doesn't handle this gracefully (treats as ERROR)

**NEEDED:**
- [ ] **CRITICAL**: Test Keychain storage on real macOS
- [ ] Handle Keychain permission prompts
- [ ] Verify `security add-generic-password` works
- [ ] Test retrieval: `security find-generic-password`
- [ ] Fix agent to handle "already_retrieved" gracefully:
  ```python
  elif status == 'already_retrieved':
      # Check if we have secret in Keychain already
      secret = KeychainStore.retrieve_secret(self.config.yacht_id)
      if secret:
          self._crypto = CryptoIdentity(self.config.yacht_id, secret)
          return InstallState.ACTIVE, None
      else:
          # Security breach - someone else got the secret
          return InstallState.ERROR, None
  ```

---

### Step 15: Agent Verifies Credentials
**What Should Happen:**
- Agent makes authenticated request to `/verify-credentials`
- Signs request with HMAC-SHA256
- Server validates signature
- Returns 200 OK if valid
- Agent transitions to OPERATIONAL state

**Current State:**
- ✅ `/verify-credentials` endpoint exists and tested
- ✅ HMAC signing code exists in `lib/crypto.py`
- ✅ Signature verification works
- ❌ **NEVER TESTED END-TO-END**

**GAPS:**
1. Credential verification never executed in real flow
2. Network errors not handled gracefully
3. No retry logic if verification fails
4. No user notification of success
5. Agent behavior after OPERATIONAL state is unclear

**NEEDED:**
- [ ] Test full authentication flow
- [ ] Add retry logic (3 attempts)
- [ ] Show success message: "✓ Installation complete!"
- [ ] Define what happens in OPERATIONAL state
- [ ] Document what the agent does after activation

---

### Step 16: Normal Operation
**What Should Happen:**
- Agent runs in background
- Makes periodic authenticated API calls
- Syncs yacht data to cloud
- Displays status in menu bar or UI

**Current State:**
- ❌ **COMPLETELY UNDEFINED**
- ⚠️ Agent code exists in `/PYTHON_LOCAL_CLOUD_PMS` but not integrated

**GAPS:**
1. No integration between installer and actual agent
2. Agent code structure unclear
3. No documentation on what agent does post-activation
4. No API endpoints for agent operations
5. No UI for agent status
6. No auto-start mechanism (LaunchAgent)
7. No auto-update mechanism
8. No uninstall process

**NEEDED:**
- [ ] **CRITICAL**: Define agent behavior in OPERATIONAL state
- [ ] Integrate installer with agent code
- [ ] Create LaunchAgent plist for auto-start
- [ ] Document agent API endpoints
- [ ] Implement status UI
- [ ] Add auto-update check
- [ ] Document uninstall procedure

---

## Cross-Cutting Concerns

### Security Issues
1. ❌ **No code signing** - App will be blocked by macOS 13+
2. ❌ **No notarization** - Gatekeeper will warn users
3. ⚠️ Manifest integrity check exists but never tested
4. ⚠️ Keychain storage exists but never tested
5. ✅ One-time credential retrieval works
6. ✅ HMAC signing implemented correctly
7. ❌ No certificate pinning for API calls
8. ❌ No detection of man-in-the-middle attacks
9. ❌ Shared secret transmitted in plain JSON (should be over HTTPS - ✅ it is)
10. ❌ No rate limiting on agent API calls

### Error Handling
1. ❌ No user-visible error messages
2. ❌ No logging accessible to user
3. ❌ No crash reporting
4. ❌ No telemetry/monitoring
5. ❌ No support contact information
6. ❌ No troubleshooting guide

### Testing Gaps
1. ❌ No end-to-end test of complete flow
2. ❌ PyInstaller build never executed
3. ❌ DMG creation never completed
4. ❌ App bundle never launched
5. ❌ Keychain access never tested
6. ❌ n8n workflow never imported/executed
7. ✅ Database functions tested
8. ✅ Edge Functions tested individually
9. ❌ No automated test suite
10. ❌ No CI/CD pipeline

### Documentation Gaps
1. ⚠️ STATUS.md exists but incomplete
2. ❌ No user-facing installation guide
3. ❌ No troubleshooting guide
4. ❌ No developer documentation for agent code
5. ❌ No API documentation
6. ❌ No architecture diagram
7. ❌ No security audit documentation

### Operational Readiness
1. ❌ No monitoring dashboard
2. ❌ No alerting for failed activations
3. ❌ No metrics collection
4. ❌ No backup/restore procedures
5. ❌ No disaster recovery plan
6. ❌ No rollback strategy for bad DMG builds
7. ❌ No admin interface for fleet management
8. ❌ No customer support tooling

---

## Priority Issues

### 🔴 CRITICAL (Must fix before any deployment)
1. **Build and test actual DMG** - Never been done
2. **Import n8n workflow** - Registration won't work without it
3. **Create Supabase Storage bucket** - No place to store DMGs
4. **Test Keychain storage** - Credentials won't persist
5. **Implement installation UI** - User has no feedback
6. **Fix PyInstaller resource paths** - Manifest won't load
7. **Code signing** - App won't run on modern macOS

### 🟡 HIGH (Should fix for MVP)
1. Create yacht creation API endpoint
2. Auto-upload DMG to storage after build
3. Generate download tokens automatically
4. Send download link email to yacht owner
5. Test email deliverability
6. Add retry logic to agent
7. Handle "already_retrieved" status gracefully
8. Define OPERATIONAL state behavior
9. Add logging and error messages
10. Create troubleshooting documentation

### 🟢 MEDIUM (Post-MVP improvements)
1. Admin dashboard for fleet management
2. Monitoring and alerting
3. Auto-update mechanism
4. Uninstall procedure
5. Certificate pinning
6. Rate limiting
7. Analytics/telemetry
8. Automated testing

### ⚪ LOW (Nice to have)
1. Custom URL scheme for redirect
2. Link click tracking in emails
3. Progress indicator for large downloads
4. DMG versioning system
5. A/B testing for email templates

---

## Testing Checklist

### Before ANY Production Use:
- [ ] Build DMG with real yacht data
- [ ] Mount DMG and verify contents
- [ ] Copy app to Applications
- [ ] Launch app (handle Gatekeeper warnings)
- [ ] Verify manifest loads correctly
- [ ] Import n8n workflow
- [ ] Send test registration
- [ ] Verify email received
- [ ] Click activation link
- [ ] Verify HTML page displays
- [ ] Verify agent receives secret
- [ ] Verify Keychain storage works
- [ ] Verify credential verification works
- [ ] Test on clean Mac (not developer machine)

### For Each Test:
- [ ] Document results
- [ ] Screenshot any errors
- [ ] Save logs
- [ ] Test on macOS 12, 13, 14, and 15

---

## Recommended Next Steps

1. **Immediate (Today):**
   - Create Supabase Storage bucket "installers"
   - Import n8n workflow
   - Test workflow sends email
   - Create test yacht in database

2. **This Week:**
   - Build first real DMG
   - Test on clean Mac
   - Fix all build errors
   - Test Keychain storage
   - Implement basic UI

3. **Next Week:**
   - End-to-end test
   - Fix all critical issues
   - Code signing setup
   - Documentation

4. **Before Production:**
   - Security audit
   - Load testing
   - Monitoring setup
   - Admin dashboard
   - Customer support process

---

## Questions Needing Decisions

1. **Download Link Delivery**: How should yacht owner initially receive the DMG?
   - Option A: Email with download link (requires download token system)
   - Option B: Portal/dashboard where they can download (requires web UI)
   - Option C: Physical USB drive (requires different process)

2. **Installation UI**: What should the user see during installation?
   - Option A: Menu bar app with dropdown
   - Option B: Modal window with progress bar
   - Option C: System notifications only
   - Option D: No UI (silent background install)

3. **Agent Behavior**: What should the agent do after activation?
   - Current: Unclear from codebase
   - Need: Document expected behavior

4. **Auto-Start**: Should agent auto-start on login?
   - Yes: Requires LaunchAgent
   - No: User manually launches

5. **Code Signing**: Do we have Apple Developer ID?
   - If yes: Set up signing in build script
   - If no: Document workaround for users

6. **Yacht ID Format**: Should we auto-generate yacht_id?
   - Current: Admin manually specifies (e.g., "YACHT_12345")
   - Better: Auto-generate from yacht_name + timestamp

---

**END OF GAP ANALYSIS**

This document should be reviewed and updated as issues are resolved.
