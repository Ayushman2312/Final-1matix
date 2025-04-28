from django.contrib import admin
from .models import *
# Register your models here.
admin.site.register(Company)
admin.site.register(Billing)
admin.site.register(Invoice)
admin.site.register(Recipent)

