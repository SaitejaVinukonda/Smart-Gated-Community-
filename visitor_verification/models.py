from django.db import models
from django.contrib.auth.models import User
import uuid

from community import settings


class Resident(models.Model):
    """Represents a resident of the gated community"""
    STATUS_CHOICES = [
        ('home', 'At Home'),
        ('away', 'Away'),
        ('dnd', 'Do Not Disturb'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True
    )
    flat_number = models.CharField(max_length=20, unique=True)
    block = models.CharField(max_length=10)
    phone = models.CharField(max_length=15)
    profile_photo = models.ImageField(upload_to='resident_photos/', null=True, blank=True)
    aadhaar_number = models.CharField(max_length=12, unique=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='home')
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name()} - Flat {self.flat_number}, Block {self.block}"

    @property
    def full_address(self):
        return f"Block {self.block}, Flat {self.flat_number}"


class Visitor(models.Model):
    """Stores visitor information including Aadhaar and live photo"""
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    aadhaar_number = models.CharField(max_length=12)
    phone = models.CharField(max_length=15)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    aadhaar_image = models.ImageField(upload_to='aadhaar_images/')
    live_photo = models.ImageField(upload_to='visitor_photos/')
    aadhaar_face_encoding = models.JSONField(null=True, blank=True)  # Stored face encoding
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.aadhaar_number})"


class ParkingSlot(models.Model):
    """Parking slots for visitor allocation"""
    slot_number = models.CharField(max_length=20, unique=True)  # e.g., "A-001", "B-002"
    is_available = models.BooleanField(default=True)
    location = models.CharField(max_length=100, blank=True)  # e.g., "Ground Floor Near Gate"
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Slot {self.slot_number} - {'Available' if self.is_available else 'Occupied'}"

    class Meta:
        ordering = ['slot_number']


class VisitLog(models.Model):
    """Records each visit attempt and its outcome"""
    VISIT_STATUS = [
        ('pending', 'Pending Verification'),
        ('face_failed', 'Face Verification Failed'),
        ('resident_unavailable', 'Resident Unavailable'),
        ('purpose_rejected', 'Purpose Rejected'),
        ('approved', 'Approved'),
        ('denied', 'Denied'),
        ('completed', 'Visit Completed'),
        ('expired', 'QR Expired'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    visitor = models.ForeignKey(Visitor, on_delete=models.CASCADE, related_name='visits')
    resident = models.ForeignKey(Resident, on_delete=models.CASCADE, related_name='visitors')
    purpose = models.TextField()
    purpose_category = models.CharField(max_length=100, null=True, blank=True)  # NLP classified
    purpose_risk_score = models.FloatField(default=0.0)  # 0.0 = safe, 1.0 = risky

    # Verification results
    face_match_score = models.FloatField(default=0.0)
    face_verified = models.BooleanField(default=False)
    aadhaar_verified = models.BooleanField(default=False)
    resident_available = models.BooleanField(default=False)
    resident_approved = models.BooleanField(null=True, blank=True)  # null = pending approval
    purpose_approved = models.BooleanField(default=False)

    # Overall status
    status = models.CharField(max_length=25, choices=VISIT_STATUS, default='pending')

    # QR Code
    qr_code = models.ImageField(upload_to='qr_codes/', null=True, blank=True)
    qr_token = models.UUIDField(default=uuid.uuid4, unique=True)
    qr_valid_until = models.DateTimeField(null=True, blank=True)
    qr_used = models.BooleanField(default=False)

    # Timing
    scheduled_time = models.DateTimeField(null=True, blank=True)
    check_in_time = models.DateTimeField(null=True, blank=True)
    check_out_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Guard info
    gate_number = models.CharField(max_length=20, null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    
    # Parking allocation
    parking_slot = models.ForeignKey(ParkingSlot, on_delete=models.SET_NULL, null=True, blank=True, related_name='visits')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Visit by {self.visitor.name} to {self.resident} - {self.status}"


class ResidentNotification(models.Model):
    """Notification sent to resident for approval"""
    visit_log = models.OneToOneField(VisitLog, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    approved = models.BooleanField(null=True, blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def __str__(self):
        return f"Notification for {self.visit_log}"


class BlockedVisitor(models.Model):
    """Blacklist for blocked visitors"""
    aadhaar_number = models.CharField(max_length=12, unique=True)
    name = models.CharField(max_length=200)
    reason = models.TextField()
    blocked_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Blocked: {self.name} ({self.aadhaar_number})"
