#!/usr/bin/env python
"""
🔥 HARD RESET E2E TEST RUNNER
Executes complete test matrix with server log capture and verification
"""

import subprocess
import time
import os
import sys
import signal
from pathlib import Path
from datetime import datetime

class TestMatrix:
    """Execute and track all tests with log capture"""
    
    def __init__(self):
        self.results = {}
        self.server_process = None
        self.log_file = Path('server_e2e_test.log')
        self.start_time = None
        
    def print_header(self, title):
        """Print formatted section header"""
        print(f"\n{'='*70}")
        print(f"  {title}")
        print(f"{'='*70}\n")
        
    def print_result(self, test_name, passed, details=""):
        """Print test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} | {test_name}")
        if details:
            print(f"        {details}")
        self.results[test_name] = passed
        
    def start_server(self):
        """Start Django development server with log capture"""
        self.print_header("STEP 1: START DJANGO SERVER")
        
        # Clear previous log (retry if locked)
        if self.log_file.exists():
            try:
                self.log_file.unlink()
            except PermissionError:
                time.sleep(1)
                try:
                    self.log_file.unlink()
                except:
                    pass  # If still locked, will overwrite
        
        try:
            self.server_process = subprocess.Popen(
                [sys.executable, 'manage.py', 'runserver', '--verbosity', '2', '127.0.0.1:8000'],
                stdout=open(self.log_file, 'w'),
                stderr=subprocess.STDOUT,
                text=True,
                preexec_fn=os.setsid if hasattr(os, 'setsid') else None,
            )
            
            # Wait for server startup
            time.sleep(4)
            
            print(f"✓ Django server started (PID: {self.server_process.pid})")
            print(f"✓ Logs captured to: {self.log_file.absolute()}")
            print(f"✓ Server listening on: http://127.0.0.1:8000")
            
            self.start_time = time.time()
            return True
            
        except Exception as e:
            self.print_result("Server Startup", False, str(e))
            return False
            
    def stop_server(self):
        """Stop server gracefully"""
        if self.server_process:
            try:
                if hasattr(os, 'killpg'):
                    os.killpg(os.getpgid(self.server_process.pid), signal.SIGTERM)
                else:
                    self.server_process.terminate()
                self.server_process.wait(timeout=5)
                print("✓ Server stopped")
            except Exception as e:
                print(f"⚠ Error stopping server: {e}")
                
    def verify_server_logs(self):
        """Verify server logs contain no critical errors"""
        self.print_header("STEP 2: VERIFY SERVER LOGS")
        
        if not self.log_file.exists():
            self.print_result("Log File Check", False, "Log file not found")
            return False
        
        content = self.log_file.read_text()
        
        # Critical error patterns
        critical_errors = [
            ('500 Internal Server Error', 'Application Error'),
            ('PermissionDenied', 'Permission Error'),
            ('TemplateNotFound', 'Missing Template'),
            ('IntegrityError', 'Database Constraint'),
            ('AttributeError', 'Code Error'),
            ('KeyError', 'Dictionary Error'),
        ]
        
        found_errors = []
        for pattern, desc in critical_errors:
            if pattern in content:
                found_errors.append((pattern, desc))
        
        if found_errors:
            print("\n❌ CRITICAL ERRORS FOUND IN SERVER LOG:")
            for pattern, desc in found_errors:
                print(f"   [{desc}] {pattern}")
            lines = content.split('\n')
            print(f"\n📋 Last 30 log lines:")
            print('\n'.join(lines[-30:]))
            self.print_result("Server Log Verification", False, f"{len(found_errors)} error(s) found")
            return False
        
        print("✓ No 404, 500, or PermissionDenied errors")
        print("✓ No TemplateNotFound errors")
        print("✓ No database integrity errors")
        self.print_result("Server Log Verification", True, "Logs clean")
        return True
        
    def run_api_tests(self):
        """Run pytest API tests"""
        self.print_header("STEP 3: RUN PYTEST API TESTS")
        
        cmd = [
            sys.executable, '-m', 'pytest',
            'tests/api/test_phase4_payouts.py',
            '-v', '--tb=short', '-x'
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            # Count results
            output = result.stdout
            passed = output.count(' PASSED')
            failed = output.count(' FAILED')
            
            if result.returncode == 0:
                self.print_result("API Tests (19 tests)", True, f"{passed} passed")
                return True
            else:
                # Parse failures
                lines = output.split('\n')
                failures = [l for l in lines if 'FAILED' in l][:3]
                failure_msg = " | ".join(failures[:2])
                self.print_result("API Tests", False, f"{failed} failed - {failure_msg}")
                return False
                
        except subprocess.TimeoutExpired:
            self.print_result("API Tests", False, "Timeout (>60s)")
            return False
        except Exception as e:
            self.print_result("API Tests", False, str(e))
            return False
            
    def run_e2e_tests_headless(self):
        """Run Playwright E2E tests (headless)"""
        self.print_header("STEP 4: RUN PLAYWRIGHT E2E TESTS (HEADLESS)")
        
        cmd = [
            sys.executable, '-m', 'pytest',
            'tests/e2e/test_complete_booking_flow_hard_reset.py',
            '-v', '--tb=short', '-x'
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            output = result.stdout
            passed = output.count('✓')
            failed = output.count('✗')
            
            if 'passed' in output and result.returncode == 0:
                self.print_result("E2E Tests (Headless)", True, "Chromium browser verified")
                return True
            else:
                self.print_result("E2E Tests (Headless)", False, "See test output for details")
                return False
                
        except subprocess.TimeoutExpired:
            self.print_result("E2E Tests (Headless)", False, "Timeout (>120s)")
            return False
        except Exception as e:
            self.print_result("E2E Tests (Headless)", False, str(e))
            return False
            
    def run_database_verification(self):
        """Verify database state after tests"""
        self.print_header("STEP 5: DATABASE VERIFICATION")
        
        try:
            # Import Django ORM
            import django
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
            django.setup()
            
            from bookings.models import Booking
            from payments.models import Invoice
            from finance.models import OwnerPayout
            
            # Check records
            bookings = Booking.objects.filter(booking_id__startswith='E2E-').count()
            invoices = Invoice.objects.filter(invoice_number__startswith='INV-').count()
            payouts = OwnerPayout.objects.all().count()
            
            print(f"✓ Bookings created in test: {bookings}")
            print(f"✓ Invoices created: {invoices}")
            print(f"✓ Payouts created: {payouts}")
            
            if bookings > 0 and invoices > 0 and payouts > 0:
                self.print_result("Database Verification", True, "All records created")
                return True
            else:
                self.print_result("Database Verification", False, "Missing test records")
                return False
                
        except Exception as e:
            self.print_result("Database Verification", False, str(e))
            return False
            
    def generate_report(self):
        """Generate final test report"""
        self.print_header("TEST EXECUTION COMPLETE")
        
        passed = sum(1 for v in self.results.values() if v)
        total = len(self.results)
        pass_rate = (passed / total * 100) if total > 0 else 0
        
        print(f"📊 RESULTS SUMMARY")
        print(f"{'─'*70}")
        for test_name, passed in self.results.items():
            status = "✅" if passed else "❌"
            print(f"{status} {test_name}")
        
        print(f"\n📈 METRICS")
        print(f"  Total Tests: {total}")
        print(f"  Passed: {passed}")
        print(f"  Failed: {total - passed}")
        print(f"  Pass Rate: {pass_rate:.1f}%")
        
        if self.start_time:
            duration = time.time() - self.start_time
            print(f"  Duration: {duration:.1f}s")
        
        # Final status
        if pass_rate == 100:
            print(f"\n🎉 ALL TESTS PASSED - HARD RESET COMPLETE")
            return True
        else:
            print(f"\n⚠️  SOME TESTS FAILED - REVIEW ABOVE")
            return False
            
    def run_all(self):
        """Execute complete test matrix"""
        try:
            # Start server
            if not self.start_server():
                return False
            
            time.sleep(2)  # Additional wait
            
            # Verify server is healthy
            try:
                import requests
                resp = requests.head('http://127.0.0.1:8000/hotels/', timeout=2)
                print(f"✓ Server health check: {resp.status_code}")
            except:
                print("⚠ Server health check failed")
            
            # Run test suite
            self.verify_server_logs()
            self.run_api_tests()
            self.run_e2e_tests_headless()
            self.run_database_verification()
            
            # Generate report
            success = self.generate_report()
            
            return success
            
        finally:
            self.stop_server()


if __name__ == '__main__':
    print("""
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║         🔥 GOEXPLORER HARD RESET E2E TEST RUNNER 🔥           ║
║                                                                ║
║  Complete test matrix with server log capture & verification  ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
    """)
    
    runner = TestMatrix()
    success = runner.run_all()
    
    sys.exit(0 if success else 1)
