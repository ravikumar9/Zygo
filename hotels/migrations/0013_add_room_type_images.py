# Generated migration to add RoomImage model for multiple room type images

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('hotels', '0012_add_timestamps_to_hotel_image'),
    ]

    operations = [
        migrations.CreateModel(
            name='RoomImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('image', models.ImageField(upload_to='hotels/rooms/')),
                ('is_primary', models.BooleanField(default=False)),
                ('display_order', models.IntegerField(default=0)),
                ('room_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='hotels.roomtype')),
            ],
            options={
                'ordering': ['-is_primary', 'display_order', 'id'],
            },
        ),
    ]
