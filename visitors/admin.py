from django.contrib import admin
from .models import Visitor, VisitRequest, AccessCode, GateEvent

@admin.register(Visitor)
class VisitorAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'phone', 'email', 'frequent_visitor']
    list_filter = ['frequent_visitor']
    search_fields = ['full_name', 'phone', 'email']
    readonly_fields = []

@admin.register(VisitRequest)
class VisitRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'get_visitor_name', 'get_resident_name', 'get_status', 'risk_score', 'get_request_time']
    list_filter = ['auto_decision']
    search_fields = ['visitor__full_name', 'purpose', 'target_flat']
    readonly_fields = ['get_request_time']
    
    # Custom methods for foreign key
    def get_visitor_name(self, obj):
        v = getattr(obj, 'visitor', None)
        if v:
            return getattr(v, 'full_name', str(v))
        # fallback to fields on VisitRequest if present, or show placeholder
        return getattr(obj, 'visitor_name', getattr(obj, 'visitor_full_name', 'N/A'))
    get_visitor_name.short_description = 'Visitor'
    
    def get_resident_name(self, obj):
        r = getattr(obj, 'resident', None)
        if r:
            return getattr(r, 'username', str(r))
        return getattr(obj, 'resident_name', 'N/A')
    get_resident_name.short_description = 'Resident'
    
    def get_status(self, obj):
        if hasattr(obj, 'status'):
            return getattr(obj, 'status')
        if hasattr(obj, 'get_status_display'):
            try:
                return obj.get_status_display()
            except Exception:
                pass
        if hasattr(obj, 'auto_decision'):
            return 'Auto-approved' if obj.auto_decision else 'Auto-rejected'
        return 'N/A'
    get_status.short_description = 'Status'
    
    def get_request_time(self, obj):
        rt = getattr(obj, 'request_time', None)
        if not rt:
            return 'N/A'
        return rt.strftime('%Y-%m-%d %H:%M')
    get_request_time.short_description = 'Created'

@admin.register(AccessCode)
class AccessCodeAdmin(admin.ModelAdmin):
    list_display = ['code', 'get_request_id', 'code_type', 'valid_from', 'valid_to', 'used']
    list_filter = ['code_type', 'used']
    
    def get_request_id(self, obj):
        return obj.request.id
    get_request_id.short_description = 'Request'

@admin.register(GateEvent)
class GateEventAdmin(admin.ModelAdmin):
    list_display = ['get_code', 'direction', 'timestamp', 'verified_by_ml']
    list_filter = ['direction', 'verified_by_ml']
    date_hierarchy = 'timestamp'
    
    def get_code(self, obj):
        return obj.access_code.code
    get_code.short_description = 'Access Code'