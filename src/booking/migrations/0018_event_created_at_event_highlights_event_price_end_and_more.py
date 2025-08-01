# Generated by Django 5.1.5 on 2025-03-20 12:37

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0017_alter_event_artists_alter_event_categories_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name='event',
            name='highlights',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='event',
            name='price_end',
            field=models.DecimalField(decimal_places=2, default=None, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='event',
            name='price_start',
            field=models.DecimalField(decimal_places=2, default=None, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='event',
            name='subtitle',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='event',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, null=True),
        ),
        migrations.CreateModel(
            name='IteneraryItem',
            fields=[
                ('item_id', models.AutoField(primary_key=True, serialize=False)),
                ('title', models.TextField(blank=True, null=True)),
                ('details', models.TextField(blank=True, null=True)),
                ('date', models.DateTimeField()),
                ('event', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='itenerary', to='booking.event')),
                ('subevent', models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='itenerary', to='booking.subevent')),
            ],
            options={
                'ordering': ['date'],
            },
        ),
    ]
