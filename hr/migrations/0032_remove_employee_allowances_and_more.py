# Generated by Django 4.2.20 on 2025-05-31 10:47

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('hr', '0031_employee_allowances_employee_salary_ctc'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='employee',
            name='allowances',
        ),
        migrations.RemoveField(
            model_name='employee',
            name='salary_ctc',
        ),
        migrations.CreateModel(
            name='TrustedDevice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('device_id', models.UUIDField(default=uuid.uuid4, editable=False)),
                ('device_name', models.CharField(blank=True, max_length=255, null=True)),
                ('browser_info', models.CharField(blank=True, max_length=255, null=True)),
                ('platform', models.CharField(blank=True, max_length=100, null=True)),
                ('last_used', models.DateTimeField(auto_now=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('is_active', models.BooleanField(default=True)),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='trusted_devices', to='hr.employee')),
            ],
            options={
                'ordering': ['-last_used'],
                'unique_together': {('device_id', 'employee')},
            },
        ),
    ]
