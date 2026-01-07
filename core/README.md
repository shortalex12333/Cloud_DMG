# Core Modules

Shared libraries used across all workflows. These modules are domain-agnostic and reusable.

## Folder Organization

### database/
**Purpose:** Supabase database operations
**Modules:**
- `client.py` - Supabase client initialization
- `fleet_registry.py` - Fleet registry table operations
- `audit_log.py` - Audit logging
- `knowledge_base.py` - Alias candidates, resolution episodes
- `documents.py` - Document metadata operations

**Usage:**
```python
from core.database.fleet_registry import get_yacht, update_yacht, create_yacht
from core.database.audit_log import log_event
```

---

### security/
**Purpose:** Authentication, encryption, validation
**Modules:**
- `hmac.py` - HMAC-SHA256 signature generation/verification
- `secrets.py` - Shared secret generation
- `hashing.py` - SHA-256 hashing utilities
- `tokens.py` - Download token generation

**Usage:**
```python
from core.security.secrets import generate_shared_secret
from core.security.hashing import hash_yacht_id
from core.security.hmac import verify_signature
```

---

### validation/
**Purpose:** Input validation and sanitization
**Modules:**
- `yacht_id.py` - Yacht ID validation
- `email.py` - Email validation
- `parameters.py` - Generic parameter validation
- `schemas.py` - Pydantic models for request/response

**Usage:**
```python
from core.validation.yacht_id import validate_yacht_id_format
from core.validation.schemas import RegisterRequest, ActivationResponse
```
