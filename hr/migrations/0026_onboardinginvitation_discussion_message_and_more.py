# Generated by Django 4.2.20 on 2025-05-28 11:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hr', '0025_employee_is_active_employee_is_approved_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='onboardinginvitation',
            name='discussion_message',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='onboardinginvitation',
            name='has_viewed_offer',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='onboardinginvitation',
            name='rejection_reason',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='onboardinginvitation',
            name='status',
            field=models.CharField(choices=[('pending', 'Pending'), ('sent', 'Sent'), ('completed', 'Completed'), ('expired', 'Expired'), ('rejected', 'Rejected'), ('accepted', 'Accepted'), ('need_discussion', 'Need Discussion')], default='pending', max_length=20),
        ),
    ]
