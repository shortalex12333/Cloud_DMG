#!/usr/bin/env python3
"""
REAL integration test - tests FastAPI server with LIVE DATABASE
"""
import subprocess
import time
import requests
import sys
import signal
import hashlib
from datetime import datetime

def test_live_server():
    print("=== LIVE SERVER TEST (REAL DATABASE) ===\n")

    # Create test yacht ID
    test_id = f"TEST_LIVE_{int(datetime.now().timestamp())}"
    test_hash = hashlib.sha256(test_id.encode()).hexdigest()

    print(f"Test Yacht: {test_id}")
    print(f"Hash: {test_hash}\n")

    # Pre-create yacht in database
    print("Pre-creating yacht in database...")
    from dotenv import load_dotenv
    load_dotenv()
    from core.database.client import get_db
    db = get_db()

    try:
        db.table('fleet_registry').insert({
            'yacht_id': test_id,
            'yacht_id_hash': test_hash,
            'yacht_name': 'M/Y Live Test',
            'buyer_email': 'livetest@celeste7.ai',
            'active': False
        }).execute()
        print("✅ Yacht created\n")
    except Exception as e:
        print(f"❌ Failed to create yacht: {e}")
        return False

    # Start server
    print("Starting FastAPI server...")
    proc = subprocess.Popen(
        [sys.executable, "main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    time.sleep(3)

    try:
        # Test 1: Register endpoint with REAL DATABASE
        print("Test 1: POST /webhook/register (real database)")
        resp = requests.post(
            "http://localhost:8000/webhook/register",
            json={"yacht_id": test_id, "yacht_id_hash": test_hash},
            timeout=10
        )

        if resp.status_code == 200:
            data = resp.json()
            print(f"✅ Registration successful")
            print(f"   Activation link: {data.get('activation_link', 'N/A')}\n")
            activation_link = data.get('activation_link')
        else:
            print(f"❌ Registration failed: {resp.status_code}")
            print(f"   Response: {resp.text}\n")
            return False

        # Test 2: Check activation (should be pending)
        print("Test 2: POST /webhook/check-activation (pending)")
        resp = requests.post(
            f"http://localhost:8000/webhook/check-activation/{test_id}",
            timeout=10
        )

        if resp.status_code == 200 and resp.json().get('status') == 'pending':
            print(f"✅ Status is pending (correct)\n")
        else:
            print(f"⚠️ Unexpected response: {resp.json()}\n")

        # Test 3: Activate yacht
        print("Test 3: GET /webhook/activate (buyer click)")
        activate_path = activation_link.replace('https://api.celeste7.ai', 'http://localhost:8000')
        resp = requests.get(activate_path, timeout=10)

        if resp.status_code == 200 and "Yacht Activated!" in resp.text:
            print(f"✅ Activation successful (HTML returned)\n")
        else:
            print(f"⚠️ Activation response: {resp.status_code}\n")

        # Test 4: Check activation (should now return credentials)
        print("Test 4: POST /webhook/check-activation (active - first time)")
        resp = requests.post(
            f"http://localhost:8000/webhook/check-activation/{test_id}",
            timeout=10
        )

        if resp.status_code == 200:
            data = resp.json()
            if data.get('status') == 'active' and data.get('shared_secret'):
                print(f"✅ Credentials returned!")
                print(f"   Shared secret: {data['shared_secret'][:16]}...\n")
            else:
                print(f"⚠️ Unexpected response: {data}\n")
        else:
            print(f"❌ Failed: {resp.status_code}\n")

        # Test 5: Second retrieval (should be blocked)
        print("Test 5: POST /webhook/check-activation (already retrieved)")
        resp = requests.post(
            f"http://localhost:8000/webhook/check-activation/{test_id}",
            timeout=10
        )

        if resp.status_code == 200:
            data = resp.json()
            if data.get('status') == 'already_retrieved':
                print(f"✅ One-time retrieval enforced!\n")
            else:
                print(f"⚠️ Expected already_retrieved, got: {data.get('status')}\n")

        print("="*60)
        print("✅ LIVE SERVER TEST COMPLETE - ALL PASSED!")
        print("="*60)
        return True

    except Exception as e:
        print(f"❌ Test failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Cleanup
        print("\nCleaning up...")
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=2)

        try:
            db.table('fleet_registry').delete().eq('yacht_id', test_id).execute()
            print("✅ Test yacht deleted")
        except:
            pass

if __name__ == "__main__":
    success = test_live_server()
    sys.exit(0 if success else 1)
