# Generated migration: Make meal_plan optional

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0012_add_completed_at_timestamp'),
        ('hotels', '0011_roommealplan'),
    ]

    operations = [
        migrations.AlterField(
            model_name='hotelbooking',
            name='meal_plan',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='bookings', to='hotels.roommealplan'),
        ),
    ]
