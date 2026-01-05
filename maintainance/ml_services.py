# maintenance/ml_services.py
from django.utils import timezone
from django.db.models import Count
import numpy as np
from accounts.models import StaffSkill, User
from .models import MaintenanceRequest

def recommend_staff_for_request(request_obj: MaintenanceRequest):
    """
    Example “complex” logic + ML-like scoring:
      - staff with matching skill gets bonus
      - fewer open tickets → better score
      - high priority → penalize staff with many critical tasks
    """
    staff_qs = User.objects.filter(role=User.Role.STAFF).annotate(
        open_tasks=Count("assignment", filter=None)
    )

    best_staff = None
    best_score = -1.0

    for staff in staff_qs:
        # skill match
        has_skill = StaffSkill.objects.filter(
            user=staff,
            skill=request_obj.category
        ).exists()
        skill_score = 1.0 if has_skill else 0.3

        # workload penalty
        workload_penalty = 1.0 / (1 + staff.open_tasks)

        # priority factor
        priority_factor = 1.0 + (request_obj.priority - 2) * 0.2

        raw = skill_score * workload_penalty * priority_factor
        if raw > best_score:
            best_score = raw
            best_staff = staff

    return best_staff, float(best_score)
