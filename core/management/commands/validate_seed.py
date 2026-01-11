"""
Validate seed data consistency across environments
"""
from django.core.management.base import BaseCommand
from django.db.models import Count


class Command(BaseCommand):
    help = "Validate seed data parity - ensures seed_all produces consistent data"

    def handle(self, *args, **options):
        from hotels.models import Hotel
        from packages.models import Package
        from buses.models import Bus, BusOperator
        from payments.models import Wallet
        from users.models import User
        
        self.stdout.write(self.style.WARNING("\n" + "="*60))
        self.stdout.write(self.style.WARNING("SEED DATA PARITY VALIDATION"))
        self.stdout.write(self.style.WARNING("="*60 + "\n"))
        
        checks = {
            'Hotels': Hotel.objects.count(),
            'Packages': Package.objects.count(),
            'Buses': Bus.objects.count(),
            'Bus Operators': BusOperator.objects.count(),
            'Wallets': Wallet.objects.count(),
        }
        
        # Expected counts from seed_all
        expected = {
            'Hotels': 16,
            'Packages': 5,
            'Buses': 3,
            'Bus Operators': 2,
            'Wallets': 1,  # testuser
        }
        
        all_pass = True
        for key, expected_count in expected.items():
            actual = checks[key]
            if actual == expected_count:
                status = self.style.SUCCESS("[OK]")
            else:
                status = self.style.ERROR("[FAIL]")
                all_pass = False
            
            self.stdout.write(f"{status} {key}: {actual}/{expected_count}")
        
        # Additional validation: testuser wallet
        self.stdout.write("\n" + "-"*60)
        self.stdout.write(self.style.NOTICE("Wallet Details:"))
        self.stdout.write("-"*60 + "\n")
        
        try:
            testuser = User.objects.get(username='testuser')
            wallet = testuser.wallet
            
            balance_check = "OK" if wallet.balance == 5000 else "FAIL"
            self.stdout.write(f"  Testuser exists: {self.style.SUCCESS('[OK]')}")
            self.stdout.write(f"  Wallet balance: {wallet.balance} [Expected: 5000]")
            if wallet.balance == 5000:
                self.stdout.write(self.style.SUCCESS("    [OK] Balance matches"))
            else:
                self.stdout.write(self.style.ERROR("    [FAIL] Balance mismatch"))
                all_pass = False
            
            from payments.models import CashbackLedger
            from django.utils import timezone
            
            active_cashback = CashbackLedger.objects.filter(
                wallet=wallet,
                is_used=False,
                is_expired=False,
                expires_at__gt=timezone.now()
            ).aggregate(total=Count('id'))['total']
            
            self.stdout.write(f"  Active cashback entries: {active_cashback} [Expected: 1]")
            if active_cashback == 1:
                self.stdout.write(self.style.SUCCESS("    [OK] Cashback entry exists"))
            else:
                self.stdout.write(self.style.ERROR("    [FAIL] Cashback entry mismatch"))
                all_pass = False
                
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR("  [FAIL] testuser does not exist"))
            all_pass = False
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  [FAIL] Error checking wallet: {str(e)}"))
            all_pass = False
        
        # Final result
        self.stdout.write("\n" + "="*60)
        if all_pass:
            self.stdout.write(self.style.SUCCESS("[OK] SEED PARITY VERIFIED!"))
            self.stdout.write(self.style.SUCCESS("All data matches expected counts."))
            exit_code = 0
        else:
            self.stdout.write(self.style.ERROR("[FAIL] SEED PARITY MISMATCH!"))
            self.stdout.write(self.style.ERROR("Check seed_all output and re-run if needed."))
            exit_code = 1
        self.stdout.write("="*60 + "\n")
        
        return exit_code
