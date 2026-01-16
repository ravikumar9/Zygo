#!/usr/bin/env python
"""
Execute seed_data_clean.py script
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

# Now run the seed script
with open('seed_data_clean.py', 'r') as f:
    exec(f.read())
