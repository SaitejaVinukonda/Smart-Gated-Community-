# maintenance/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone
from accounts.models import StaffSkill

User = settings.AUTH_USER_MODEL

class MaintenanceRequest(models.Model):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        ASSIGNED = "ASSIGNED", "Assigned"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        COMPLETED = "COMPLETED", "Completed"

    PRIORITY_CHOICES = [
        (1, "Low"),
        (2, "Medium"),
        (3, "High"),
        (4, "Critical"),
    ]

    resident = models.ForeignKey(User, on_delete=models.CASCADE, related_name="maintenance_requests")
    title = models.CharField(max_length=100)
    description = models.TextField()
    category = models.CharField(
        max_length=50,
        choices=StaffSkill.SKILL_CHOICES,
        default="GENERAL",
    )
    created_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=2)

    predicted_duration_minutes = models.IntegerField(default=30)

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"


class Assignment(models.Model):
    request = models.OneToOneField(MaintenanceRequest, on_delete=models.CASCADE, related_name="assignment")
    staff = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={"role": "STAFF"})
    assigned_at = models.DateTimeField(default=timezone.now)
    predicted_start_time = models.DateTimeField(blank=True, null=True)
    predicted_end_time = models.DateTimeField(blank=True, null=True)
    score = models.FloatField(default=0.0)  # ML score for suitability
     # ✅ NEW FIELDS - Accept/Reject
    accepted = models.BooleanField(default=False)
    rejected = models.BooleanField(default=False)
    rejection_reason = models.TextField(blank=True, null=True)
    accepted_at = models.DateTimeField(blank=True, null=True)
    
    def __str__(self):
        status = "Accepted" if self.accepted else "Rejected" if self.rejected else "Pending"
        return f"{self.request.title} → {self.staff} [{status}]"
class StaffPerformance(models.Model):
    staff = models.OneToOneField(User, on_delete=models.CASCADE, related_name='performance')
    total_services = models.PositiveIntegerField(default=0)
    avg_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)
    updated_at = models.DateTimeField(auto_now=True)

class ServiceRating(models.Model):
    assignment = models.ForeignKey('Assignment', on_delete=models.CASCADE, related_name='ratings')
    rating = models.PositiveSmallIntegerField(choices=[(i, i) for i in range(1, 6)])  # 1-5 stars
    comment = models.TextField(blank=True)
    rated_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)
