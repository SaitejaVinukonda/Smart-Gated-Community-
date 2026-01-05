from django.shortcuts import render

# Create your views here.
# maintenance/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import MaintenanceRequest, Assignment
from .ml_services import recommend_staff_for_request
from .models import MaintenanceRequest, Assignment
#issue raising logic
@login_required
def create_maintenance_request(request):
    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description")
        category = request.POST.get("category")
        priority = int(request.POST.get("priority", 2))

        mr = MaintenanceRequest.objects.create(
            resident=request.user,
            title=title,
            description=description,
            category=category,
            priority=priority,
        )

        staff, score = recommend_staff_for_request(mr)
        if staff:
            now = timezone.now()
            duration = mr.predicted_duration_minutes
            assignment = Assignment.objects.create(
                request=mr,
                staff=staff,
                assigned_at=now,
                predicted_start_time=now,
                predicted_end_time=now + timezone.timedelta(minutes=duration),
                score=score,
            )
            mr.status = MaintenanceRequest.Status.ASSIGNED
            mr.save()

        return redirect("maintenance_detail", pk=mr.pk)

    return render(request, "maintainance/create_request.html")
@login_required
def maintenance_detail(request, pk):
    mr = get_object_or_404(MaintenanceRequest, pk=pk, resident=request.user)
    return render(request, "maintainance/details.html", {"request_obj": mr})

@login_required
def my_tasks(request):
    # only assignments for this staff user
    assignments = Assignment.objects.select_related("request", "staff").filter(
        staff=request.user
    ).order_by(
        "request__status", "-assigned_at"
    )
    return render(request, "maintainance/my_tasks.html", {"assignments": assignments})
