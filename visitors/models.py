from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid

User = get_user_model()


class Visitor(models.Model):
    full_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=32, db_index=True)
    email = models.EmailField(blank=True, null=True)
    frequent_visitor = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        name = getattr(self, "full_name", None) or getattr(self, "name", None) or f"Visitor ({getattr(self, 'pk', 'n/a')})"
        phone = getattr(self, "phone", None)
        return f"{name} [{phone}]" if phone else name


class VisitRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    visitor = models.ForeignKey(Visitor, on_delete=models.SET_NULL, null=True, blank=True, related_name="requests")
    resident = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="visit_requests")
    purpose = models.TextField(blank=True)
    target_flat = models.CharField(max_length=32, blank=True)
    target_resident_name = models.CharField(max_length=200, blank=True)
    vehicle_number = models.CharField(max_length=64, blank=True)
    relation_to_resident = models.CharField(max_length=128, blank=True)
    expected_arrival = models.DateTimeField(null=True, blank=True)

    # Images / ML fields
    visitor_photo = models.ImageField(upload_to="visitor_photos/", null=True, blank=True)
    face_image = models.TextField(null=True, blank=True)  # base64 or encoded payload

    # ML / risk fields
    risk_score = models.FloatField(null=True, blank=True)
    overall_risk_score = models.FloatField(null=True, blank=True)
    face_match_score = models.FloatField(null=True, blank=True)
    text_risk_score = models.FloatField(null=True, blank=True)
    anomaly_score = models.FloatField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    auto_decision = models.BooleanField(default=False)
    approved = models.BooleanField(default=False)

    request_time = models.DateTimeField(auto_now_add=True,null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-request_time",)

    def __str__(self):
        # Defensive stringifier: handles legacy/alternate field names gracefully
        visitor_obj = getattr(self, "visitor", None)
        if visitor_obj:
            visitor_name = getattr(visitor_obj, "full_name", None) or str(visitor_obj)
        else:
            visitor_name = (
                getattr(self, "visitor_name", None)
                or getattr(self, "visitor_full_name", None)
                or "Unknown Visitor"
            )

        target = (
            getattr(self, "target_flat", None)
            or getattr(self, "target_resident_name", None)
            or ""
        )

        parts = [visitor_name]
        if target:
            parts.append(f"-> {target}")
        status = getattr(self, "status", None)
        if status:
            parts.append(f"[{status}]")
        parts.append(f"(id={getattr(self, 'pk', 'n/a')})")

        return " ".join(parts)


class AccessCode(models.Model):
    CODE_TYPES = (
        ("ONE_TIME", "One-time"),
        ("TEMP", "Temporary"),
        ("PERM", "Permanent"),
    )

    # temporary CharField to avoid UUID parsing errors while we sanitize DB
    code = models.CharField(max_length=64, unique=True, null=True, blank=True)

    request = models.ForeignKey(VisitRequest, on_delete=models.CASCADE, related_name="access_codes", null=True, blank=True)
    code_type = models.CharField(max_length=16, choices=CODE_TYPES, default="ONE_TIME")
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_to = models.DateTimeField(null=True, blank=True)
    used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def save(self, *args, **kwargs):
        import uuid
        if not self.code:
            self.code = uuid.uuid4().hex
        super().save(*args, **kwargs)

    def is_valid(self):
        now = timezone.now()
        if self.used:
            return False
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_to and now > self.valid_to:
            return False
        return True

    def __str__(self):
        req_id = getattr(self.request, "pk", "n/a")
        return f"{self.code} (req={req_id})"


class GateEvent(models.Model):
    DIRECTION = (("IN", "In"), ("OUT", "Out"))
    access_code = models.ForeignKey(AccessCode, on_delete=models.SET_NULL, null=True, blank=True, related_name="events")
    direction = models.CharField(max_length=3, choices=DIRECTION, default="IN")
    timestamp = models.DateTimeField(auto_now_add=True)
    verified_by_ml = models.BooleanField(default=False)
    extra = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ("-timestamp",)

    def __str__(self):
        code = getattr(self.access_code, "code", "n/a")
        return f"{code} {self.direction} @ {self.timestamp.isoformat()}"