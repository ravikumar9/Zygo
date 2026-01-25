from django.db import migrations, models
import django.db.models.deletion
from django.core.validators import MaxValueValidator, MinValueValidator


class Migration(migrations.Migration):

    dependencies = [
        ('hotels', '0015_roomtype_discount_is_active_roomtype_discount_type_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='RoomCancellationPolicy',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('policy_type', models.CharField(choices=[('FREE', 'Free Cancellation'), ('PARTIAL', 'Partial Refund'), ('NON_REFUNDABLE', 'Non-Refundable')], default='NON_REFUNDABLE', max_length=20)),
                ('free_cancel_until', models.DateTimeField(blank=True, null=True)),
                ('refund_percentage', models.PositiveIntegerField(blank=True, help_text='Percentage of paid amount to refund (0-100)', null=True, validators=[MinValueValidator(0), MaxValueValidator(100)])),
                ('policy_text', models.TextField(help_text='Human-readable policy snapshot')),
                ('is_active', models.BooleanField(default=True)),
                ('room_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cancellation_policies', to='hotels.roomtype')),
            ],
            options={
                'ordering': ['-is_active', '-created_at'],
            },
        ),
    ]
