from django.contrib import admin
from .models import *
# Register your models here.
admin.site.register(WebsiteTemplate)
admin.site.register(Website)
admin.site.register(CustomDomain)
admin.site.register(DomainLog)
admin.site.register(WebsitePage)
