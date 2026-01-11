#!/usr/bin/env python
"""
Cross-platform seed runner with Windows UTF-8 support
"""
import os
import sys
import subprocess

# Set UTF-8 mode for Windows
os.environ['PYTHONIOENCODING'] = 'utf-8'

def run_seed(command):
    """Run a seed management command"""
    cmd = [sys.executable, 'manage.py'] + command
    print(f"\n{'='*60}")
    print(f"Running: {' '.join(command)}")
    print(f"{'='*60}\n")
    
    result = subprocess.run(cmd, cwd=os.path.dirname(__file__))
    return result.returncode == 0

if __name__ == '__main__':
    os.chdir(os.path.dirname(__file__))
    
    seeds = [
        ['seed_hotels'],
        ['seed_packages'],
        ['seed_buses'],
        ['seed_wallet_data'],
    ]
    
    failed = []
    for seed in seeds:
        if not run_seed(seed):
            failed.append(' '.join(seed))
    
    print(f"\n{'='*60}")
    if failed:
        print(f"[FAILED] Some seeds failed to run:")
        for f in failed:
            print(f"  - {f}")
        sys.exit(1)
    else:
        print(f"[OK] All seeds completed successfully!")
        print(f"{'='*60}\n")
        sys.exit(0)
