# CelesteOS Cloud - Complete System Architecture

**Database:** qvzmkaamzaqxpzbewjxe.supabase.co (Cloud HQ)
**Analysis Date:** 2026-01-07
**Status:** Production Active

---

## 🏗️ System Overview

CelesteOS Cloud is a **multi-tenant yacht fleet management and knowledge system** with three major subsystems:

1. **Onboarding System** - Yacht registration and activation
2. **Document Ingestion Pipeline** - NAS document collection and storage
3. **Knowledge Base Indexing** - Vector search and AI-powered retrieval

---

## 📊 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLOUD HQ DATABASE                            │
│                 qvzmkaamzaqxpzbewjxe.supabase.co                    │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐       │
│  │fleet_registry│  │download_links│  │alias_candidates     │       │
│  │user_accounts │  │audit_log     │  │resolution_episodes  │       │
│  │user_sessions │  │security_events│  │doc_metadata        │       │
│  │twofa_codes   │  │alert_rules   │  │search_document_chunks│      │
│  └──────────────┘  └──────────────┘  └────────────────────┘       │
└─────────────────────────────────────────────────────────────────────┘
            ▲                    ▲                      ▲
            │                    │                      │
┌───────────┴────────┐  ┌────────┴──────────┐  ┌──────┴───────────┐
│   ONBOARDING       │  │  DOC INGESTION    │  │  DOC INDEXING    │
│   n8n workflow     │  │  n8n workflow     │  │  n8n workflow    │
└────────────────────┘  └───────────────────┘  └──────────────────┘
            ▲                    ▲                      ▲
            │                    │                      │
┌───────────┴────────┐  ┌────────┴──────────┐  ┌──────┴───────────┐
│  Yacht Installer   │  │  localhost:5050   │  │  Render Service  │
│  (DMG on yacht)    │  │  (Yacht-side)     │  │  Text Extraction │
└────────────────────┘  └───────────────────┘  └──────────────────┘
```

---

## 🔄 System 1: Onboarding & Activation

**n8n Workflow:** `Signature_Installer_Cloud.json`
**Purpose:** Yacht fleet registration, activation, and credential distribution

### Components

#### **1.1 Webhook Endpoints**

| Endpoint | Method | Purpose | Called By |
|----------|--------|---------|-----------|
| `/register` | POST | Register yacht for activation | Yacht installer (DMG) |
| `/check-activation/:yacht_id` | POST | Poll for activation status | Yacht installer (polling) |
| `/activate/:yacht_id` | GET | Activate yacht via email link | Buyer clicking email |
| `/celesteos/activation-email` | POST | Manual email trigger | Internal/testing |

#### **1.2 Database Operations**

**Tables Used:**
- `fleet_registry` - Master yacht records
- `download_links` - Activation tokens (unused in current flow)
- `audit_log` - Activity tracking

**Connection:**
- PostgreSQL credential: `"Cloud HQ"` (id: `jlUpkUwelaH9HiTL`)
- Also connects to: `"Cloud PMS"` (id: `aWIDhHpJCpC97WzF`)

#### **1.3 Activation Flow**

```
1. YACHT INSTALLER CALLS /register
   ├─ Validates yacht_id + yacht_id_hash
   ├─ Looks up yacht in fleet_registry
   ├─ Validates buyer_email exists
   ├─ Updates registered_at timestamp
   ├─ Generates activation email (XSS-safe HTML)
   └─ Sends email via Microsoft Outlook OAuth

2. BUYER RECEIVES EMAIL
   └─ Activation link: https://api.celeste7.ai/webhook/yacht-activate-webhook-v2/activate/{yacht_id}

3. BUYER CLICKS LINK → /activate/:yacht_id
   ├─ Validates yacht exists and active=false
   ├─ Updates database:
   │   ├─ active = true
   │   ├─ activated_at = NOW()
   │   ├─ shared_secret = encode(gen_random_bytes(32), 'hex')
   └─ Returns success HTML page

4. YACHT INSTALLER POLLS /check-activation/:yacht_id
   ├─ Returns "pending" while waiting
   ├─ When activated, returns ONE-TIME:
   │   ├─ yacht_id
   │   ├─ yacht_id_hash
   │   ├─ shared_secret (64-char hex)
   │   └─ activated_at timestamp
   ├─ Marks credentials_retrieved = true
   └─ Future polls return "already_retrieved"
```

### **1.4 Security Features**

1. **Input Validation:**
   - `yacht_id`: Must match `^[A-Z0-9_-]+$`, max 50 chars
   - `yacht_id_hash`: Must be 64-char hex (SHA-256)

2. **One-Time Credential Retrieval:**
   - `shared_secret` returned only ONCE
   - `credentials_retrieved` flag prevents re-retrieval
   - Stored in yacht's macOS Keychain

3. **Email Safety:**
   - XSS protection via HTML escaping
   - Microsoft Outlook OAuth integration

4. **Cleanup:**
   - Daily cron job (00:00) deletes abandoned registrations (7+ days old)

---

## 🔄 System 2: Document Ingestion Pipeline

**n8n Workflow:** `Ingestion_Docs.json`
**Purpose:** Accept documents from yachts, store in cloud, queue for indexing

### Components

#### **2.1 Webhook Endpoint**

| Endpoint | Method | Purpose | Called By |
|----------|--------|---------|-----------|
| `/ingest-docs-nas-cloud` | POST | Ingest documents from NAS | **localhost:5050** (yacht-side service) |

**Caller:** Local service running on yacht (port 5050) - **NOT in this repo**

#### **2.2 Request Format**

```json
{
  "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
  "local_path": "/nas/Engineering/Fuel/manual.pdf",
  "filename": "manual.pdf",
  "content_type": "application/pdf",
  "file_size": 524288,
  "system_path": "02_ENGINEERING/fuel_systems",
  "directories": ["engineering", "fuel"],
  "doc_type": "manual",
  "system_tag": "fuel"
}
```

Plus **binary file attachment** in multipart/form-data.

#### **2.3 Processing Flow**

```
1. RECEIVE DOCUMENT
   ├─ Parse metadata from body.data (JSON string)
   └─ Extract binary file

2. CHECK FOR DUPLICATE
   ├─ Query doc_metadata for yacht_id + filename
   └─ If exists: Return "duplicate" response

3. UPLOAD TO SUPABASE STORAGE
   ├─ Destination: documents/{yacht_id}/{system_path}/{filename}
   ├─ Endpoint: vzsohavtuotocgrfkfyd.supabase.co/storage/v1/object/documents/...
   └─ Returns storage_path (Key)

4. INSERT METADATA TO DATABASE
   Table: doc_metadata
   Fields:
   ├─ yacht_id (UUID)
   ├─ source: "nas"
   ├─ original_path (from NAS)
   ├─ filename
   ├─ content_type
   ├─ size_bytes
   ├─ sha256 (NULL for now)
   ├─ storage_path (Supabase Storage key)
   ├─ system_path
   ├─ indexed: false
   ├─ metadata (JSONB with directories, upload_timestamp, etc.)
   ├─ doc_type
   └─ system_type (mapped from system_tag)

5. RESPOND SUCCESS
   └─ Return document_id to caller

6. TRIGGER INDEXING (async)
   ├─ POST https://api.celeste7.ai/webhook/index-documents
   └─ Pass document metadata to indexing workflow
```

#### **2.4 Database Connections**

- **PostgreSQL:** `"Cloud PMS"` (id: `aWIDhHpJCpC97WzF`)
- **Supabase Storage:** `"PMS"` (id: `TYZQMctc7crEVTTP`)
  - Project: `vzsohavtuotocgrfkfyd.supabase.co`

---

## 🔄 System 3: Document Indexing & Vector Search

**n8n Workflow:** `Index_docs (1).json`
**Purpose:** Extract text from documents, chunk, embed, and store for semantic search

### Components

#### **3.1 Webhook Endpoint**

| Endpoint | Method | Purpose | Called By |
|----------|--------|---------|-----------|
| `/index-documents` | POST | Index a document | **Ingestion_Docs workflow** (step 6) |

#### **3.2 Request Format**

```json
{
  "filename": "manual.pdf",
  "content_type": "application/pdf",
  "storage_path": "documents/{yacht_id}/path/file.pdf",
  "document_id": "9499c577-a0c4-4b43-9505-9c0f1464fc00",
  "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
  "system_tag": "fuel",
  "doc_type": "manual"
}
```

#### **3.3 Processing Flow**

```
1. RECEIVE INDEXING REQUEST
   └─ Get document metadata

2. EXTRACT TEXT FROM DOCUMENT
   ├─ POST https://celeste-file-type.onrender.com/extract
   ├─ External service fetches file from Supabase Storage
   ├─ Extracts text based on content_type:
   │   ├─ PDF → PDF text extraction
   │   ├─ DOCX → Word text extraction
   │   ├─ XLSX → Excel text extraction
   │   ├─ CSV/JSON/XML/HTML/TXT → Direct parsing
   └─ Returns: { text, yacht_id, document_id, filename, ... }

3. LOAD AS LANGCHAIN DOCUMENT
   ├─ Document Loader node
   └─ Metadata attached:
       ├─ yacht_id
       ├─ document_id
       ├─ filename
       ├─ content_type
       ├─ doc_type
       └─ system_tag

4. CHUNK TEXT
   ├─ Text Splitter: RecursiveCharacterTextSplitter
   ├─ Chunk size: 1000 characters
   └─ Chunk overlap: 200 characters

5. GENERATE EMBEDDINGS
   ├─ OpenAI Embeddings: text-embedding-3-small
   └─ API: OpenAI credential "OpenAi"

6. STORE IN VECTOR DATABASE
   ├─ Supabase Vector Store
   ├─ Table: search_document_chunks
   ├─ Query function: match_documents
   └─ Each chunk stored with:
       ├─ embedding (vector)
       └─ metadata (yacht_id, doc_id, filename, etc.)

7. RESPOND SUCCESS
   └─ Return indexed status
```

### **3.4 External Services**

| Service | URL | Purpose |
|---------|-----|---------|
| Text Extraction Service | https://celeste-file-type.onrender.com | Extract text from PDFs, DOCX, XLSX, etc. |
| OpenAI API | text-embedding-3-small | Generate semantic embeddings |
| Supabase Storage | vzsohavtuotocgrfkfyd.supabase.co | Store document chunks + vectors |

### **3.5 Database Schema**

**Table:** `search_document_chunks` (on Cloud PMS DB)

```sql
CREATE TABLE search_document_chunks (
  id UUID PRIMARY KEY,
  content TEXT,                    -- Chunk text
  metadata JSONB,                  -- { yacht_id, document_id, filename, ... }
  embedding VECTOR(1536)           -- OpenAI embedding dimension
);

-- Function for vector similarity search
CREATE FUNCTION match_documents(
  query_embedding VECTOR(1536),
  match_count INT,
  filter JSONB
) RETURNS ...
```

---

## 🗄️ Database Architecture

### **Cloud HQ Database** (qvzmkaamzaqxpzbewjxe.supabase.co)

**Purpose:** Fleet management and onboarding

**Tables:**
```
fleet_registry              - Yacht identities, credentials
├─ yacht_id (PK)
├─ yacht_id_hash
├─ shared_secret (one-time retrieval)
├─ buyer_email
├─ active, credentials_retrieved
└─ registered_at, activated_at

user_accounts               - Portal user logins
user_sessions               - Active sessions
twofa_codes                 - 2FA verification
download_links              - Activation tokens
audit_log                   - All fleet events
security_events             - Security incidents
alert_rules                 - Monitoring rules
alert_history               - Alert logs
alias_candidates            - NLP learning
resolution_episodes         - Forum-scraped knowledge
```

### **Cloud PMS Database** (vzsohavtuotocgrfkfyd.supabase.co)

**Purpose:** Document management and knowledge base

**Tables:**
```
doc_metadata                - Document registry
├─ yacht_id (UUID)
├─ filename
├─ storage_path (Supabase Storage key)
├─ indexed (boolean)
├─ doc_type, system_type
└─ metadata (JSONB)

search_document_chunks      - Vector search database
├─ content (text chunk)
├─ embedding (VECTOR(1536))
└─ metadata (yacht_id, doc_id, etc.)
```

---

## 🔐 Authentication & Security

### **Yacht-to-Cloud Authentication**

1. **Registration Phase:**
   - Yacht sends `yacht_id` + `yacht_id_hash` (SHA-256)
   - Server validates both against fleet_registry

2. **Activation Phase:**
   - Server generates 256-bit `shared_secret`
   - Returned ONE TIME to yacht installer
   - Yacht stores in macOS Keychain

3. **Operational Phase:**
   - All requests signed with HMAC-SHA256(payload, shared_secret)
   - Signature verified by edge functions

### **n8n Credentials**

| Credential | Type | Used In |
|------------|------|---------|
| Cloud HQ | PostgreSQL | Onboarding workflow |
| Cloud PMS | PostgreSQL | Doc ingestion, indexing |
| PMS | Supabase API | Storage uploads |
| Microsoft Outlook account | OAuth2 | Activation emails |
| OpenAi | OpenAI API | Embeddings generation |

---

## 🚀 Data Flow: Complete Journey

### **Scenario: New Yacht Onboarding + Document Upload**

```
Day 1: YACHT SETUP
┌─────────────────────────────────────────────────────────────┐
│ 1. Admin pre-creates yacht in fleet_registry:              │
│    - yacht_id: MYSTIC_2025_001                             │
│    - yacht_id_hash: SHA256("MYSTIC_2025_001")              │
│    - buyer_email: owner@superyacht-mystic.com              │
│    - active: false                                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. Yacht installer (DMG) runs on yacht Mac Studio:         │
│    POST /register                                           │
│    { yacht_id: "MYSTIC_2025_001",                          │
│      yacht_id_hash: "53571185..." }                        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. n8n validates & sends activation email via Outlook:     │
│    To: owner@superyacht-mystic.com                         │
│    Link: https://api.celeste7.ai/.../activate/MYSTIC...    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. Yacht installer polls /check-activation (5s interval):  │
│    Response: { status: "pending" }                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. Owner clicks activation link:                           │
│    - Updates: active=true, activated_at=NOW()              │
│    - Generates: shared_secret (64-char hex)                │
│    - Returns: Success HTML page                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. Next poll returns credentials (ONE TIME):               │
│    { status: "active",                                     │
│      shared_secret: "04690e76b8ffba0...",                  │
│      yacht_id_hash: "53571185..." }                        │
│    - Installer stores in Keychain                          │
│    - credentials_retrieved = true                          │
└─────────────────────────────────────────────────────────────┘

Day 2: DOCUMENT INGESTION
┌─────────────────────────────────────────────────────────────┐
│ 7. Yacht's localhost:5050 service scans NAS folders:       │
│    Found: /nas/Engineering/Fuel/diesel_manual.pdf          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 8. POST /ingest-docs-nas-cloud                             │
│    Headers: x-yacht-id                                     │
│    Body: metadata + binary file                            │
│    { yacht_id, filename, content_type, system_path, ... }  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 9. Ingestion_Docs workflow:                                │
│    - Checks for duplicate (by yacht_id + filename)         │
│    - Uploads to Supabase Storage                           │
│    - Inserts to doc_metadata table                         │
│    - Returns document_id                                   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 10. Triggers Index_docs workflow (async):                  │
│     POST /index-documents                                  │
│     { document_id, storage_path, content_type, ... }       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 11. Index_docs workflow:                                   │
│     - Calls Render service to extract text                 │
│     - Chunks text (1000 chars, 200 overlap)                │
│     - Generates OpenAI embeddings                          │
│     - Stores chunks in search_document_chunks              │
│     - Marks doc_metadata.indexed = true                    │
└─────────────────────────────────────────────────────────────┘

Day 3: SEARCH & RETRIEVAL (not shown in workflows)
┌─────────────────────────────────────────────────────────────┐
│ 12. Crew searches: "diesel fuel filter replacement"        │
│     - Query embedded with OpenAI                           │
│     - Vector search on search_document_chunks              │
│     - Returns relevant chunks + source docs                │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔌 External Service Dependencies

| Service | URL | Purpose | SLA |
|---------|-----|---------|-----|
| **Supabase Cloud HQ** | qvzmkaamzaqxpzbewjxe.supabase.co | Fleet database | Critical |
| **Supabase Cloud PMS** | vzsohavtuotocgrfkfyd.supabase.co | Document database + storage | Critical |
| **n8n Cloud** | api.celeste7.ai | Workflow orchestration | Critical |
| **Microsoft Outlook** | OAuth API | Activation emails | High |
| **Render Text Extraction** | celeste-file-type.onrender.com | PDF/DOCX extraction | High |
| **OpenAI API** | text-embedding-3-small | Embeddings | Medium |
| **Localhost:5050** | Yacht-side service | Document scanning | Yacht-dependent |

---

## 📡 Webhook URLs (Production)

```bash
# Onboarding
POST   https://api.celeste7.ai/webhook/register
POST   https://api.celeste7.ai/webhook/check-activation/:yacht_id
GET    https://api.celeste7.ai/webhook/yacht-activate-webhook-v2/activate/:yacht_id
POST   https://api.celeste7.ai/webhook/celesteos/activation-email

# Document Pipeline
POST   https://api.celeste7.ai/webhook/ingest-docs-nas-cloud
POST   https://api.celeste7.ai/webhook/index-documents
```

---

## 🧪 Testing

### **Test Yacht Credentials**

```
yacht_id: TEST_YACHT_001
yacht_id_hash: 53571185bf07ba57bc3d59eef9ac7d87b4edaf6d6c0ce15c45cb224559c393a7
buyer_email: test@celeste7.ai
shared_secret: 04690e76b8ffba0ff3221977ff0decdbe4b6c24b509e38c91aa7ca8da71df86f
```

### **Test Document Upload**

```bash
curl -X POST https://api.celeste7.ai/webhook/ingest-docs-nas-cloud \
  -H "x-yacht-id: 85fe1119-b04c-41ac-80f1-829d23322598" \
  -F 'data={"yacht_id":"85fe1119-b04c-41ac-80f1-829d23322598","filename":"test.pdf","content_type":"application/pdf","file_size":1024,"system_path":"engineering","doc_type":"manual","system_tag":"general"}' \
  -F 'file=@test.pdf'
```

---

## 🔮 Future Enhancements (Not Yet Implemented)

1. **Token-Based Activation** - `download_links` table exists but unused
2. **DMG Download System** - References in workflows but not active
3. **User Portal** - `user_accounts` + `user_sessions` defined but no UI
4. **Real-time Monitoring** - `alert_rules` configured but no dashboard
5. **Alias Learning Deployment** - `alias_candidates` collecting data, no auto-deploy

---

## 📝 Notes

- **Two Supabase Projects:** HQ for fleet management, PMS for documents
- **Yacht-side Service (localhost:5050):** Not in this repo - separate codebase
- **Text Extraction Service:** External Render deployment
- **n8n Instance:** Cloud-hosted at api.celeste7.ai
- **Credentials Never Logged:** All sensitive data handled securely

---

**Last Updated:** 2026-01-07
**Maintained By:** CelesteOS Engineering Team
