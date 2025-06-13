from django.contrib import admin
from .models import TrendSearch

@admin.register(TrendSearch)
class TrendSearchAdmin(admin.ModelAdmin):
    list_display = ['keyword', 'timestamp', 'country', 'user']
    list_filter = ['country', 'timestamp', 'user']
    search_fields = ['keyword']
    date_hierarchy = 'timestamp'
