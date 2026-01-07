#!/bin/bash
# Deployment Verification Script
# Tests if military-grade security features are active

set -e

DEPLOYMENT_URL="https://cloud-dmg.onrender.com"
PASS=0
FAIL=0

echo "============================================"
echo "  CelesteOS Security Deployment Verification"
echo "============================================"
echo ""

# Test 1: Check version
echo "[TEST 1] Checking deployment version..."
VERSION=$(curl -s $DEPLOYMENT_URL/ | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
if [ "$VERSION" = "2.0.0-secure" ]; then
    echo "✅ PASS: Version is 2.0.0-secure (military-grade security active)"
    ((PASS++))
else
    echo "❌ FAIL: Version is $VERSION (expected 2.0.0-secure)"
    echo "   → Security features NOT deployed"
    ((FAIL++))
fi
echo ""

# Test 2: Check security headers
echo "[TEST 2] Checking security headers..."
HEADERS=$(curl -sI $DEPLOYMENT_URL/)

if echo "$HEADERS" | grep -qi "x-frame-options.*DENY"; then
    echo "✅ PASS: X-Frame-Options header present"
    ((PASS++))
else
    echo "❌ FAIL: X-Frame-Options header missing"
    ((FAIL++))
fi

if echo "$HEADERS" | grep -qi "strict-transport-security"; then
    echo "✅ PASS: Strict-Transport-Security header present"
    ((PASS++))
else
    echo "❌ FAIL: Strict-Transport-Security header missing"
    ((FAIL++))
fi

if echo "$HEADERS" | grep -qi "x-request-id"; then
    echo "✅ PASS: X-Request-ID header present (request tracking active)"
    ((PASS++))
else
    echo "❌ FAIL: X-Request-ID header missing"
    ((FAIL++))
fi
echo ""

# Test 3: Check health endpoint
echo "[TEST 3] Checking health endpoint..."
HEALTH=$(curl -s $DEPLOYMENT_URL/health)
if echo "$HEALTH" | grep -q "healthy"; then
    echo "✅ PASS: Health endpoint responding"
    ((PASS++))
else
    echo "❌ FAIL: Health endpoint not responding correctly"
    ((FAIL++))
fi
echo ""

# Test 4: Check if API docs are disabled (production mode)
echo "[TEST 4] Checking API docs protection..."
DOCS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" $DEPLOYMENT_URL/docs)
if [ "$DOCS_STATUS" = "404" ] || [ "$DOCS_STATUS" = "401" ]; then
    echo "✅ PASS: API docs protected (status: $DOCS_STATUS)"
    ((PASS++))
else
    echo "⚠️  WARNING: API docs accessible (status: $DOCS_STATUS)"
    echo "   → Should be disabled in production"
    ((FAIL++))
fi
echo ""

# Test 5: Rate limiting (light test - just check if it responds)
echo "[TEST 5] Testing rate limiting..."
echo "   Making 3 quick requests..."
for i in 1 2 3; do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" $DEPLOYMENT_URL/)
    echo "   Request $i: HTTP $STATUS"
    sleep 0.5
done
echo "   ℹ️  Note: Full rate limit test requires >60 requests"
echo "   ℹ️  If all requests succeeded (200), rate limiting may not be active"
echo ""

# Summary
echo "============================================"
echo "  Test Results Summary"
echo "============================================"
echo "Passed: $PASS"
echo "Failed: $FAIL"
echo ""

if [ $FAIL -eq 0 ]; then
    echo "🎉 ALL TESTS PASSED - MILITARY-GRADE SECURITY ACTIVE"
    echo ""
    echo "Security Features Verified:"
    echo "  ✅ Version 2.0.0-secure deployed"
    echo "  ✅ Security headers active"
    echo "  ✅ Request tracking enabled"
    echo "  ✅ API documentation protected"
    echo "  ✅ System healthy"
    echo ""
    exit 0
else
    echo "⚠️  SOME TESTS FAILED"
    echo ""
    echo "Action Required:"
    if [ "$VERSION" != "2.0.0-secure" ]; then
        echo "  1. Check Render deployment status"
        echo "  2. Trigger manual deployment if auto-deploy failed"
        echo "  3. Add environment variables to Render:"
        echo "     - ENVIRONMENT=production"
        echo "     - ALLOWED_ORIGINS=https://celeste7.ai,https://www.celeste7.ai,https://api.celeste7.ai"
        echo "     - ALLOWED_HOSTS=cloud-dmg.onrender.com,api.celeste7.ai"
    fi
    echo ""
    exit 1
fi
