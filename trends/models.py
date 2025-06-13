from django.db import models
from django.conf import settings

# Create your models here.

class TrendSearch(models.Model):
    keyword = models.CharField(max_length=100)
    timestamp = models.DateTimeField(auto_now_add=True)
    country = models.CharField(max_length=5, default='IN')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='trend_searches')
    
    def __str__(self):
        return f"{self.keyword} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
    
    class Meta:
        ordering = ['-timestamp']
