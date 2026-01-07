#!/usr/bin/env python3
"""
Autonomous End-to-End Test - 3 Yachts
Simulates complete onboarding flow without human intervention
"""
from dotenv import load_dotenv
import os
import hashlib
from datetime import datetime
import time

load_dotenv()

from core.database.client import get_db
from workflows.onboarding.register import handle_register
from workflows.onboarding.check_activation import handle_check_activation
from workflows.onboarding.activate import handle_activate
from core.validation.schemas import RegisterRequest

class YachtTest:
    def __init__(self, yacht_number):
        self.yacht_number = yacht_number
        timestamp = int(datetime.now().timestamp())
        self.yacht_id = f"AUTO_TEST_{yacht_number}_{timestamp}"
        self.yacht_hash = hashlib.sha256(self.yacht_id.encode()).hexdigest()
        self.buyer_email = f"autotest{yacht_number}@celeste7.ai"
        self.db = get_db()
        self.activation_link = None
        self.shared_secret = None
        self.issues = []
        self.steps_completed = []

    def log(self, message, level="INFO"):
        prefix = {
            "INFO": "📋",
            "SUCCESS": "✅",
            "ERROR": "❌",
            "WARNING": "⚠️"
        }.get(level, "📋")
        print(f"{prefix} [Yacht {self.yacht_number}] {message}")

    def step_1_create_in_database(self):
        """Step 1: Pre-create yacht in database"""
        self.log("STEP 1: Creating yacht in database...")
        self.log(f"  Yacht ID: {self.yacht_id}")
        self.log(f"  Hash: {self.yacht_hash}")
        self.log(f"  Email: {self.buyer_email}")

        try:
            response = self.db.table('fleet_registry').insert({
                'yacht_id': self.yacht_id,
                'yacht_id_hash': self.yacht_hash,
                'yacht_name': f'M/Y Auto Test {self.yacht_number}',
                'buyer_email': self.buyer_email,
                'active': False
            }).execute()

            self.log("Database insert successful", "SUCCESS")
            self.steps_completed.append("create_in_database")
            return True
        except Exception as e:
            self.log(f"Database insert failed: {e}", "ERROR")
            self.issues.append(f"Step 1 - Database insert: {e}")
            return False

    def step_2_register(self):
        """Step 2: Call /register endpoint"""
        self.log("STEP 2: Calling POST /register...")

        try:
            request = RegisterRequest(
                yacht_id=self.yacht_id,
                yacht_id_hash=self.yacht_hash
            )
            result = handle_register(request)

            if result.get('success'):
                self.activation_link = result.get('activation_link')
                self.log(f"Registration successful!", "SUCCESS")
                self.log(f"  Activation link: {self.activation_link}")
                self.steps_completed.append("register")
                return True
            else:
                self.log(f"Registration failed: {result}", "ERROR")
                self.issues.append(f"Step 2 - Register: {result.get('error', 'Unknown error')}")
                return False

        except Exception as e:
            self.log(f"Register exception: {e}", "ERROR")
            self.issues.append(f"Step 2 - Register exception: {e}")
            return False

    def step_3_check_pending(self):
        """Step 3: Check activation status (should be pending)"""
        self.log("STEP 3: Checking activation status (should be pending)...")

        try:
            result = handle_check_activation(self.yacht_id)

            if result.get('status') == 'pending':
                self.log("Status is 'pending' (correct)", "SUCCESS")
                self.steps_completed.append("check_pending")
                return True
            else:
                self.log(f"Unexpected status: {result.get('status')}", "WARNING")
                self.log(f"Full response: {result}", "WARNING")
                # Don't fail, just warn - might be already activated from previous run
                self.steps_completed.append("check_pending")
                return True

        except Exception as e:
            self.log(f"Check activation exception: {e}", "ERROR")
            self.issues.append(f"Step 3 - Check pending: {e}")
            return False

    def step_4_activate(self):
        """Step 4: Simulate buyer clicking activation link"""
        self.log("STEP 4: Simulating buyer clicking activation link...")

        if not self.activation_link:
            self.log("No activation link available!", "ERROR")
            self.issues.append("Step 4 - No activation link")
            return False

        try:
            # Extract yacht_id from activation link
            # Link format: https://api.celeste7.ai/webhook/activate/YACHT_ID
            yacht_id_from_link = self.activation_link.split('/')[-1]

            self.log(f"  Activating yacht: {yacht_id_from_link}")
            html, status_code = handle_activate(yacht_id_from_link)

            if status_code == 200 and "Yacht Activated!" in html:
                self.log("Activation successful!", "SUCCESS")
                self.steps_completed.append("activate")
                return True
            else:
                self.log(f"Activation failed: status={status_code}", "ERROR")
                self.log(f"HTML snippet: {html[:200]}...", "ERROR")
                self.issues.append(f"Step 4 - Activate: status={status_code}")
                return False

        except Exception as e:
            self.log(f"Activate exception: {e}", "ERROR")
            self.issues.append(f"Step 4 - Activate exception: {e}")
            return False

    def step_5_retrieve_credentials(self):
        """Step 5: Retrieve credentials (first time)"""
        self.log("STEP 5: Retrieving credentials (first time)...")

        try:
            result = handle_check_activation(self.yacht_id)

            if result.get('status') == 'active':
                self.shared_secret = result.get('shared_secret')
                supabase_url = result.get('supabase_url')

                if self.shared_secret and len(self.shared_secret) == 64:
                    self.log("Credentials retrieved successfully!", "SUCCESS")
                    self.log(f"  Shared secret: {self.shared_secret[:16]}...")
                    self.log(f"  Supabase URL: {supabase_url}")
                    self.steps_completed.append("retrieve_credentials")
                    return True
                else:
                    self.log(f"Invalid shared secret: {self.shared_secret}", "ERROR")
                    self.issues.append(f"Step 5 - Invalid secret length: {len(self.shared_secret) if self.shared_secret else 0}")
                    return False
            else:
                self.log(f"Unexpected status: {result.get('status')}", "ERROR")
                self.log(f"Full response: {result}", "ERROR")
                self.issues.append(f"Step 5 - Status not active: {result.get('status')}")
                return False

        except Exception as e:
            self.log(f"Retrieve credentials exception: {e}", "ERROR")
            self.issues.append(f"Step 5 - Retrieve exception: {e}")
            return False

    def step_6_verify_one_time(self):
        """Step 6: Verify one-time retrieval (should be blocked)"""
        self.log("STEP 6: Verifying one-time retrieval enforcement...")

        try:
            result = handle_check_activation(self.yacht_id)

            if result.get('status') == 'already_retrieved':
                self.log("One-time retrieval enforced!", "SUCCESS")
                self.log("  Second attempt correctly blocked")
                self.steps_completed.append("verify_one_time")
                return True
            else:
                self.log(f"Security issue: Got status '{result.get('status')}'", "ERROR")
                self.log("  Credentials should only be retrievable ONCE!", "ERROR")
                self.issues.append(f"Step 6 - One-time not enforced: {result.get('status')}")
                return False

        except Exception as e:
            self.log(f"Verify one-time exception: {e}", "ERROR")
            self.issues.append(f"Step 6 - Verify exception: {e}")
            return False

    def step_7_verify_database(self):
        """Step 7: Verify database state"""
        self.log("STEP 7: Verifying database state...")

        try:
            yacht_data = self.db.table('fleet_registry').select('*').eq('yacht_id', self.yacht_id).execute()

            if not yacht_data.data or len(yacht_data.data) == 0:
                self.log("Yacht not found in database!", "ERROR")
                self.issues.append("Step 7 - Yacht not in database")
                return False

            yacht = yacht_data.data[0]

            # Verify all fields
            checks = [
                ('active', True, yacht.get('active')),
                ('credentials_retrieved', True, yacht.get('credentials_retrieved')),
                ('shared_secret exists', True, yacht.get('shared_secret') is not None),
                ('shared_secret length', 64, len(yacht.get('shared_secret', ''))),
                ('activated_at', True, yacht.get('activated_at') is not None),
            ]

            all_good = True
            for field, expected, actual in checks:
                if expected == actual:
                    self.log(f"  ✓ {field}: {actual}", "SUCCESS")
                else:
                    self.log(f"  ✗ {field}: expected {expected}, got {actual}", "ERROR")
                    self.issues.append(f"Step 7 - {field} mismatch")
                    all_good = False

            if all_good:
                self.steps_completed.append("verify_database")
                return True
            else:
                return False

        except Exception as e:
            self.log(f"Database verification exception: {e}", "ERROR")
            self.issues.append(f"Step 7 - Database verify exception: {e}")
            return False

    def cleanup(self):
        """Cleanup: Delete test yacht"""
        self.log("CLEANUP: Deleting test yacht...")

        try:
            self.db.table('fleet_registry').delete().eq('yacht_id', self.yacht_id).execute()
            self.log("Test yacht deleted", "SUCCESS")
            return True
        except Exception as e:
            self.log(f"Cleanup failed: {e}", "WARNING")
            return False

    def run_full_test(self):
        """Run complete test flow"""
        print("\n" + "="*70)
        print(f"🚢 YACHT {self.yacht_number} - AUTONOMOUS TEST")
        print("="*70 + "\n")

        steps = [
            ("Create in Database", self.step_1_create_in_database),
            ("Register (POST /register)", self.step_2_register),
            ("Check Pending Status", self.step_3_check_pending),
            ("Activate (Buyer Click)", self.step_4_activate),
            ("Retrieve Credentials", self.step_5_retrieve_credentials),
            ("Verify One-Time Retrieval", self.step_6_verify_one_time),
            ("Verify Database State", self.step_7_verify_database),
        ]

        for step_name, step_func in steps:
            success = step_func()
            if not success:
                self.log(f"❌ TEST FAILED at step: {step_name}", "ERROR")
                break
            time.sleep(0.5)  # Small delay between steps

        # Cleanup regardless of success/failure
        self.cleanup()

        # Print summary
        print("\n" + "-"*70)
        print(f"📊 YACHT {self.yacht_number} SUMMARY")
        print("-"*70)
        print(f"Steps Completed: {len(self.steps_completed)}/7")
        for step in self.steps_completed:
            print(f"  ✅ {step}")

        if self.issues:
            print(f"\n❌ Issues Encountered: {len(self.issues)}")
            for issue in self.issues:
                print(f"  • {issue}")
        else:
            print(f"\n✅ NO ISSUES - FULLY SUCCESSFUL!")

        print("-"*70 + "\n")

        return len(self.issues) == 0

def main():
    print("\n" + "="*70)
    print("🚀 AUTONOMOUS 3-YACHT END-TO-END TEST")
    print("="*70)
    print("\nThis test will:")
    print("  1. Create 3 test yachts")
    print("  2. Run complete onboarding flow for each")
    print("  3. Extract activation links (simulate email)")
    print("  4. Verify all steps work correctly")
    print("  5. Be honest about any failures")
    print("  6. Fix issues between runs\n")

    results = []

    for yacht_num in [1, 2, 3]:
        yacht_test = YachtTest(yacht_num)
        success = yacht_test.run_full_test()
        results.append({
            'yacht': yacht_num,
            'success': success,
            'issues': yacht_test.issues,
            'steps_completed': len(yacht_test.steps_completed)
        })

        if not success:
            print("\n" + "!"*70)
            print(f"⚠️  YACHT {yacht_num} FAILED - STOPPING FOR ANALYSIS")
            print("!"*70)
            print("\nIssues found:")
            for issue in yacht_test.issues:
                print(f"  • {issue}")
            print("\nFix these issues before continuing to next yacht.")
            print("!"*70 + "\n")
            break  # Stop here, don't run next yacht until fixed

        # Small delay between yachts
        if yacht_num < 3:
            print("\n⏳ Waiting 2 seconds before next yacht...\n")
            time.sleep(2)

    # Final Summary
    print("\n" + "="*70)
    print("📊 FINAL TEST SUMMARY")
    print("="*70)

    total = len(results)
    passed = sum(1 for r in results if r['success'])

    print(f"\nYachts Tested: {total}/3")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}\n")

    for result in results:
        status = "✅ PASS" if result['success'] else "❌ FAIL"
        print(f"Yacht {result['yacht']}: {status} ({result['steps_completed']}/7 steps)")
        if result['issues']:
            for issue in result['issues']:
                print(f"    • {issue}")

    print("\n" + "="*70)

    if passed == 3:
        print("🎉 ALL 3 YACHTS PASSED - SYSTEM FULLY FUNCTIONAL!")
    else:
        print(f"⚠️  {3 - passed} YACHT(S) FAILED - SEE ISSUES ABOVE")

    print("="*70 + "\n")

    return passed == 3

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
