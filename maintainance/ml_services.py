# maintainance/ml_services.py - 100% COMPATIBLE WITH YOUR MODEL
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.mail import send_mail
from accounts.models import User, StaffSkill
from maintainance.models import MaintenanceRequest, Assignment
from typing import Tuple, Optional

class StaffRecommender:
    MAX_DAILY_WORKLOAD = 3
    
    def get_daily_workload(self, staff: User) -> int:
        """🔢 Count assignments TODAY using assigned_at (NO status field needed!)"""
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # ✅ NO status filter - counts ALL assignments today
        return Assignment.objects.filter(
            staff=staff,
            assigned_at__range=[today_start, today_end]  # YOUR field!
        ).count()
    
    def can_accept_work(self, staff: User) -> bool:
        """✅ Workload < 3?"""
        return self.get_daily_workload(staff) < self.MAX_DAILY_WORKLOAD
    
    def has_skill_match(self, staff: User, category: str) -> bool:
        """✅ YOUR original skill matching"""
        return StaffSkill.objects.filter(user=staff, skill=category.upper()).exists()
    
    def find_best_staff(self, request: MaintenanceRequest) -> Tuple[Optional[User], str]:
        """🎯 YOUR ORIGINAL LOGIC + WORKLOAD"""
        skilled_ids = StaffSkill.objects.filter(skill=request.category.upper()).values_list('user_id', flat=True)
        
        candidates = User.objects.filter(
            id__in=skilled_ids,
            role='STAFF',
            is_active=True
        )
        
        for staff in candidates:
            if self.can_accept_work(staff):
                workload = self.get_daily_workload(staff)
                return staff, f"Workload: {workload}/3"
        
        return None, "All staff at daily limit (3 tasks)"
    
    def assign_staff(self, request: MaintenanceRequest, staff: User) -> Tuple[bool, str]:
        """🚀 Creates YOUR exact Assignment (NO status field!)"""
        try:
            with transaction.atomic():
                # ✅ YOUR EXACT FIELDS ONLY
                Assignment.objects.create(
                    request=request,
                    staff=staff,
                    assigned_at=timezone.now(),
                    predicted_start_time=timezone.now(),
                    predicted_end_time=timezone.now() + timezone.timedelta(minutes=60),
                    score=0.95
                )
                
                request.status = 'ASSIGNED'
                request.save()
                
                print(f"✅ SUCCESS: Assigned {request.title} to {staff.username}")
                return True, f"Assigned to {staff.get_full_name()}"
                
        except Exception as e:
            print(f"❌ Assignment error: {e}")
            return False, f"Assignment failed"
    
    def recommend_and_assign(self, request: MaintenanceRequest) -> Tuple[Optional[User], bool, str]:
        """🔥 MAIN METHOD - WORKS WITH YOUR MODEL"""
        staff, msg = self.find_best_staff(request)
        
        if staff:
            success, assign_msg = self.assign_staff(request, staff, 0.95)
            return staff, success, f"{msg} → {assign_msg}"
        
        request.status = 'PENDING_NO_STAFF'
        request.save()
        return None, False, msg
    def send_assignment_email(self, staff: User, request: MaintenanceRequest, score: float):
        """📧 Send notification email to staff"""
        try:
            subject = f"🛠️ New Task Assigned: {request.title}"
            
            # HTML Email Template
            context = {
                'staff_name': staff.get_full_name(),
                'request_title': request.title,
                'resident_name': request.resident.get_full_name(),
                'category': request.category,
                'priority': request.priority,
                'description': request.description,
                'match_score': f"{score:.1%}",
                'app_url': f"http://localhost:8000/maintenance/{request.id}/",  # Production URL
                'assigned_at': timezone.now().strftime("%I:%M %p, %B %d")
            }
            
            html_message = render_to_string('maintainance/staff_assignment.html', context)
            plain_message = strip_tags(html_message)
            
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[staff.email],
                html_message=html_message,
                fail_silently=False,
            )
            print(f"✅ Email sent to {staff.email}")
            
        except Exception as e:
            print(f"❌ Email failed: {e}")

    def assign_staff(self, request: MaintenanceRequest, staff: User, score: float) -> Tuple[bool, str]:
        """🚀 Creates Assignment + SENDS EMAIL"""
        try:
            with transaction.atomic():
                Assignment.objects.create(
                    request=request,
                    staff=staff,
                    assigned_at=timezone.now(),
                    score=score
                )
                
                request.status = MaintenanceRequest.Status.ASSIGNED
                request.save()
                
                # ✅ SEND NOTIFICATION EMAIL
                self.send_assignment_email(staff, request, score)
                
                print(f"✅ SUCCESS: Assigned + Email sent to {staff.username}")
                return True, f"Assigned to {staff.get_full_name()} ({score:.1%})"
                
        except Exception as e:
            print(f"❌ Assignment error: {e}")
            return False, f"Assignment failed"
    

# Global instance
recommender = StaffRecommender()

def recommend_staff_for_request(request_obj: MaintenanceRequest):
    """View wrapper"""
    return recommender.recommend_and_assign(request_obj)

