# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, StaffSkill

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Additional info", {"fields": ("role", "flat_number", "phone")}),
    )
    list_display = ("username", "email", "role", "flat_number")

admin.site.register(StaffSkill)
