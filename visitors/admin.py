from django.contrib import admin
from .models import Resident, VisitRequest

@admin.register(Resident)
class ResidentAdmin(admin.ModelAdmin):
    list_display = ['flat_number', 'name', 'phone']
    search_fields = ['flat_number', 'name']
    list_filter = ['created_at']

@admin.register(VisitRequest)
class VisitRequestAdmin(admin.ModelAdmin):
    list_display = ['visitor_name', 'resident_flat', 'overall_confidence', 'status', 'created_at']
    list_filter = ['status', 'overall_confidence', 'created_at']
    search_fields = ['visitor_name', 'resident_flat', 'phone']
    readonly_fields = ['id', 'created_at']
    
    fieldsets = (
        ('Visitor Info', {
            'fields': ('visitor_name', 'visitor_phone', 'visitor_email', 'resident_flat', 'purpose')
        }),
        ('AI Scores', {
            'fields': ('face_match_score', 'id_ocr_confidence', 'tampering_score', 
                      'purpose_match_score', 'resident_validation', 'anomaly_score', 'overall_confidence'),
        }),
        ('Status & Technical', {
            'fields': ('status', 'qr_code_data', 'live_photo', 'id_photo', 'id', 'created_at'),
            'classes': ('collapse',)
        })
    )
