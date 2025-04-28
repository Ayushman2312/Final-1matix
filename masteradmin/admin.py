from django.contrib import admin
from .models import *
# Register your models here.

admin.site.register(MasterAdmin)
@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('name', 'plan_type', 'price_monthly', 'is_active')
    list_filter = ('plan_type', 'is_active')
    search_fields = ('name',)
admin.site.register(QuickNotes)
# @admin.register(Coupon)
# class CouponAdmin(admin.ModelAdmin):
#     list_display = ('code', 'discount_type', 'rate', 'expiry_date')
#     search_fields = ('code',)

@admin.register(Coupons)
class CouponsAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'discount_type', 'rate', 'expiry_date')
    search_fields = ('name', 'code')
admin.site.register(Tickets)
# @admin.register(Tickets)
# class TicketsAdmin(admin.ModelAdmin):
#     list_display = ('name', 'email', 'department', 'problem', 'status')
#     search_fields = ('name', 'email', 'department')

admin.site.register(WhatsOnMind)
admin.site.register(AgentNotification)
admin.site.register(EmployeeNotification)
admin.site.register(SupportNotification)
admin.site.register(WhatsOnMindReadStatus)
admin.site.register(AI_Prompt)
