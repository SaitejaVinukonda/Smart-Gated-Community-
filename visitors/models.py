from django.db import models
from django.utils import timezone
import uuid
from django.conf import settings

class Resident(models.Model):
    flat_number = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=15, blank=True)
    approved_purposes = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['flat_number']
    
    def __str__(self):
        return f"🏠 {self.flat_number} - {self.name}"

class VisitRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('denied', 'Denied'),
        ('expired', 'Expired'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    visitor_name = models.CharField(max_length=200)
    visitor_phone = models.CharField(max_length=15)
    visitor_email = models.EmailField(blank=True)
    
    resident_flat = models.CharField(max_length=20)
    purpose = models.CharField(max_length=200)
    
    # ML Scores (0.0-1.0)
    face_match_score = models.FloatField(default=0.0)
    id_ocr_confidence = models.FloatField(default=0.0)
    tampering_score = models.FloatField(default=0.0)
    purpose_match_score = models.FloatField(default=0.0)
    resident_validation = models.FloatField(default=0.0)
    anomaly_score = models.FloatField(default=0.0)
    
    overall_confidence = models.FloatField(default=0.0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Technical
    live_photo = models.TextField(blank=True)  # base64
    id_photo = models.TextField(blank=True)    # base64
    qr_code_data = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"👤 {self.visitor_name} → {self.resident_flat} ({self.status})"
    
    @property
    def is_approved(self):
        return self.status == 'approved'
