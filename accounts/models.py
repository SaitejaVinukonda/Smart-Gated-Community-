# accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

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

    def is_resident(self):
        return self.role == self.Role.RESIDENT

    def is_staff_member(self):
        return self.role == self.Role.STAFF

    def is_guard(self):
        return self.role == self.Role.GUARD


class StaffSkill(models.Model):
    SKILL_CHOICES = [
        ("ELECTRICAL", "Electrical"),
        ("PLUMBING", "Plumbing"),
        ("CLEANING", "Cleaning"),
        ("SECURITY", "Security Systems"),
        ("GENERAL", "General Maintenance"),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="skills")
    skill = models.CharField(max_length=50, choices=SKILL_CHOICES)
    experience_years = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("user", "skill")

    def __str__(self):
        return f"{self.user.username} - {self.skill}"
