from django.contrib import admin
from .models import *

class AppAdmin(admin.ModelAdmin):
    list_display = ('name', 'url_keyword', 'is_active', 'is_temporarily_disabled', 'created_at')
    list_editable = ('url_keyword', 'is_active', 'is_temporarily_disabled',)
    list_filter = ('is_active', 'is_temporarily_disabled', 'created_at')
    search_fields = ('name', 'description', 'url_keyword')

# Register your models here.

admin.site.register(Apps, AppAdmin)
