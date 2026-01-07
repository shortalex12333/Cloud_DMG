# Workflows

Top-level business logic implementations converted from n8n workflows.

## Folder Organization

### onboarding/
**Domain:** Yacht fleet registration and activation
**n8n Source:** Signature_Installer_Cloud.json
**Endpoints:**
- POST /register - Yacht registration
- POST /check-activation/:yacht_id - Activation polling
- GET /activate/:yacht_id - Buyer activation

**Modules:**
- `register.py` - Registration endpoint logic
- `check_activation.py` - Activation status polling
- `activate.py` - Buyer activation handler
- `email.py` - Activation email sender

---

### documents/
**Domain:** Document ingestion and vector indexing
**n8n Source:** Ingestion_Docs.json, Index_docs.json
**Endpoints:**
- POST /ingest-docs-nas-cloud - Document upload from yacht
- POST /index-documents - Document vectorization

**Modules:**
- `ingestion.py` - Document ingestion from yacht NAS
- `indexing.py` - Text extraction and embedding
- `chunking.py` - Document chunking logic
- `storage.py` - Supabase storage operations

---

### portal/
**Domain:** User-facing yacht buyer portal (future)
**n8n Source:** Portal_Cloud.json (not yet deployed)
**Endpoints:**
- POST /user-login - 2FA login
- POST /verify-2fa - Code verification
- POST /download-request - DMG download

**Status:** Future implementation
