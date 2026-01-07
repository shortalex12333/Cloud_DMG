# Quick Start: System Validation

**Goal:** Prove CelesteOS Cloud works in 10 minutes

---

## 🚀 Run the Automated Test Suite

```bash
cd /Users/celeste7/Documents/CelesteOS-Cloud
./test_e2e_validation.sh
```

**What it tests:**
1. ✅ Database connectivity
2. ✅ Yacht registration (`POST /register`)
3. ✅ Email activation link generation
4. ✅ Activation flow (`GET /activate/:yacht_id`)
5. ✅ Credential retrieval (`POST /check-activation`)
6. ✅ One-time retrieval enforcement
7. ✅ Database updates (active, shared_secret, timestamps)
8. ✅ Knowledge base data (alias_candidates, resolution_episodes)
9. ✅ Audit logging

**Expected Output:**
```
╔════════════════════════════════════════════════════════════╗
║   CelesteOS Cloud - End-to-End Validation Test Suite      ║
╚════════════════════════════════════════════════════════════╝

[INFO] Test Yacht ID: TEST_E2E_1736277584
[INFO] Test Start Time: Wed Jan  7 18:39:44 GMT 2026

========================================
TEST 1: Database Connectivity
========================================
[PASS] Database connected - 6 yachts in registry

========================================
TEST 2: Create Test Yacht Entry
========================================
[PASS] Test yacht created in fleet_registry

...

Total Tests:  10
Passed:       8-10
Failed:       0-2

Success Rate: 80-100%
✓ System validation: EXCELLENT/ACCEPTABLE
```

---

## 📊 What the Results Tell You

### **90-100% Pass Rate** ✅
```
System Status: PRODUCTION READY for onboarding
Action: Proceed with deployment
Blockers: None
```

### **70-89% Pass Rate** ⚠️
```
System Status: WORKS but has issues
Action: Review failed tests, fix bugs
Blockers: Minor (n8n workflow not deployed, timestamps not set, etc.)
```

### **< 70% Pass Rate** ❌
```
System Status: BROKEN
Action: Debug immediately
Blockers: Critical (database unreachable, workflows not active, etc.)
```

---

## 🔍 Common Issues

### **Issue 1: 404 on /register endpoint**
```
[FAIL] Registration endpoint not found (404)
```

**Cause:** n8n workflow `Signature_Installer_Cloud.json` not deployed/active

**Fix:**
1. Log into n8n at https://api.celeste7.ai
2. Import workflow from `/n8n-workflows/Signature_Installer_Cloud.json`
3. Activate workflow
4. Re-run test

---

### **Issue 2: registered_at is NULL**
```
[FAIL] registered_at is NULL - workflow bug detected
```

**Cause:** Workflow line 198 "Update Registration Timestamp" not executing

**Fix:**
1. Open n8n workflow editor
2. Check node "Update Registration Timestamp" (line 198)
3. Verify SQL query executes
4. Check execution logs for errors

---

### **Issue 3: Audit log is empty**
```
[FAIL] Audit log is empty - monitoring not working
```

**Cause:** Workflows not configured to log events

**Fix:**
1. Add audit_log insert nodes to workflows
2. OR: Accept that monitoring is not yet implemented
3. Mark as "known issue" in SYSTEM_VALIDATION_REPORT.md

---

## 📈 Next Steps Based on Results

### **If All Tests Pass:**
1. ✅ Read `SYSTEM_VALIDATION_REPORT.md` for production readiness gaps
2. ✅ Review Phase 2 "CLEAN UP THE MESS" tasks
3. ✅ Implement monitoring (audit_log population)
4. ✅ Add error handling and retry logic

### **If Some Tests Fail:**
1. ❌ Fix failed tests first
2. ❌ Re-run until 100% pass rate
3. ❌ Document any "known issues" that are acceptable
4. ❌ Then proceed to production hardening

### **If Most Tests Fail:**
1. 🔥 System may not be deployed correctly
2. 🔥 Verify n8n workflows are active
3. 🔥 Check database credentials
4. 🔥 Review `SYSTEM_ARCHITECTURE.md` for correct setup

---

## 🛠️ Manual Validation (If Automated Tests Fail)

### **Test 1: Database Access**
```bash
curl "https://qvzmkaamzaqxpzbewjxe.supabase.co/rest/v1/fleet_registry?select=count" \
  -H "apikey: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF2em1rYWFtemFxeHB6YmV3anhlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM5NzkwNDYsImV4cCI6MjA3OTU1NTA0Nn0.MMzzsRkvbug-u19GBUnD0qLDtMVWEbOf6KE8mAADaxw" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF2em1rYWFtemFxeHB6YmV3anhlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2Mzk3OTA0NiwiZXhwIjoyMDc5NTU1MDQ2fQ.83Bc6rEQl4qNf0MUwJPmMl1n0mhqEo6nVe5fBiRmh8Q"
```

Expected: `[{"count":6}]`

---

### **Test 2: n8n Webhook Availability**
```bash
curl -I "https://api.celeste7.ai/webhook/register"
```

Expected: `HTTP 200` (or 400 with validation error)
NOT: `HTTP 404` (workflow not deployed)

---

### **Test 3: Check Existing Yacht Data**
```bash
curl "https://qvzmkaamzaqxpzbewjxe.supabase.co/rest/v1/fleet_registry?yacht_id=eq.TEST_YACHT_001&select=active,credentials_retrieved" \
  -H "apikey: ..." \
  -H "Authorization: Bearer ..."
```

Expected:
```json
[{
  "active": true,
  "credentials_retrieved": true
}]
```

This proves the system worked at least once!

---

## 📖 Documentation Reference

| Document | Purpose |
|----------|---------|
| `SYSTEM_ARCHITECTURE.md` | Complete system design and data flow |
| `SYSTEM_VALIDATION_REPORT.md` | Detailed analysis of what works vs what's broken |
| `test_e2e_validation.sh` | Automated test suite (this runs the tests) |
| `QUICK_START_VALIDATION.md` | This file - how to run tests |

---

## 💡 Pro Tips

1. **Run tests frequently** - After any code/workflow change
2. **Test in isolation** - Use unique yacht IDs each run
3. **Check n8n execution logs** - See exactly what workflows are doing
4. **Monitor Supabase logs** - See database queries and errors
5. **Save test output** - Compare before/after changes

Example:
```bash
./test_e2e_validation.sh > test_results_$(date +%Y%m%d_%H%M%S).log
```

---

## 🎯 Success Criteria

**Minimum Viable:**
- ✅ Database connectivity works
- ✅ Test yacht can be created
- ✅ Knowledge base has data

**MVP Complete:**
- ✅ All of above PLUS
- ✅ Registration endpoint returns 200
- ✅ Activation flow completes
- ✅ Credentials retrieved successfully

**Production Ready:**
- ✅ All of above PLUS
- ✅ 100% test pass rate over 10 runs
- ✅ Audit logging works
- ✅ Error handling tested
- ✅ Performance baseline established

---

**Remember:** Tests don't lie. If they fail, the system is broken. Fix it, then re-test.
