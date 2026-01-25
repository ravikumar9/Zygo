from django.db import migrations, models
import django.db.models.deletion
from django.core.validators import MaxValueValidator, MinValueValidator


class Migration(migrations.Migration):

    dependencies = [
        ('hotels', '0016_roomcancellationpolicy'),
        ('bookings', '0013_add_promo_code_to_booking'),
    ]

    operations = [
        migrations.AddField(
            model_name='hotelbooking',
            name='cancellation_policy',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='bookings', to='hotels.roomcancellationpolicy'),
        ),
        migrations.AddField(
            model_name='hotelbooking',
            name='policy_free_cancel_until',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='hotelbooking',
            name='policy_locked_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='hotelbooking',
            name='policy_refund_percentage',
            field=models.PositiveIntegerField(blank=True, null=True, validators=[MinValueValidator(0), MaxValueValidator(100)]),
        ),
        migrations.AddField(
            model_name='hotelbooking',
            name='policy_text',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='hotelbooking',
            name='policy_type',
            field=models.CharField(choices=[('FREE', 'Free Cancellation'), ('PARTIAL', 'Partial Refund'), ('NON_REFUNDABLE', 'Non-Refundable')], default='NON_REFUNDABLE', max_length=20),
        ),
    ]
