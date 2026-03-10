from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        RESIDENT = "RESIDENT", "Resident"
        STAFF = "STAFF", "Maintenance Staff"
        GUARD = "GUARD", "Security Guard"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.RESIDENT,
    )

    flat_number = models.CharField(max_length=20, blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    
    # NEW: Designation field for staff
    class Designation(models.TextChoices):
        PLUMBER = "PLUMBER", "Plumber"
        ELECTRICIAN = "ELECTRICIAN", "Electrician"
        CARPENTER = "CARPENTER", "Carpenter"
        PAINTER = "PAINTER", "Painter"
        HVAC_TECHNICIAN = "HVAC_TECHNICIAN", "HVAC Technician"
        GARDENER = "GARDENER", "Gardener"
        SECURITY_GUARD = "SECURITY_GUARD", "Security Guard"
        CLEANER = "CLEANER", "Cleaner"
        GENERAL = "GENERAL", "General Maintenance"

    designation = models.CharField(
        max_length=20,
        choices=Designation.choices,
        blank=True,
        null=True,
        help_text="Staff designation"
    )

    def is_resident(self):
        return self.role == self.Role.RESIDENT

    def is_staff_member(self):
        return self.role == self.Role.STAFF

    def is_guard(self):
        return self.role == self.Role.GUARD

    def __str__(self):
        return f"{self.username} ({self.role})"


class StaffSkill(models.Model):
    SKILL_CHOICES = [
        ("ELECTRICAL", "Electrical"),
        ("PLUMBING", "Plumbing"),
        ("CLEANING", "Cleaning"),
        ("SECURITY", "Security Systems"),
        ("GENERAL", "General Maintenance"),
        ("CARPENTRY", "Carpentry"),
        ("PAINTING", "Painting"),
        ("HVAC", "HVAC"),
        ("GARDENING", "Gardening"),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="staff_skills")
    skill = models.CharField(max_length=50, choices=SKILL_CHOICES)
    experience_years = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("user", "skill")

    def __str__(self):
        return f"{self.user.username} - {self.skill}"

