# Generated by Django 5.1.5 on 2025-02-12 17:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0005_event_is_featured'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='event',
            name='category',
        ),
        migrations.AddField(
            model_name='event',
            name='category',
            field=models.ManyToManyField(related_name='events', to='booking.eventcategory'),
        ),
    ]
