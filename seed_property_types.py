#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'goexplorer.settings')
django.setup()

from property_owners.models import PropertyType

PropertyType.objects.all().delete()

types = [
    ('homestay', 'Homestay'),
    ('resort', 'Resort'),
    ('villa', 'Villa'),
    ('guesthouse', 'Guest House'),
    ('farmstay', 'Farm Stay'),
    ('houseboat', 'Houseboat'),
]

for name, display_name in types:
    pt, created = PropertyType.objects.get_or_create(name=name, defaults={'description': f'{display_name} property'})
    print(f'{"Created" if created else "Exists"}: {display_name}')

print(f'\nTotal PropertyTypes: {PropertyType.objects.count()}')
