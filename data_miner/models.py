from django.db import models
from django.core.files.storage import default_storage
import os
from django.contrib.auth.models import User


class MiningHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mining_history')
    keyword = models.CharField(max_length=255)
    country = models.CharField(max_length=10)
    data_type = models.CharField(max_length=10)  # 'phone' or 'email'
    results_count = models.IntegerField(default=0)
    excel_file = models.FileField(upload_to='mining_results/')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Mining Histories'

    def __str__(self):
        return f"{self.keyword} - {self.data_type} ({self.results_count} results)"

    def delete(self, *args, **kwargs):
        # Delete the Excel file when the record is deleted
        if self.excel_file:
            if os.path.isfile(self.excel_file.path):
                default_storage.delete(self.excel_file.path)
        super().delete(*args, **kwargs)


class BackgroundTask(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='background_tasks')
    task_id = models.CharField(max_length=255, unique=True)
    task_name = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    parameters = models.JSONField(null=True, blank=True)
    progress = models.IntegerField(default=0)
    error_message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    mining_history = models.ForeignKey(MiningHistory, on_delete=models.SET_NULL, null=True, blank=True, related_name='task')
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.task_name} ({self.status}) - {self.task_id[:8]}"
