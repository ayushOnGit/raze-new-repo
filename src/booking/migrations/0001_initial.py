# Generated by Django 5.1.5 on 2025-02-11 14:11

import booking.models.order
import django.db.models.deletion
import django.utils.timezone
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Event',
            fields=[
                ('event_id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('address', models.TextField()),
                ('description', models.TextField(blank=True, null=True)),
                ('start_date', models.DateTimeField(blank=True, null=True)),
                ('end_date', models.DateTimeField(blank=True, null=True)),
                ('sale_start', models.DateTimeField()),
                ('sale_end', models.DateTimeField()),
                ('is_active', models.BooleanField(default=True)),
                ('parent_event', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='booking.event')),
            ],
        ),
        migrations.CreateModel(
            name='EventSection',
            fields=[
                ('section_id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('sale_start', models.DateTimeField(null=True)),
                ('sale_end', models.DateTimeField(null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('event', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='booking.event')),
            ],
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('order_id', models.AutoField(primary_key=True, serialize=False)),
                ('timestamp', models.DateTimeField(default=django.utils.timezone.now)),
                ('expiry_on', models.DateTimeField(default=booking.models.order.get_default_expiry)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('discount_coupon', models.CharField(blank=True, max_length=50, null=True)),
                ('payment_id', models.CharField(blank=True, max_length=100, null=True)),
                ('status', models.CharField(choices=[('initial', 'Initial'), ('failed', 'Failed'), ('successful', 'Successful')], max_length=20)),
                ('failure_reason', models.TextField(blank=True, null=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Cart',
            fields=[
                ('cart_id', models.AutoField(primary_key=True, serialize=False)),
                ('discount_coupon', models.CharField(blank=True, max_length=50, null=True)),
                ('expires_on', models.DateTimeField(default=booking.models.order.get_default_expiry)),
                ('total_price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('status', models.CharField(choices=[('initial', 'Initial'), ('freed', 'Freed'), ('order_created', 'Order Created')], max_length=20)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('order', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='booking.order')),
            ],
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('product_id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('description', models.TextField(blank=True, null=True)),
                ('sale_start', models.DateTimeField(null=True)),
                ('sale_end', models.DateTimeField(null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('tickets_active_until', models.DateTimeField(blank=True, null=True)),
                ('event', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='booking.event')),
                ('section', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='booking.eventsection')),
            ],
        ),
        migrations.CreateModel(
            name='OrderLine',
            fields=[
                ('order_line_id', models.AutoField(primary_key=True, serialize=False)),
                ('quantity', models.IntegerField()),
                ('price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='booking.order')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='booking.product')),
            ],
        ),
        migrations.CreateModel(
            name='CartLine',
            fields=[
                ('cart_line_id', models.AutoField(primary_key=True, serialize=False)),
                ('quantity', models.IntegerField()),
                ('price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('cart', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='booking.cart')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='booking.product')),
            ],
        ),
        migrations.CreateModel(
            name='Quota',
            fields=[
                ('quota_id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('max_count', models.IntegerField()),
                ('slots_booked', models.IntegerField(default=0)),
                ('products', models.ManyToManyField(related_name='quotas', to='booking.product')),
            ],
        ),
        migrations.CreateModel(
            name='Ticket',
            fields=[
                ('ticket_id', models.AutoField(primary_key=True, serialize=False)),
                ('price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('is_cancelled', models.BooleanField(default=False)),
                ('order_line', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='booking.orderline')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='booking.product')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
