# Generated for bonus transaction type
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='wallettransaction',
            name='transaction_type',
            field=models.CharField(
                choices=[
                    ('credit', 'Credit'),
                    ('debit', 'Debit'),
                    ('cashback', 'Cashback'),
                    ('refund', 'Refund'),
                    ('bonus', 'Bonus'),
                ],
                max_length=20
            ),
        ),
    ]
