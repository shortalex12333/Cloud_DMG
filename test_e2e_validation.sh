#!/bin/bash
#
# CelesteOS Cloud - End-to-End Validation Test Suite
# ====================================================
# Tests the complete onboarding and document pipeline to prove the system works
#
# Usage: ./test_e2e_validation.sh
# Requirements: curl, jq, openssl

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SUPABASE_URL="https://qvzmkaamzaqxpzbewjxe.supabase.co"
SUPABASE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF2em1rYWFtemFxeHB6YmV3anhlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2Mzk3OTA0NiwiZXhwIjoyMDc5NTU1MDQ2fQ.83Bc6rEQl4qNf0MUwJPmMl1n0mhqEo6nVe5fBiRmh8Q"
API_BASE="https://api.celeste7.ai/webhook"
TEST_YACHT_ID="TEST_E2E_$(date +%s)"
BUYER_EMAIL="test@celeste7.ai"

# Test results tracking
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Utility functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
    PASSED_TESTS=$((PASSED_TESTS + 1))
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $1"
    FAILED_TESTS=$((FAILED_TESTS + 1))
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

run_test() {
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}TEST $TOTAL_TESTS: $1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

# Generate yacht_id_hash
generate_hash() {
    echo -n "$1" | openssl dgst -sha256 | sed 's/^.* //'
}

# Database query helper
db_query() {
    local query="$1"
    curl -s "${SUPABASE_URL}/rest/v1/rpc" \
        -H "apikey: ${SUPABASE_KEY}" \
        -H "Authorization: Bearer ${SUPABASE_KEY}" \
        -H "Content-Type: application/json" \
        -d "{\"query\":\"${query}\"}"
}

# Direct table query
db_select() {
    local table="$1"
    local where="$2"
    curl -s "${SUPABASE_URL}/rest/v1/${table}?${where}" \
        -H "apikey: ${SUPABASE_KEY}" \
        -H "Authorization: Bearer ${SUPABASE_KEY}"
}

# Cleanup function
cleanup() {
    log_info "Cleaning up test data..."
    curl -s -X DELETE "${SUPABASE_URL}/rest/v1/fleet_registry?yacht_id=eq.${TEST_YACHT_ID}" \
        -H "apikey: ${SUPABASE_KEY}" \
        -H "Authorization: Bearer ${SUPABASE_KEY}" > /dev/null
    log_success "Test yacht deleted: ${TEST_YACHT_ID}"
}

# Main test suite
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║   CelesteOS Cloud - End-to-End Validation Test Suite      ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
log_info "Test Yacht ID: ${TEST_YACHT_ID}"
log_info "Test Start Time: $(date)"
echo ""

# ============================================================================
# TEST 1: Database Connectivity
# ============================================================================
run_test "Database Connectivity"

YACHT_COUNT=$(db_select "fleet_registry" "select=count" | jq -r '.[0].count')
if [ -n "$YACHT_COUNT" ]; then
    log_success "Database connected - ${YACHT_COUNT} yachts in registry"
else
    log_error "Database connection failed"
    exit 1
fi

# ============================================================================
# TEST 2: Pre-create Test Yacht in Fleet Registry
# ============================================================================
run_test "Create Test Yacht Entry"

YACHT_HASH=$(generate_hash "$TEST_YACHT_ID")
log_info "Yacht ID: ${TEST_YACHT_ID}"
log_info "Yacht Hash: ${YACHT_HASH}"

# Create yacht entry
RESPONSE=$(curl -s -X POST "${SUPABASE_URL}/rest/v1/fleet_registry" \
    -H "apikey: ${SUPABASE_KEY}" \
    -H "Authorization: Bearer ${SUPABASE_KEY}" \
    -H "Content-Type: application/json" \
    -H "Prefer: return=representation" \
    -d "{
        \"yacht_id\": \"${TEST_YACHT_ID}\",
        \"yacht_id_hash\": \"${YACHT_HASH}\",
        \"yacht_name\": \"M/Y E2E Test\",
        \"buyer_email\": \"${BUYER_EMAIL}\",
        \"active\": false
    }")

if echo "$RESPONSE" | jq -e '.[0].yacht_id' > /dev/null 2>&1; then
    log_success "Test yacht created in fleet_registry"
else
    log_error "Failed to create yacht entry"
    echo "$RESPONSE"
    exit 1
fi

# ============================================================================
# TEST 3: Onboarding - Registration Endpoint
# ============================================================================
run_test "POST /register - Yacht Registration"

REGISTER_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/register" \
    -H "Content-Type: application/json" \
    -d "{
        \"yacht_id\": \"${TEST_YACHT_ID}\",
        \"yacht_id_hash\": \"${YACHT_HASH}\"
    }")

HTTP_CODE=$(echo "$REGISTER_RESPONSE" | tail -n1)
BODY=$(echo "$REGISTER_RESPONSE" | sed '$d')

log_info "HTTP Status: ${HTTP_CODE}"

if [ "$HTTP_CODE" == "200" ]; then
    log_success "Registration endpoint returned 200"
    echo "$BODY" | jq '.' || echo "$BODY"

    # Check for expected response fields
    if echo "$BODY" | jq -e '.success' > /dev/null 2>&1; then
        log_success "Response contains 'success' field"
    else
        log_warn "Response missing 'success' field"
    fi

    if echo "$BODY" | jq -e '.activation_link' > /dev/null 2>&1; then
        ACTIVATION_LINK=$(echo "$BODY" | jq -r '.activation_link')
        log_success "Activation link generated: ${ACTIVATION_LINK}"
    else
        log_warn "Response missing 'activation_link' field"
    fi
elif [ "$HTTP_CODE" == "404" ]; then
    log_error "Registration endpoint not found (404) - n8n workflow may not be deployed"
    log_warn "Skipping remaining onboarding tests"
    SKIP_ONBOARDING=true
else
    log_error "Registration failed with HTTP ${HTTP_CODE}"
    echo "$BODY"
fi

# ============================================================================
# TEST 4: Verify registered_at Timestamp
# ============================================================================
if [ "$SKIP_ONBOARDING" != "true" ]; then
    run_test "Verify registered_at Timestamp"

    sleep 2  # Give workflow time to complete

    YACHT_DATA=$(db_select "fleet_registry" "yacht_id=eq.${TEST_YACHT_ID}&select=registered_at,active")
    REGISTERED_AT=$(echo "$YACHT_DATA" | jq -r '.[0].registered_at')

    log_info "registered_at: ${REGISTERED_AT}"

    if [ "$REGISTERED_AT" != "null" ] && [ -n "$REGISTERED_AT" ]; then
        log_success "registered_at timestamp was set"
    else
        log_error "registered_at is NULL - workflow bug detected"
    fi
fi

# ============================================================================
# TEST 5: Check Activation Status (Pending)
# ============================================================================
if [ "$SKIP_ONBOARDING" != "true" ]; then
    run_test "POST /check-activation - Pending Status"

    CHECK_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/check-activation/${TEST_YACHT_ID}")
    HTTP_CODE=$(echo "$CHECK_RESPONSE" | tail -n1)
    BODY=$(echo "$CHECK_RESPONSE" | sed '$d')

    log_info "HTTP Status: ${HTTP_CODE}"

    if [ "$HTTP_CODE" == "200" ]; then
        STATUS=$(echo "$BODY" | jq -r '.status')
        log_info "Activation status: ${STATUS}"

        if [ "$STATUS" == "pending" ]; then
            log_success "Yacht status is 'pending' (correct before activation)"
        else
            log_error "Expected status 'pending', got '${STATUS}'"
        fi
    elif [ "$HTTP_CODE" == "404" ]; then
        log_error "Check-activation endpoint not found (404)"
    else
        log_error "Check-activation failed with HTTP ${HTTP_CODE}"
    fi
fi

# ============================================================================
# TEST 6: Simulate Buyer Activation
# ============================================================================
if [ "$SKIP_ONBOARDING" != "true" ] && [ -n "$ACTIVATION_LINK" ]; then
    run_test "GET /activate/:yacht_id - Simulate Buyer Click"

    ACTIVATE_RESPONSE=$(curl -s -w "\n%{http_code}" "$ACTIVATION_LINK")
    HTTP_CODE=$(echo "$ACTIVATE_RESPONSE" | tail -n1)
    BODY=$(echo "$ACTIVATE_RESPONSE" | sed '$d')

    log_info "HTTP Status: ${HTTP_CODE}"

    if [ "$HTTP_CODE" == "200" ]; then
        log_success "Activation endpoint returned 200"

        # Check if HTML success page returned
        if echo "$BODY" | grep -q "Yacht Activated"; then
            log_success "Success page returned (HTML contains 'Yacht Activated')"
        else
            log_warn "Response doesn't look like expected success page"
        fi

        # Verify database updated
        sleep 2
        YACHT_DATA=$(db_select "fleet_registry" "yacht_id=eq.${TEST_YACHT_ID}&select=active,activated_at,shared_secret")
        ACTIVE=$(echo "$YACHT_DATA" | jq -r '.[0].active')
        ACTIVATED_AT=$(echo "$YACHT_DATA" | jq -r '.[0].activated_at')
        SHARED_SECRET=$(echo "$YACHT_DATA" | jq -r '.[0].shared_secret')

        log_info "active: ${ACTIVE}"
        log_info "activated_at: ${ACTIVATED_AT}"
        log_info "shared_secret: ${SHARED_SECRET:0:16}... (truncated)"

        if [ "$ACTIVE" == "true" ]; then
            log_success "Yacht marked as active in database"
        else
            log_error "Yacht not marked as active"
        fi

        if [ "$ACTIVATED_AT" != "null" ] && [ -n "$ACTIVATED_AT" ]; then
            log_success "activated_at timestamp was set"
        else
            log_error "activated_at is NULL"
        fi

        if [ ${#SHARED_SECRET} -eq 64 ]; then
            log_success "shared_secret generated (64 characters)"
        else
            log_error "shared_secret not generated or invalid length: ${#SHARED_SECRET}"
        fi

    elif [ "$HTTP_CODE" == "404" ]; then
        log_error "Activation endpoint not found (404)"
    else
        log_error "Activation failed with HTTP ${HTTP_CODE}"
    fi
elif [ "$SKIP_ONBOARDING" != "true" ]; then
    log_warn "Skipping activation test - no activation link from registration"
fi

# ============================================================================
# TEST 7: Retrieve Credentials (One-Time)
# ============================================================================
if [ "$SKIP_ONBOARDING" != "true" ]; then
    run_test "POST /check-activation - Retrieve Credentials"

    sleep 2

    CRED_RESPONSE=$(curl -s -X POST "${API_BASE}/check-activation/${TEST_YACHT_ID}")
    STATUS=$(echo "$CRED_RESPONSE" | jq -r '.status')
    SHARED_SECRET=$(echo "$CRED_RESPONSE" | jq -r '.shared_secret')

    log_info "Status: ${STATUS}"

    if [ "$STATUS" == "active" ]; then
        log_success "Yacht status is 'active'"

        if [ ${#SHARED_SECRET} -eq 64 ]; then
            log_success "shared_secret retrieved (64 characters)"
            log_info "Secret (first 16 chars): ${SHARED_SECRET:0:16}..."
        else
            log_error "shared_secret not returned or invalid"
        fi

    elif [ "$STATUS" == "already_retrieved" ]; then
        log_warn "Credentials already retrieved (possible from previous test run)"
    else
        log_error "Unexpected status: ${STATUS}"
    fi
fi

# ============================================================================
# TEST 8: Verify One-Time Retrieval Enforcement
# ============================================================================
if [ "$SKIP_ONBOARDING" != "true" ]; then
    run_test "POST /check-activation - Verify One-Time Enforcement"

    SECOND_RESPONSE=$(curl -s -X POST "${API_BASE}/check-activation/${TEST_YACHT_ID}")
    STATUS=$(echo "$SECOND_RESPONSE" | jq -r '.status')
    SHARED_SECRET=$(echo "$SECOND_RESPONSE" | jq -r '.shared_secret')

    log_info "Status: ${STATUS}"

    if [ "$STATUS" == "already_retrieved" ]; then
        log_success "One-time retrieval enforced - status is 'already_retrieved'"
    else
        log_error "Expected 'already_retrieved', got '${STATUS}'"
    fi

    if [ "$SHARED_SECRET" == "null" ] || [ -z "$SHARED_SECRET" ]; then
        log_success "shared_secret not returned on second attempt"
    else
        log_error "shared_secret returned again - security vulnerability!"
    fi

    # Verify credentials_retrieved flag
    YACHT_DATA=$(db_select "fleet_registry" "yacht_id=eq.${TEST_YACHT_ID}&select=credentials_retrieved")
    CRED_RETRIEVED=$(echo "$YACHT_DATA" | jq -r '.[0].credentials_retrieved')

    if [ "$CRED_RETRIEVED" == "true" ]; then
        log_success "credentials_retrieved flag set in database"
    else
        log_error "credentials_retrieved flag not set"
    fi
fi

# ============================================================================
# TEST 9: Knowledge Base Data Validation
# ============================================================================
run_test "Knowledge Base - Data Validation"

ALIAS_COUNT=$(db_select "alias_candidates" "select=count" | jq -r '.[0].count')
EPISODE_COUNT=$(db_select "resolution_episodes" "select=count" | jq -r '.[0].count')

log_info "Alias Candidates: ${ALIAS_COUNT}"
log_info "Resolution Episodes: ${EPISODE_COUNT}"

if [ "$ALIAS_COUNT" -gt 0 ]; then
    log_success "Alias candidates exist (${ALIAS_COUNT} entries)"
else
    log_warn "No alias candidates found"
fi

if [ "$EPISODE_COUNT" -gt 0 ]; then
    log_success "Resolution episodes exist (${EPISODE_COUNT} entries)"
else
    log_warn "No resolution episodes found"
fi

# ============================================================================
# TEST 10: Audit Log Validation
# ============================================================================
run_test "Audit Log - Monitoring Validation"

AUDIT_COUNT=$(db_select "audit_log" "select=count" | jq -r '.[0].count')
log_info "Audit log entries: ${AUDIT_COUNT}"

if [ "$AUDIT_COUNT" -gt 0 ]; then
    log_success "Audit log has ${AUDIT_COUNT} entries"
else
    log_error "Audit log is empty - monitoring not working"
fi

# ============================================================================
# CLEANUP
# ============================================================================
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                      CLEANUP                               ║"
echo "╚════════════════════════════════════════════════════════════╝"
cleanup

# ============================================================================
# FINAL REPORT
# ============================================================================
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                   TEST RESULTS                             ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Total Tests:  ${TOTAL_TESTS}"
echo -e "${GREEN}Passed:${NC}       ${PASSED_TESTS}"
echo -e "${RED}Failed:${NC}       ${FAILED_TESTS}"
echo ""

SUCCESS_RATE=$((PASSED_TESTS * 100 / TOTAL_TESTS))
echo "Success Rate: ${SUCCESS_RATE}%"

if [ $SUCCESS_RATE -ge 90 ]; then
    echo -e "${GREEN}✓ System validation: EXCELLENT${NC}"
elif [ $SUCCESS_RATE -ge 70 ]; then
    echo -e "${YELLOW}⚠ System validation: ACCEPTABLE (needs improvement)${NC}"
else
    echo -e "${RED}✗ System validation: FAILED (critical issues)${NC}"
fi

echo ""
echo "Test End Time: $(date)"
echo ""

# Exit with appropriate code
if [ $FAILED_TESTS -eq 0 ]; then
    exit 0
else
    exit 1
fi
