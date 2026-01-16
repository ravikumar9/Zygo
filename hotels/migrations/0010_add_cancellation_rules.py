# Generated for cancellation rules
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hotels', '0009_hotel_amenities_rules'),
    ]

    operations = [
        migrations.AddField(
            model_name='hotel',
            name='cancellation_type',
            field=models.CharField(
                choices=[('NO_CANCELLATION', 'No Cancellation'), ('UNTIL_CHECKIN', 'Allowed Until Check-in'), ('X_DAYS_BEFORE', 'Allowed X Days Before Check-in')],
                default='UNTIL_CHECKIN',
                max_length=20
            ),
        ),
        migrations.AddField(
            model_name='hotel',
            name='cancellation_days',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='hotel',
            name='refund_percentage',
            field=models.PositiveIntegerField(default=100),
        ),
        migrations.AddField(
            model_name='hotel',
            name='refund_mode',
            field=models.CharField(
                choices=[('WALLET', 'Wallet'), ('ORIGINAL', 'Original Payment')],
                default='WALLET',
                max_length=20
            ),
        ),
    ]
