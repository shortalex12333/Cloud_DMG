# CelesteOS DMG Distribution - Build and Test Guide
**Last Updated**: 2025-11-25
**Status**: Ready for First Build

This guide walks through building and testing the complete CelesteOS DMG distribution system from scratch.

---

## Prerequisites

### Required Software
- Python 3.9+ with pip
- macOS 12+ (for building DMG)
- Node.js 16+ (for Supabase CLI)
- PyInstaller: `pip3 install pyinstaller`
- Requests: `pip3 install requests`

### Required Accounts & Keys
- Supabase account with Cloud HQ project (qvzmkaamzaqxpzbewjxe)
- Supabase service role key
- n8n instance at https://api.celeste7.ai
- Microsoft Outlook configured in n8n

### Environment Variables
```bash
# Required for build and deployment
export SUPABASE_SERVICE_KEY='your-service-role-key-here'
export SUPABASE_ACCESS_TOKEN='sbp_26c94978c38e6bbe5e8a52679acf40f404e584ea'

# Optional - override defaults
export CELESTEOS_AGENT_SOURCE="$HOME/Documents/PYTHON_LOCAL_CLOUD_PMS"
export CELESTEOS_OUTPUT_DIR="$HOME/Documents/CelesteOS-Cloud/installer/build/output"
```

---

## Phase 1: Database Setup

### Step 1: Apply Migrations
1. Go to https://supabase.com/dashboard/project/qvzmkaamzaqxpzbewjxe/sql
2. Open `/supabase/migrations/APPLY_ALL.sql`
3. Copy entire contents
4. Paste into SQL Editor
5. Click "Run"
6. Verify no errors

**What this does:**
- Creates "installers" storage bucket
- Adds DMG tracking columns to fleet_registry
- Creates download token generation functions
- Sets up RLS policies

### Step 2: Verify Storage Bucket
1. Go to https://supabase.com/dashboard/project/qvzmkaamzaqxpzbewjxe/storage/buckets
2. Confirm "installers" bucket exists
3. Settings should show:
   - Public: NO
   - File size limit: 2GB
   - Allowed MIME types: application/x-apple-diskimage, application/octet-stream

**If bucket doesn't exist:**
- Create manually in dashboard
- Re-run migration 005

---

## Phase 2: Deploy Edge Functions

### Step 1: Deploy create-yacht Function
```bash
cd /Users/celeste7/Documents/CelesteOS-Cloud
export SUPABASE_ACCESS_TOKEN='sbp_26c94978c38e6bbe5e8a52679acf40f404e584ea'
npx supabase functions deploy create-yacht --project-ref qvzmkaamzaqxpzbewjxe
```

**Verify:**
```bash
curl -X POST 'https://qvzmkaamzaqxpzbewjxe.supabase.co/functions/v1/create-yacht' \
  -H "Authorization: Bearer $SUPABASE_SERVICE_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "yacht_name": "M/Y Test Build",
    "yacht_model": "Test Model",
    "buyer_name": "Test Buyer",
    "buyer_email": "test@celeste7.ai"
  }' | jq '.'
```

**Expected response:**
```json
{
  "success": true,
  "yacht_id": "M_Y_TEST_BUILD_123456",
  "yacht_id_hash": "abc123...",
  "yacht_name": "M/Y Test Build",
  "buyer_email": "test@celeste7.ai",
  "created_at": "2025-11-25T..."
}
```

### Step 2: Verify Other Functions Still Work
```bash
# Test check-activation
curl -X POST 'https://qvzmkaamzaqxpzbewjxe.supabase.co/functions/v1/check-activation' \
  -H "Content-Type: application/json" \
  -d '{"yacht_id": "TEST_YACHT_001"}' | jq '.'

# Test activate
# (Don't actually run this without a valid token)
```

---

## Phase 3: Import n8n Workflow

### Step 1: Import Workflow
1. Go to https://api.celeste7.ai (your n8n instance)
2. Click "Workflows" → "Import from File"
3. Select `/Users/celeste7/Documents/Cloud_installer/n8n-workflows/cloud_workflow_v3_with_tokens.json`
4. Click "Import"

### Step 2: Configure Credentials
1. Open imported workflow
2. Check "Cloud HQ Database" credential:
   - Host: aws-0-us-west-2.pooler.supabase.com
   - Port: 6543
   - Database: postgres
   - User: postgres.qvzmkaamzaqxpzbewjxe
   - Password: @-Ei-9Pa.uENn6g
   - SSL: enabled

3. Check "Microsoft Outlook" credential:
   - Verify connection works
   - Test sending an email

### Step 3: Activate Workflow
1. Click "Active" toggle in top-right
2. Copy webhook URL (should be `https://api.celeste7.ai/webhook/register`)

### Step 4: Test Workflow
```bash
# Create test yacht first
curl -X POST 'https://qvzmkaamzaqxpzbewjxe.supabase.co/functions/v1/create-yacht' \
  -H "Authorization: Bearer $SUPABASE_SERVICE_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "yacht_name": "M/Y Workflow Test",
    "buyer_name": "Test Owner",
    "buyer_email": "celeste@celeste7.ai"
  }' | jq -r '.yacht_id,.yacht_id_hash'

# Save the yacht_id and yacht_id_hash from above, then:
export TEST_YACHT_ID="M_Y_WORKFLOW_TEST_123456"
export TEST_YACHT_HASH="abc123..."

# Trigger registration (should send email)
curl -X POST 'https://api.celeste7.ai/webhook/register' \
  -H "Content-Type: application/json" \
  -d "{
    \"yacht_id\": \"$TEST_YACHT_ID\",
    \"yacht_id_hash\": \"$TEST_YACHT_HASH\"
  }" | jq '.'
```

**Expected response:**
```json
{
  "success": true,
  "yacht_id": "M_Y_WORKFLOW_TEST_123456",
  "activation_link": "https://qvzmkaamzaqxpzbewjxe.supabase.co/functions/v1/activate?token=xxx&yacht_id=xxx",
  "message": "Registration successful. Check your email for activation link.",
  "status": "pending_activation",
  "expires_at": "2025-11-26T..."
}
```

**Verify email:**
- Check celeste@celeste7.ai inbox
- Should receive "Activate CelesteOS for M_Y_WORKFLOW_TEST_123456"
- Email should have activation button and plain text link

---

## Phase 4: Build First DMG

### Step 1: Create Test Yacht
```bash
# Create yacht using API (no manual SQL!)
curl -X POST 'https://qvzmkaamzaqxpzbewjxe.supabase.co/functions/v1/create-yacht' \
  -H "Authorization: Bearer $SUPABASE_SERVICE_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "yacht_name": "M/Y First Build",
    "yacht_model": "Test 001",
    "buyer_name": "Celeste Seven",
    "buyer_email": "celeste@celeste7.ai"
  }' | jq '.'

# Save the yacht_id
export BUILD_YACHT_ID="M_Y_FIRST_BUILD_123456"
```

### Step 2: Verify Agent Source Exists
```bash
ls -la ~/Documents/PYTHON_LOCAL_CLOUD_PMS/celesteos_daemon.py
# Should show the file exists
```

**If missing:**
- Set CELESTEOS_AGENT_SOURCE to correct path
- Or create a minimal celesteos_daemon.py for testing

### Step 3: Build DMG
```bash
cd /Users/celeste7/Documents/CelesteOS-Cloud/installer/build

# Make sure environment variable is set
export SUPABASE_SERVICE_KEY='your-service-key-here'

# Build (no signing for first test)
python3 build_dmg.py $BUILD_YACHT_ID
```

**Expected output:**
```
Fetching yacht data from database for: M_Y_FIRST_BUILD_123456
Found yacht: M/Y First Build
Buyer: Celeste Seven <celeste@celeste7.ai>
Building CelesteOS for yacht: M_Y_FIRST_BUILD_123456
Build directory: /var/folders/.../celesteos_build_xxx

1. Generating installation manifest...
   yacht_id_hash: abc123...
2. Bundling application with PyInstaller...
   (PyInstaller output)
   Created: /var/folders/.../dist/CelesteOS.app
3. Embedding installation manifest...
   Embedded at: /var/folders/.../CelesteOS.app/Contents/Resources/install_manifest.json
4. Creating DMG...
   Created: /var/folders/.../CelesteOS-M_Y_FIRST_BUILD_123456.dmg
   SHA256: def456...
6. Uploading to Supabase Storage...
   ✓ Uploaded to: dmg/M_Y_FIRST_BUILD_123456/CelesteOS-M_Y_FIRST_BUILD_123456.dmg
   ✓ Database updated with DMG hash

============================================================
✓ Build Complete!
============================================================
DMG: /Users/celeste7/Documents/CelesteOS-Cloud/installer/build/output/CelesteOS-M_Y_FIRST_BUILD_123456.dmg

Next steps:
  1. DMG is saved locally and uploaded to Supabase Storage
  2. Generate download token: curl -X POST https://.../.../generate-download-token
  3. Send download link to yacht owner
  4. Owner downloads, installs, and activates
```

### Step 4: Verify DMG
```bash
# Check local file
ls -lh ~/Documents/CelesteOS-Cloud/installer/build/output/CelesteOS-M_Y_FIRST_BUILD_123456.dmg

# Verify in storage
curl -s "https://qvzmkaamzaqxpzbewjxe.supabase.co/rest/v1/fleet_registry?select=yacht_id,dmg_storage_path,dmg_sha256,dmg_built_at&yacht_id=eq.$BUILD_YACHT_ID" \
  -H "apikey: $SUPABASE_SERVICE_KEY" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_KEY" | jq '.'
```

### Step 5: Mount and Inspect DMG
```bash
# Mount the DMG
open ~/Documents/CelesteOS-Cloud/installer/build/output/CelesteOS-M_Y_FIRST_BUILD_123456.dmg

# Should see:
# - CelesteOS.app
# - Applications symlink

# Check app bundle
ls -la /Volumes/CelesteOS*/CelesteOS.app/Contents/
ls -la /Volumes/CelesteOS*/CelesteOS.app/Contents/Resources/

# Verify manifest exists
cat /Volumes/CelesteOS*/CelesteOS.app/Contents/Resources/install_manifest.json | jq '.'
```

**Expected manifest:**
```json
{
  "yacht_id": "M_Y_FIRST_BUILD_123456",
  "yacht_id_hash": "abc123...",
  "yacht_name": "M/Y First Build",
  "api_endpoint": "https://qvzmkaamzaqxpzbewjxe.supabase.co",
  "n8n_endpoint": "https://api.celeste7.ai/webhook",
  "version": "1.0.0",
  "build_timestamp": 1732569600,
  "bundle_id": "com.celeste7.celesteos"
}
```

---

## Phase 5: Generate Download Token

### Step 1: Generate Token
```bash
# Call database function directly
curl -s "https://qvzmkaamzaqxpzbewjxe.supabase.co/rest/v1/rpc/generate_download_token" \
  -H "apikey: $SUPABASE_SERVICE_KEY" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"p_yacht_id\": \"$BUILD_YACHT_ID\", \"p_expires_days\": 7, \"p_max_downloads\": 3}" | jq '.'
```

**Expected response:**
```json
[
  {
    "token": "abc123def456...",
    "token_hash": "789ghi...",
    "download_link": "https://qvzmkaamzaqxpzbewjxe.supabase.co/functions/v1/download?token=abc123def456...",
    "expires_at": "2025-12-02T..."
  }
]
```

### Step 2: Save Download Link
```bash
export DOWNLOAD_LINK="https://qvzmkaamzaqxpzbewjxe.supabase.co/functions/v1/download?token=abc123..."
echo $DOWNLOAD_LINK
```

---

## Phase 6: Test Download Endpoint

### Step 1: Test Download Link
```bash
# Test with curl (will download DMG)
curl -L "$DOWNLOAD_LINK" -o /tmp/test_download.dmg

# Check file
ls -lh /tmp/test_download.dmg
file /tmp/test_download.dmg
# Should show: Macintosh HFS Extended version 4 data
```

### Step 2: Verify Download Count
```bash
# Check download_links table
curl -s "https://qvzmkaamzaqxpzbewjxe.supabase.co/rest/v1/download_links?select=yacht_id,download_count,max_downloads,last_download_at&yacht_id=eq.$BUILD_YACHT_ID&is_activation_link=eq.false&order=created_at.desc&limit=1" \
  -H "apikey: $SUPABASE_SERVICE_KEY" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_KEY" | jq '.'

# Should show download_count = 1
```

---

## Phase 7: Test Installation Flow

### Step 1: Copy App to Applications (Simulated)
```bash
# Don't actually install on your dev machine yet
# Instead, test the manifest loading:

# Extract app from DMG temporarily
mkdir -p /tmp/celesteos_test
hdiutil attach ~/Documents/CelesteOS-Cloud/installer/build/output/CelesteOS-M_Y_FIRST_BUILD_123456.dmg -mountpoint /tmp/dmg_mount
cp -R /tmp/dmg_mount/CelesteOS.app /tmp/celesteos_test/
hdiutil detach /tmp/dmg_mount
```

### Step 2: Test Manifest Loading
```python
# Create test script
cat > /tmp/test_manifest.py << 'EOF'
import sys
from pathlib import Path

# Simulate PyInstaller bundle
sys.frozen = True
sys._MEIPASS = str(Path("/tmp/celesteos_test/CelesteOS.app/Contents/MacOS"))

# Add lib to path
sys.path.insert(0, str(Path.home() / "Documents" / "CelesteOS-Cloud" / "lib"))

from installer import InstallConfig

try:
    # This will fail because _MEIPASS doesn't have Resources/
    # But shows the path logic works
    config = InstallConfig.load_embedded()
    print(f"✓ Loaded: {config.yacht_id}")
except FileNotFoundError as e:
    print(f"Expected error (testing path logic): {e}")
    # Now try with actual path
    manifest_path = Path("/tmp/celesteos_test/CelesteOS.app/Contents/Resources/install_manifest.json")
    if manifest_path.exists():
        print(f"✓ Manifest exists at: {manifest_path}")
        import json
        with open(manifest_path) as f:
            data = json.load(f)
        print(f"✓ yacht_id: {data['yacht_id']}")
        print(f"✓ yacht_id_hash: {data['yacht_id_hash'][:16]}...")
    else:
        print(f"✗ Manifest not found at: {manifest_path}")
EOF

python3 /tmp/test_manifest.py
```

### Step 3: Test Registration (Don't Actually Run)
**IMPORTANT**: Don't run this yet - it will trigger real email

```python
# Test script (save for later)
cat > /tmp/test_registration.py << 'EOF'
import sys
from pathlib import Path
sys.path.insert(0, str(Path.home() / "Documents" / "CelesteOS-Cloud" / "lib"))

from installer import InstallConfig, InstallationOrchestrator

# Load from temp location
config = InstallConfig(
    yacht_id="M_Y_FIRST_BUILD_123456",
    yacht_id_hash="abc123...",
    api_endpoint="https://qvzmkaamzaqxpzbewjxe.supabase.co",
    n8n_endpoint="https://api.celeste7.ai/webhook"
)

orchestrator = InstallationOrchestrator(config)
success, message = orchestrator.register()

print(f"Registration: {success}")
print(f"Message: {message}")
EOF

# Don't run yet!
# python3 /tmp/test_registration.py
```

---

## Phase 8: End-to-End Test

### Checklist

- [ ] **Database migrations applied**
- [ ] **Storage bucket created**
- [ ] **create-yacht function deployed**
- [ ] **n8n workflow imported and active**
- [ ] **Test yacht created via API (no manual SQL)**
- [ ] **DMG built successfully**
- [ ] **DMG uploaded to storage**
- [ ] **DMG file verified (mounts, contains app, manifest correct)**
- [ ] **Download token generated**
- [ ] **Download link works**
- [ ] **Download count increments**

### Next Test: Full Activation Flow

1. Create fresh test yacht:
```bash
curl -X POST 'https://qvzmkaamzaqxpzbewjxe.supabase.co/functions/v1/create-yacht' \
  -H "Authorization: Bearer $SUPABASE_SERVICE_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "yacht_name": "M/Y Full Test",
    "buyer_name": "Test Owner",
    "buyer_email": "celeste@celeste7.ai"
  }' | jq -r '.yacht_id,.yacht_id_hash'
```

2. Build DMG for this yacht
3. Generate download token
4. Download DMG
5. Mount and copy to /Applications (on test Mac)
6. Launch app
7. App registers (check n8n execution)
8. Receive activation email
9. Click activation link
10. Agent receives shared_secret
11. Agent stores in Keychain
12. Agent verifies credentials
13. Installation complete

---

## Troubleshooting

### PyInstaller Fails
```
Error: Module not found: celesteos_agent
```
**Fix**: Verify agent source path is correct
```bash
ls $CELESTEOS_AGENT_SOURCE/celesteos_daemon.py
```

### Storage Upload Fails
```
Error: Storage upload failed: 404
```
**Fix**: Create storage bucket manually in dashboard

### DMG Not Found in Storage
**Fix**: Check fleet_registry.dmg_storage_path is set:
```bash
curl -s "https://qvzmkaamzaqxpzbewjxe.supabase.co/rest/v1/fleet_registry?select=yacht_id,dmg_storage_path&yacht_id=eq.$BUILD_YACHT_ID" \
  -H "apikey: $SUPABASE_SERVICE_KEY" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_KEY" | jq '.'
```

### Download Token Invalid
**Fix**: Check token hasn't expired or been used:
```bash
curl -s "https://qvzmkaamzaqxpzbewjxe.supabase.co/rest/v1/download_links?select=*&yacht_id=eq.$BUILD_YACHT_ID&is_activation_link=eq.false&order=created_at.desc" \
  -H "apikey: $SUPABASE_SERVICE_KEY" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_KEY" | jq '.'
```

---

## Success Criteria

✅ **Phase 1-3 Complete When:**
- Migrations applied without errors
- Storage bucket exists
- create-yacht function deployed
- n8n workflow active and sending emails

✅ **Phase 4-6 Complete When:**
- DMG builds without errors
- DMG uploads to storage
- DMG downloads via token link
- Download count increments correctly

✅ **Ready for Production When:**
- Full end-to-end test passes
- Code signing implemented
- Monitoring in place
- Documentation complete

---

**End of Build and Test Guide**

Next: Complete full end-to-end test on clean Mac
