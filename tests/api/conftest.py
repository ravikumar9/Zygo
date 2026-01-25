"""
pytest configuration for Phase-3 tests
"""
import pytest
from django.contrib.auth.models import Group
from django.core.management import call_command


@pytest.fixture(scope='session', autouse=True)
def django_db_setup(django_db_setup, django_db_blocker):
    """Setup Django Groups for tests"""
    with django_db_blocker.unblock():
        call_command('setup_admin_roles')


@pytest.fixture(autouse=True)
def enable_db_access(db):
    """Enable database access for all tests"""
    pass
