from django.contrib import admin
from django.utils.html import format_html
from .models import Visitor, Resident, VisitLog, BlockedVisitor, ResidentNotification, ParkingSlot


@admin.register(Resident)
class ResidentAdmin(admin.ModelAdmin):
    list_display = ['user', 'flat_number', 'block', 'status', 'is_verified', 'phone']
    list_filter = ['status', 'block', 'is_verified']
    search_fields = ['user__first_name', 'user__last_name', 'flat_number', 'aadhaar_number']
    list_editable = ['status', 'is_verified']


@admin.register(Visitor)
class VisitorAdmin(admin.ModelAdmin):
    list_display = ['name', 'aadhaar_number', 'phone', 'created_at', 'photo_preview']
    search_fields = ['name', 'aadhaar_number', 'phone']
    readonly_fields = ['aadhaar_face_encoding', 'photo_preview']

    def photo_preview(self, obj):
        if obj.live_photo:
            return format_html(
                '<img src="/media/{}" width="60" height="60" style="border-radius:50%"/>',
                obj.live_photo
            )
        return '—'
    photo_preview.short_description = 'Photo'


@admin.register(VisitLog)
class VisitLogAdmin(admin.ModelAdmin):
    list_display = [
        'visitor', 'resident', 'status', 'face_match_score',
        'purpose_category', 'created_at', 'qr_status'
    ]
    list_filter = ['status', 'face_verified', 'purpose_approved', 'created_at']
    search_fields = ['visitor__name', 'resident__flat_number', 'purpose']
    readonly_fields = ['qr_code', 'qr_token', 'face_match_score']

    def qr_status(self, obj):
        if obj.qr_code:
            color = '#22c55e' if not obj.qr_used else '#94a3b8'
            return format_html('<span style="color:{}">●</span> {}', color, 'Active' if not obj.qr_used else 'Used')
        return '—'
    qr_status.short_description = 'QR'


@admin.register(BlockedVisitor)
class BlockedVisitorAdmin(admin.ModelAdmin):
    list_display = ['name', 'aadhaar_number', 'reason', 'blocked_by', 'created_at']
    search_fields = ['name', 'aadhaar_number']


@admin.register(ParkingSlot)
class ParkingSlotAdmin(admin.ModelAdmin):
    list_display = ['slot_number', 'location', 'is_available', 'created_at', 'availability_status']
    list_filter = ['is_available', 'created_at']
    search_fields = ['slot_number', 'location']
    list_editable = ['is_available']
    readonly_fields = ['created_at']

    def availability_status(self, obj):
        color = '#22c55e' if obj.is_available else '#ef4444'
        status_text = 'Available' if obj.is_available else 'Occupied'
        return format_html('<span style="color:{}">●</span> {}', color, status_text)
    availability_status.short_description = 'Status'
