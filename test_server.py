#!/usr/bin/env python3
"""
Integration test script - tests FastAPI server with actual HTTP requests
"""
import subprocess
import time
import requests
import sys
import signal

def test_server():
    print("=== STAGE 6: Testing FastAPI Server ===\n")

    # Start server
    print("Starting server...")
    proc = subprocess.Popen(
        [sys.executable, "main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    # Wait for server to start
    time.sleep(2)

    try:
        # Test 1: Root endpoint
        print("Test 1: GET / (root endpoint)")
        resp = requests.get("http://localhost:8000/", timeout=5)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert "service" in data
        assert data["service"] == "CelesteOS Cloud API"
        print("✅ Root endpoint works\n")

        # Test 2: Health check
        print("Test 2: GET /health")
        resp = requests.get("http://localhost:8000/health", timeout=5)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        print("✅ Health check works\n")

        # Test 3: Register endpoint (validation error expected - no db)
        print("Test 3: POST /webhook/register (invalid input)")
        resp = requests.post(
            "http://localhost:8000/webhook/register",
            json={"yacht_id": "invalid!@#", "yacht_id_hash": "short"},
            timeout=5
        )
        assert resp.status_code == 422, f"Expected 422 validation error, got {resp.status_code}"
        print("✅ Register endpoint validates input\n")

        # Test 4: Check activation endpoint (invalid yacht_id)
        print("Test 4: POST /webhook/check-activation/invalid!@#")
        resp = requests.post(
            "http://localhost:8000/webhook/check-activation/invalid!@#",
            timeout=5
        )
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code}"
        print("✅ Check-activation endpoint validates yacht_id\n")

        # Test 5: Activate endpoint (invalid yacht_id)
        print("Test 5: GET /webhook/activate/invalid!@#")
        resp = requests.get(
            "http://localhost:8000/webhook/activate/invalid!@#",
            timeout=5
        )
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code}"
        assert "text/html" in resp.headers["content-type"]
        print("✅ Activate endpoint validates yacht_id\n")

        # Test 6: OpenAPI docs
        print("Test 6: GET /docs (OpenAPI documentation)")
        resp = requests.get("http://localhost:8000/docs", timeout=5)
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        print("✅ OpenAPI docs accessible\n")

        print("✅ Stage 6 Complete: All server tests passed (6/6)\n")
        return True

    except AssertionError as e:
        print(f"❌ Test failed: {e}\n")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}\n")
        return False
    finally:
        # Stop server
        print("Stopping server...")
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=2)
        print("Server stopped\n")

if __name__ == "__main__":
    success = test_server()
    sys.exit(0 if success else 1)
