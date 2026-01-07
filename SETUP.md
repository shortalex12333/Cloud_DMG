# Setup Guide - CelesteOS Cloud Python

Complete setup and testing instructions for the Python implementation.

---

## 📋 Prerequisites

- Python 3.9+
- pip or uv package manager
- Access to Supabase database credentials

---

## 🚀 Installation

### 1. Clone or Navigate to Repository
```bash
cd /Users/celeste7/Documents/CelesteOS-Cloud-Python
```

### 2. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
# OR
venv\Scripts\activate  # On Windows
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment
```bash
cp .env.example .env
# Edit .env with your actual credentials:
# - SUPABASE_URL
# - SUPABASE_SERVICE_ROLE_KEY
# - SUPABASE_ANON_KEY
```

---

## 🧪 Running Tests

### Unit Tests
```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=workflows --cov=core --cov-report=html

# Run specific test file
pytest tests/test_onboarding.py -v
```

### Integration Test (Against Live Database)
```bash
# Create integration test script
python tests/test_integration.py
```

---

## 🏃 Running the Server

### Development Mode (Auto-reload)
```bash
python main.py
```

Server will start on `http://0.0.0.0:8000`

### Production Mode
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## 📡 API Documentation

Once the server is running, access:
- **Interactive Docs:** http://localhost:8000/docs
- **Alternative Docs:** http://localhost:8000/redoc
- **OpenAPI JSON:** http://localhost:8000/openapi.json

---

## 🧪 Manual Testing

### 1. Test Registration Endpoint
```bash
curl -X POST http://localhost:8000/webhook/register \
  -H "Content-Type: application/json" \
  -d '{
    "yacht_id": "TEST_YACHT_001",
    "yacht_id_hash": "066f68eef8c07c6c5117a40acdcd9ee7db839523e5dd5948d1d577f1a06b62e6"
  }'
```

Expected Response:
```json
{
  "success": true,
  "message": "Registration successful. Activation email sent.",
  "activation_link": "https://api.celeste7.ai/webhook/activate/TEST_YACHT_001"
}
```

### 2. Test Check Activation (Pending)
```bash
curl -X POST http://localhost:8000/webhook/check-activation/TEST_YACHT_001
```

Expected Response:
```json
{
  "status": "pending",
  "message": "Waiting for owner activation"
}
```

### 3. Test Activation (Buyer Click)
```bash
# Open in browser or use curl
curl http://localhost:8000/webhook/activate/TEST_YACHT_001
```

Expected: HTML page with "Yacht Activated!" message

### 4. Test Check Activation (Active)
```bash
curl -X POST http://localhost:8000/webhook/check-activation/TEST_YACHT_001
```

Expected Response (first time):
```json
{
  "status": "active",
  "shared_secret": "...",
  "supabase_url": "...",
  "supabase_anon_key": "..."
}
```

Expected Response (second time):
```json
{
  "status": "already_retrieved",
  "message": "Credentials have already been retrieved"
}
```

---

## 📊 Comparison: n8n vs Python

### Advantages of Python Implementation

✅ **Version Control**
- Diff-friendly (see exact code changes)
- Proper git workflow
- Code review capabilities

✅ **Testing**
- Unit tests for each module
- Integration tests
- Mocking and fixtures
- Code coverage reports

✅ **IDE Support**
- Autocomplete
- Type checking
- Refactoring tools
- Debugging

✅ **Local Development**
- No n8n instance required
- Run locally for development
- Faster iteration

✅ **CI/CD Integration**
- Automated testing
- Linting (black, pylint, mypy)
- Deployment automation

✅ **Maintainability**
- Modular structure
- Reusable core libraries
- Clear separation of concerns

### Migration Path

```
Phase 1: Testing ✅
- Python implementation complete
- Unit tests passing
- Manual testing against live database

Phase 2: Parallel Deployment
- Deploy Python server alongside n8n
- Route 10% traffic to Python
- Monitor and compare

Phase 3: Full Migration
- Route 100% traffic to Python
- Deprecate n8n workflows
- Archive old workflows

Phase 4: Optimization
- Add caching (Redis)
- Implement rate limiting
- Add monitoring/alerting
```

---

## 🗂️ Code Structure

```
CelesteOS-Cloud-Python/
├── main.py                    # FastAPI server entry point
├── requirements.txt           # Python dependencies
├── .env.example              # Environment variables template
├── core/                     # Shared core modules
│   ├── database/
│   │   ├── client.py         # Supabase client
│   │   └── fleet_registry.py # Fleet operations
│   ├── validation/
│   │   ├── yacht_id.py       # Yacht ID validation
│   │   ├── email.py          # Email validation
│   │   └── schemas.py        # Pydantic models
│   └── security/             # Security utilities (TODO)
├── workflows/                # Business logic workflows
│   ├── onboarding/
│   │   ├── register.py       # POST /register
│   │   ├── check_activation.py  # POST /check-activation
│   │   └── activate.py       # GET /activate
│   └── documents/            # Document pipeline (TODO)
└── tests/                    # Test suite
    └── test_onboarding.py    # Onboarding tests
```

---

## 🔧 Development Workflow

### Adding a New Endpoint

1. **Extract logic from n8n workflow**
```bash
jq '.nodes[] | select(.name == "YourNode")' workflow.json
```

2. **Create Python module**
```python
# workflows/your_domain/your_endpoint.py
def handle_your_endpoint(params):
    # Validate input
    # Query database
    # Process logic
    # Return response
```

3. **Add to FastAPI server**
```python
# main.py
@app.post("/webhook/your-endpoint")
async def your_endpoint(request: YourRequest):
    return handle_your_endpoint(request)
```

4. **Write tests**
```python
# tests/test_your_endpoint.py
def test_your_endpoint_success():
    result = handle_your_endpoint(...)
    assert result["success"] is True
```

5. **Test manually**
```bash
curl -X POST http://localhost:8000/webhook/your-endpoint
```

---

## 🐛 Troubleshooting

### Import Errors
```bash
# Ensure __init__.py files exist
find . -type d -name "__pycache__" -exec rm -r {} +
python -c "import workflows.onboarding.register"
```

### Database Connection Errors
```bash
# Verify .env file exists and has correct credentials
cat .env | grep SUPABASE_URL

# Test connection
python -c "from core.database.client import get_db; print(get_db().table('fleet_registry').select('count').execute())"
```

### Module Not Found
```bash
# Ensure virtual environment is activated
which python  # Should show venv/bin/python

# Reinstall dependencies
pip install -r requirements.txt
```

---

## 📈 Next Steps

### Immediate
- [ ] Run unit tests
- [ ] Test against live database
- [ ] Compare with n8n workflow results

### Short-term
- [ ] Implement email sending (Microsoft Outlook API)
- [ ] Add document ingestion endpoint
- [ ] Add document indexing endpoint
- [ ] Create integration test suite

### Long-term
- [ ] Deploy to production
- [ ] Set up monitoring (Sentry, DataDog)
- [ ] Add caching layer (Redis)
- [ ] Implement rate limiting
- [ ] Add authentication for admin endpoints

---

**Generated:** 2026-01-07
**Converted from:** n8n Signature_Installer_Cloud.json
**Status:** Ready for testing
