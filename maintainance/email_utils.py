from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings


def send_assignment_emails(request_obj, assignment):
    staff = assignment.staff
    resident = request_obj.resident

    # ---------- STAFF EMAIL ----------
    staff_subject = "🛠 New Maintenance Task Assigned"

    staff_html = render_to_string("maintainance/staff_assignment.html", {
    "staff_name": staff.get_full_name() or staff.username,
    "title": request_obj.title,           # ✅ Add this
    "category": request_obj.category,     # ✅ Add this  
    "priority": request_obj.priority,     # ✅ Add this
    "resident": resident.get_full_name() or resident.username,  # ✅ Add this
    "flat": getattr(resident, 'flat_number', None),
    "description": request_obj.description or "Check resident's description",
})

    staff_email = EmailMultiAlternatives(
        subject=staff_subject,
        body="New maintenance task assigned",
        from_email=settings.EMAIL_HOST_USER,
        to=[staff.email],
    )
    staff_email.attach_alternative(staff_html, "text/html")
    staff_email.send()


    # ---------- RESIDENT EMAIL ----------
    resident_subject = "✅ Maintenance Request Assigned"

    resident_html = render_to_string("maintainance/resident_assignment.html", {
        "resident_name": resident.get_full_name() or resident.username,
        "title": request_obj.title,
        "category": request_obj.category,
        "priority": request_obj.priority,
        "staff_name": staff.get_full_name() or staff.username,
        "skill": getattr(staff, 'skill', 'General Maintenance'),
        "phone": staff.phone,
        "email": staff.email,
    })
    # Debug: print context to verify values
    print({
        "resident_name": resident.get_full_name() or resident.username,
        "title": request_obj.title,
        "category": request_obj.category,
        "priority": request_obj.priority,
        "staff_name": staff.get_full_name() or staff.username,
        "designation": staff.designation,
    })

    resident_email = EmailMultiAlternatives(
        subject=resident_subject,
        body="Your request has been assigned",
        from_email=settings.EMAIL_HOST_USER,
        to=[resident.email],
    )
    resident_email.attach_alternative(resident_html, "text/html")
    resident_email.send()
