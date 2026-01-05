from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.http import JsonResponse, Http404
import json
import base64
from django.contrib import messages
import numpy as np
from .models import Visitor, VisitRequest, AccessCode
from .advanced_ml import AdvancedVisitorVerifier  # New ML engine
from .ml_services import compute_risk_score  # ADD THIS LINE

# Global ML verifier instance (loads models once)
verifier = AdvancedVisitorVerifier()


@login_required
def create_visit_request(request):
    print("=" * 50)
    print("🔍 DEBUG: Visitor create called")
    print(f"Method: {request.method}")
    print(f"User: {request.user.username}")
    print(f"POST keys: {list(request.POST.keys())}")

    if request.method == "POST":
        v_name = request.POST.get("visitor_name")
        v_phone = request.POST.get("visitor_phone")
        v_email = request.POST.get("visitor_email")
        target_flat = request.POST.get("target_flat")
        target_name = request.POST.get("target_resident_name")
        purpose = request.POST.get("purpose")
        vehicle = request.POST.get("vehicle_number")
        relation = request.POST.get("relation_to_resident")
        expected_time = request.POST.get("expected_arrival")

        if not v_name or not v_phone:
            messages.error(request, "Visitor name and phone are required.")
            return render(request, "visitors/create_request.html")

        visitor, _ = Visitor.objects.get_or_create(
            full_name=v_name,
            phone=v_phone,
            defaults={"email": v_email},
        )

        # Build VisitRequest defensively (only set fields that exist)
        vr = VisitRequest()
        model_fields = {
            f.name
            for f in VisitRequest._meta.get_fields()
            if getattr(f, "concrete", False) and not getattr(f, "auto_created", False)
        }

        data_map = {
            "visitor": visitor,
            "resident": request.user,
            "purpose": purpose,
            "target_flat": target_flat,
            "target_resident_name": target_name,
            "vehicle_number": vehicle,
            "relation_to_resident": relation,
            "expected_arrival": expected_time if expected_time else None,
        }

        for key, val in data_map.items():
            if val is None:
                continue
            if key not in model_fields:
                print(f"⚠️ Skipping field '{key}' — not on VisitRequest model")
                continue
            if key == "expected_arrival" and isinstance(val, str):
                parsed = parse_datetime(val)
                setattr(vr, key, parsed if parsed else val)
            else:
                setattr(vr, key, val)

        # Attach file/base64 fields only if present on model
        if "visitor_photo" in request.FILES and "visitor_photo" in model_fields:
            vr.visitor_photo = request.FILES["visitor_photo"]
        if "face_image" in request.POST and request.POST["face_image"] and "face_image" in model_fields:
            vr.face_image = request.POST["face_image"]

        # Save initial object (so ML, relations, and AccessCode creation have a PK)
        try:
            vr.save()
        except Exception as e:
            messages.error(request, "Failed to create visit request.")
            print("Error saving VisitRequest:", e)
            return render(request, "visitors/create_request.html")

        # ML + save...
        try:
            result = compute_risk_score(vr)
            # compute_risk_score might return a float or a dict with breakdowns
            if isinstance(result, dict):
                risk = float(result.get("overall", result.get("risk", 1.0)))
                # write breakdown fields back to the model if they exist
                for key in ("face", "face_match_score", "text", "text_risk_score", "anomaly", "anomaly_score", "overall", "overall_risk_score"):
                    if key in result and key in model_fields:
                        setattr(vr, key, result[key])
                # Also try common attribute names
                if "overall" in result and "overall_risk_score" in model_fields:
                    setattr(vr, "overall_risk_score", result["overall"])
                if "risk" in result and "risk_score" in model_fields:
                    setattr(vr, "risk_score", result["risk"])
            else:
                risk = float(result)
        except Exception as e:
            messages.error(request, "Failed to compute risk score.")
            risk = 1.0  # conservative fallback
            print("ML error:", e)

        # Set risk on model where appropriate
        if "risk_score" in model_fields:
            vr.risk_score = risk
        elif "overall_risk_score" in model_fields:
            vr.overall_risk_score = risk

        # Auto-decision logic (only set fields that exist)
        try:
            now = timezone.now()
            if risk < 0.6:
                if "auto_decision" in model_fields:
                    vr.auto_decision = True
                # mark explicit approval fields if they exist
                if "approved" in model_fields:
                    vr.approved = True
                vr.save()
                # create access code (works if AccessCode has 'request' FK)
                ac_kwargs = {"request": vr, "code_type": "ONE_TIME", "valid_from": now, "valid_to": now + timezone.timedelta(hours=4)}
                try:
                    AccessCode.objects.create(**{k: v for k, v in ac_kwargs.items() if k in {f.name for f in AccessCode._meta.get_fields()}})
                except Exception as e:
                    print("Warning: AccessCode creation failed:", e)
                return redirect("visit_request_detail", pk=vr.pk)
            else:
                if "auto_decision" in model_fields:
                    vr.auto_decision = False
                if "approved" in model_fields:
                    vr.approved = False
                vr.save()
                messages.warning(request, "Request flagged: higher risk.")
                return render(request, "visitors/create_request.html", {"request_obj": vr})
        except Exception as e:
            messages.error(request, "Failed to finalize request.")
            print("Finalization error:", e)
            return render(request, "visitors/create_request.html", {"request_obj": vr})

    # GET request
    print("🌐 Showing form (GET)")
    return render(request, "visitors/create_request.html")


@login_required
def visit_request_detail(request, pk):
    # Fetch model fields to decide owner check
    model_fields = {
        f.name
        for f in VisitRequest._meta.get_fields()
        if getattr(f, "concrete", False) and not getattr(f, "auto_created", False)
    }

    if "resident" in model_fields:
        vr = get_object_or_404(VisitRequest, pk=pk, resident=request.user)
    else:
        vr = get_object_or_404(VisitRequest, pk=pk)

    # Provide safe ML breakdown values
    context = {"request_obj": vr}
    context["ml_breakdown"] = {
        "face": getattr(vr, "face_match_score", getattr(vr, "face", "N/A")),
        "text": getattr(vr, "text_risk_score", getattr(vr, "text", "N/A")),
        "anomaly": getattr(vr, "anomaly_score", getattr(vr, "anomaly", "N/A")),
        "overall": getattr(vr, "overall_risk_score", getattr(vr, "risk_score", "N/A")),
    }

    return render(request, "visitors/request_detail.html", context)
