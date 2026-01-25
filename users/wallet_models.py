"""User wallet models for payment handling"""
from django.db import models
from django.conf import settings
from decimal import Decimal


class UserWallet(models.Model):
    """User wallet for payments"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_wallets'
        verbose_name = 'User Wallet'
        verbose_name_plural = 'User Wallets'
    
    def __str__(self):
        return f"{self.user.email} - ₹{self.balance}"
    
    def has_sufficient_balance(self, amount):
        """Check if wallet has sufficient balance"""
        return self.balance >= Decimal(str(amount))
    
    def deduct(self, amount, description=''):
        """Deduct amount from wallet"""
        amount = Decimal(str(amount))
        if not self.has_sufficient_balance(amount):
            raise ValueError('Insufficient wallet balance')
        
        self.balance -= amount
        self.save(update_fields=['balance'])
        
        # Create transaction record
        WalletTransaction.objects.create(
            wallet=self,
            transaction_type='DEBIT',
            amount=amount,
            description=description,
            balance_after=self.balance
        )
        
        return self.balance
    
    def add(self, amount, description=''):
        """Add amount to wallet"""
        amount = Decimal(str(amount))
        self.balance += amount
        self.save(update_fields=['balance'])
        
        # Create transaction record
        WalletTransaction.objects.create(
            wallet=self,
            transaction_type='CREDIT',
            amount=amount,
            description=description,
            balance_after=self.balance
        )
        
        return self.balance


class WalletTransaction(models.Model):
    """Wallet transaction history"""
    TRANSACTION_TYPE_CHOICES = [
        ('CREDIT', 'Credit'),
        ('DEBIT', 'Debit'),
    ]
    
    wallet = models.ForeignKey(UserWallet, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    balance_after = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'wallet_transactions'
        verbose_name = 'Wallet Transaction'
        verbose_name_plural = 'Wallet Transactions'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.wallet.user.email} - {self.transaction_type} ₹{self.amount}"
