from django.contrib import admin

from maintainance.models import Assignment

# Register your models here.
@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ['request', 'staff', 'score', 'accepted', 'rejected', 'rejection_reason']
    list_filter = ['accepted', 'rejected', 'assigned_at']
