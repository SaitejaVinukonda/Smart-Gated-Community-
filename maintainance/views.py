from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.utils.html import strip_tags
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from accounts.models import User, StaffSkill
from community import settings
from .models import MaintenanceRequest, Assignment, ServiceRating
from .ml_services import recommend_staff_for_request
from .email_utils import send_assignment_emails
from django.core.mail import send_mail
from django.template.loader import render_to_string


@login_required
def create_maintenance_request(request):
    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description")
        category = request.POST.get("category").upper()
        priority = int(request.POST.get("priority", 2))

        mr = MaintenanceRequest.objects.create(
            resident=request.user,
            title=title,
            description=description,
            category=category,
            priority=priority,
            status="PENDING",
        )

        staff, success, message = recommend_staff_for_request(mr)

        if success:
            try:
                assignment = mr.assignment  # OneToOne relation
                send_assignment_emails(mr, assignment)
                messages.success(request, f"✅ {message} & email sent")
            except ObjectDoesNotExist:
                messages.warning(request, "⚠️ Assigned but email failed")

        else:
            messages.warning(request, f"⚠️ Created - {message}")

        return redirect("maintenance_detail", pk=mr.pk)

    return render(request, "maintainance/create_request.html")


@login_required
def maintenance_detail(request, pk):
    mr = get_object_or_404(MaintenanceRequest, pk=pk)

    assignment = getattr(mr, "assignment", None)

    if request.method == "POST" and request.user.role == "RESIDENT":
        if assignment:
            ServiceRating.objects.create(
                assignment=assignment,
                rating=int(request.POST["rating"]),
                comment=request.POST.get("comment", ""),
                rated_by=request.user,
            )
            messages.success(request, "⭐ Thanks for your feedback!")
            return redirect("maintenance_detail", pk=pk)

    return render(
        request,
        "maintainance/details.html",
        {"request_obj": mr, "assignment": assignment},
    )
@login_required
def my_tasks(request):
    if request.user.role == 'STAFF':
        assignments = Assignment.objects.filter(
            staff=request.user
        ).select_related('request__resident').order_by("-assigned_at")
        
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start.replace(hour=23, minute=59, second=59, microsecond=999999)
        daily_workload = Assignment.objects.filter(
            staff=request.user,
            assigned_at__range=[today_start, today_end]
        ).count()
        
        context = {
            "assignments": assignments,
            "daily_workload": daily_workload,
            "max_workload": 3,
            "can_accept_more": daily_workload < 3,
            "today_count": daily_workload,
            "total_count": assignments.count(),
            "pending_count": assignments.filter(predicted_start_time__isnull=True).count(),  # ✅ ADDED
        }
        return render(request, "maintainance/my_tasks.html", context)
    return redirect("home")
@login_required
def task_action(request, assignment_id):
    if request.user.role != 'STAFF':
        return redirect("home")
    
    assignment = get_object_or_404(Assignment, id=assignment_id, staff=request.user)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'accept':
            assignment.score = 1.0  # ✅ ACCEPTED = score = 1.0
            assignment.predicted_start_time = timezone.now()
            assignment.save()
            messages.success(request, "✅ Task ACCEPTED!")
            return redirect("staff_complete_task", assignment_id=assignment.id)
        
        elif action == 'reject':
            assignment.delete()
            staff, success, message = recommend_staff_for_request(assignment.request)
            if success:
                messages.success(request, "✅ Task REJECTED & Reassigned!")
            else:
                messages.warning(request, "⚠️ Task REJECTED - No staff available")
            return redirect("my_tasks")
    
    return redirect("my_tasks")


@login_required
def staff_complete_task(request, assignment_id):
    """Staff marks task COMPLETE"""
    if request.user.role != 'STAFF':
        return redirect("home")
    
    assignment = get_object_or_404(Assignment, id=assignment_id, staff=request.user)
    
    if request.method == 'POST':
        assignment.predicted_end_time = timezone.now()
        assignment.save()
        messages.success(request, "✅ Task COMPLETED! Resident can now rate.")
        return redirect("my_tasks")
    
    context = {'assignment': assignment}
    return render(request, "maintainance/complete_task.html", context)

@login_required
def maintenance_list(request):
    if request.user.role == 'RESIDENT':
        requests = MaintenanceRequest.objects.filter(resident=request.user).order_by("-created_at")
    else:
        requests = MaintenanceRequest.objects.all().order_by("-created_at")
    
    context = {'requests': requests}
    return render(request, "maintainance/list.html", context)
def send_resident_notification(request_obj: MaintenanceRequest):
    """📧 Notify resident when staff assigned"""
    try:
        context = {
            'resident_name': request_obj.resident.get_full_name(),
            'staff_name': request_obj.assignment.staff.get_full_name(),
            'title': request_obj.title,
            'app_url': f"http://localhost:8000/maintenance/{request_obj.id}/"
        }
        
        html_message = render_to_string('emails/resident_assigned.html', context)
        send_mail(
            '✅ Your maintenance request has been assigned!',
            strip_tags(html_message),
            settings.DEFAULT_FROM_EMAIL,
            [request_obj.resident.email],
            html_message=html_message,
        )
    except:
        pass  # Silent fail
