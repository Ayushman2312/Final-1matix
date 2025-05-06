from django.db import models

# Create your models here.

class TrendSearch(models.Model):
    keyword = models.CharField(max_length=100)
    timestamp = models.DateTimeField(auto_now_add=True)
    country = models.CharField(max_length=5, default='IN')
    
    def __str__(self):
        return f"{self.keyword} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
    
    class Meta:
        ordering = ['-timestamp']
