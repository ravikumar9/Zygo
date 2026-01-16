# Generated for wallet traceability
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='wallet_balance_before',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Wallet balance before payment', max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='booking',
            name='wallet_balance_after',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Wallet balance after payment', max_digits=10, null=True),
        ),
    ]
