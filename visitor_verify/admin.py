# myapp/admin.py
from django.contrib import admin
from .models import Resident, ParkingSlot, Visitor

@admin.register(Resident)
class ResidentAdmin(admin.ModelAdmin):
    # What columns to show in the list view
    list_display = ('flat_number', 'owner_name', 'email')
    # Add a search bar to easily find residents by flat or name
    search_fields = ('flat_number', 'owner_name')
    # Default sorting by flat number
    ordering = ('flat_number',)

@admin.register(ParkingSlot)
class ParkingSlotAdmin(admin.ModelAdmin):
    list_display = ('slot_number', 'is_occupied')
    # Allow admins to filter by available vs occupied slots
    list_filter = ('is_occupied',)
    search_fields = ('slot_number',)
    # Make the is_occupied toggle clickable directly from the list view
    list_editable = ('is_occupied',) 

@admin.register(Visitor)
class VisitorAdmin(admin.ModelAdmin):
    list_display = ('name', 'resident_visited', 'visit_time', 'is_verified', 'allocated_parking', 'token_id')
    # Powerful filters for security to check logs by date or verification status
    list_filter = ('is_verified', 'visit_time')
    search_fields = ('name', 'aadhaar_number', 'token_id')
    # Make these fields read-only so security guards can't accidentally alter historical logs
    readonly_fields = ('token_id', 'visit_time', 'is_verified')
    
    # Organize the detail view into sections
    fieldsets = (
        ('Visitor Details', {
            'fields': ('name', 'aadhaar_number', 'purpose')
        }),
        ('Visit Information', {
            'fields': ('resident_visited', 'allocated_parking', 'token_id', 'visit_time', 'is_verified')
        }),
    )