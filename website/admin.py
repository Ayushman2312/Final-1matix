from django.contrib import admin
from .models import *
# Register your models here.
admin.site.register(WebsiteTemplate)
admin.site.register(Website)
admin.site.register(CustomDomain)
admin.site.register(DomainLog)
admin.site.register(WebsitePage)

# Register newly added models
@admin.register(WebsiteDeployment)
class WebsiteDeploymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'website', 'status', 'version', 'environment', 'deployed_at', 'completed_at')
    list_filter = ('status', 'environment')
    search_fields = ('website__name',)
    readonly_fields = ('deployed_at', 'completed_at')

@admin.register(WebsiteBackup)
class WebsiteBackupAdmin(admin.ModelAdmin):
    list_display = ('id', 'website', 'name', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('website__name', 'name')
    readonly_fields = ('created_at',)
    
    def has_change_permission(self, request, obj=None):
        # Backups should not be modified
        return False

@admin.register(WebsiteTheme)
class WebsiteThemeAdmin(admin.ModelAdmin):
    list_display = ('name', 'template', 'is_premium', 'is_active')
    list_filter = ('is_premium', 'is_active', 'template')
    search_fields = ('name', 'description')

@admin.register(WebsiteFont)
class WebsiteFontAdmin(admin.ModelAdmin):
    list_display = ('name', 'font_family', 'font_type', 'is_active')
    list_filter = ('font_type', 'is_active')
    search_fields = ('name', 'font_family')

@admin.register(WebsiteColorScheme)
class WebsiteColorSchemeAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_dark', 'is_active')
    list_filter = ('is_dark', 'is_active')
    search_fields = ('name',)

@admin.register(WebsiteAsset)
class WebsiteAssetAdmin(admin.ModelAdmin):
    list_display = ('name', 'website', 'asset_type', 'created_at')
    list_filter = ('asset_type', 'created_at')
    search_fields = ('name', 'website__name')
    readonly_fields = ('created_at',)
