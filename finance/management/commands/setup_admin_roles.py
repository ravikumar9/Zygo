"""
Management command to setup Django Groups for role-based admin access
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType


class Command(BaseCommand):
    help = 'Setup Django Groups for role-based admin access'

    def handle(self, *args, **options):
        """Create 4 admin role groups with appropriate permissions"""
        
        # Define roles and their permissions
        roles = {
            'SUPER_ADMIN': {
                'description': 'Full system access - all dashboards, all operations',
                'permissions': []  # Will get all permissions
            },
            'FINANCE_ADMIN': {
                'description': 'Financial data access - invoices, payouts, ledger',
                'permissions': [
                    'view_invoice',
                    'view_ownerpayout',
                    'view_platformledger',
                    'view_booking',
                    'view_payment',
                ]
            },
            'PROPERTY_ADMIN': {
                'description': 'Property management - hotel approvals, room inventory',
                'permissions': [
                    'view_hotel',
                    'change_hotel',
                    'view_roomtype',
                    'view_booking',
                ]
            },
            'SUPPORT_ADMIN': {
                'description': 'Customer support - view bookings, limited operations',
                'permissions': [
                    'view_booking',
                    'view_user',
                    'view_review',
                ]
            },
        }
        
        created_count = 0
        updated_count = 0
        
        for role_name, role_data in roles.items():
            group, created = Group.objects.get_or_create(name=role_name)
            
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'Created group: {role_name}'))
            else:
                updated_count += 1
                self.stdout.write(self.style.WARNING(f'Updated group: {role_name}'))
            
            # Clear existing permissions
            group.permissions.clear()
            
            if role_name == 'SUPER_ADMIN':
                # Give all permissions
                all_perms = Permission.objects.all()
                group.permissions.set(all_perms)
                self.stdout.write(f'  -> Assigned ALL permissions ({all_perms.count()} total)')
            else:
                # Assign specific permissions
                perm_count = 0
                for perm_codename in role_data['permissions']:
                    try:
                        perm = Permission.objects.get(codename=perm_codename)
                        group.permissions.add(perm)
                        perm_count += 1
                    except Permission.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(f'  -> Permission not found: {perm_codename}')
                        )
                
                self.stdout.write(f'  -> Assigned {perm_count} permissions')
            
            self.stdout.write(f'  -> Description: {role_data["description"]}')
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Role setup complete: {created_count} created, {updated_count} updated'
        ))
        self.stdout.write('')
        self.stdout.write('To assign a role to a user: user.groups.add(Group.objects.get(name="SUPER_ADMIN"))')
