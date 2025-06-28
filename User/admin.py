from django.contrib import admin
from .models import *
# Register your models here.
admin.site.register(User)
admin.site.register(UserArticle)
admin.site.register(Feedbacks)
admin.site.register(UserSession)
admin.site.register(Reminder)
admin.site.register(QuickNote)
admin.site.register(PasswordResetToken)
admin.site.register(LoginActivity)