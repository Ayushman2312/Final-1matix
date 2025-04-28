from django.contrib import admin
from .models import *
# Register your models here
admin.site.register(AgentFamily)
admin.site.register(AgentCoorporate)

@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    list_display = ('agent_user', 'start_time', 'end_time')
    list_filter = ('agent_user', 'start_time', 'end_time')

admin.site.register(DemoSession)
admin.site.register(Policy)


# yourapp/admin.py
import csv
from django.http import HttpResponse
from django.contrib import admin

# Define the export function
def export_to_csv(modeladmin, request, queryset):
    # Create the HttpResponse object with CSV header
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="agentuser_data.csv"'

    # Create a CSV writer
    writer = csv.writer(response)
    
    # Write the header row (field names)
    fields = [field.name for field in AgentUser._meta.fields]  # Get all field names
    writer.writerow(fields)

    # Write data rows (all objects, not just selected queryset)
    all_objects = AgentUser.objects.all()  # Fetch all data
    for obj in all_objects:
        writer.writerow([getattr(obj, field) for field in fields])

    return response

# Give the action a user-friendly name
export_to_csv.short_description = "Download all data as CSV"

# Register the model with the admin
@admin.register(AgentUser)
class AgentUserAdmin(admin.ModelAdmin):
    search_fields = ('name', 'email')
    actions = [export_to_csv]  # Add the custom action