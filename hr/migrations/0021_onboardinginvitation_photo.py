# Generated by Django 4.2.20 on 2025-05-27 11:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hr', '0020_onboardinginvitation_rejected_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='onboardinginvitation',
            name='photo',
            field=models.ImageField(blank=True, null=True, upload_to='employee_photos/'),
        ),
    ]
