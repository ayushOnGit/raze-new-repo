# Generated by Django 5.1.5 on 2025-03-20 14:08

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0019_artist_facebook_link_artist_instagram_link_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='subevent',
            name='event',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='subevents', to='booking.event'),
        ),
    ]
