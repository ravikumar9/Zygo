#!/usr/bin/env python
"""Minimal Playwright setup - just run tests"""
import os
import sys
import django
import subprocess
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

def run_playwright_tests():
    """Run Playwright UI E2E tests"""
    print("\n[*] Running Playwright UI E2E tests...")
    print("=" * 60)
    
    # Ensure test-results directory exists
    Path('test-results/videos').mkdir(parents=True, exist_ok=True)
    Path('test-results/html-report').mkdir(parents=True, exist_ok=True)
    
    # Run Playwright tests with headed mode and full reporting
    result = subprocess.run(
        ['npx', 'playwright', 'test', '--headed', '--reporter=list,html'],
        cwd=os.getcwd()
    )
    
    return result.returncode == 0

def main():
    """Main execution flow"""
    print(">>> Goibibo Booking Platform - Playwright UI E2E Test Suite")
    print("=" * 60)
    print("[*] Django server should be running on http://localhost:8000")
    print("[*] Test data should already be seeded")
    print()
    
    try:
        # Run tests
        success = run_playwright_tests()
        
        if success:
            print("\n[+] ALL PLAYWRIGHT UI E2E TESTS PASSED")
            print("\n[*] Artifacts generated:")
            print("   >> Videos: test-results/videos/")
            print("   >> Screenshots: test-results/*.png")
            print("   >> Traces: test-results/trace.zip")
            print("   >> Report: test-results/html-report/index.html")
            print("\nTo view results:")
            print("   npx playwright show-report test-results/html-report")
            sys.exit(0)
        else:
            print("\n[-] SOME TESTS FAILED")
            print("Check test-results/html-report/index.html for details")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n[-] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
