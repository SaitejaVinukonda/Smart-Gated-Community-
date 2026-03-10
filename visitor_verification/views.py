import json
import uuid
import logging
import base64
from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction

from .models import Visitor, Resident, VisitLog, BlockedVisitor, ParkingSlot
from .ml_utils import face_verifier, purpose_analyzer, aadhaar_ocr, verhoeff_validator
from .utils import generate_visitor_qr, send_visitor_approval_email, save_base64_image
from .forms import VisitorRegistrationForm

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# API: Fetch Residents
# ─────────────────────────────────────────────

class ResidentsListAPI(View):
    """GET endpoint to fetch all verified residents as JSON"""
    
    def get(self, request):
        residents = Resident.objects.filter(is_verified=True).order_by('block', 'flat_number')
        
        residents_data = []
        for resident in residents:
            # Get initials from user's full name
            full_name = resident.user.get_full_name() if resident.user else "Resident"
            initials = ''.join([word[0].upper() for word in full_name.split() if word])[:2]
            if not initials:
                initials = 'R'
            
            residents_data.append({
                'id': resident.id,
                'name': full_name,
                'flat': resident.flat_number,
                'block': resident.block,
                'status': resident.status,
                'initials': initials,
                'phone': resident.phone,
            })
        
        return JsonResponse({
            'success': True,
            'residents': residents_data,
        })


# ─────────────────────────────────────────────
# STEP 1: Visitor Registration Form
# ─────────────────────────────────────────────

class VisitorFormView(View):
    template_name = 'visitor_verification/visitor_form.html'

    def get(self, request):
        residents = Resident.objects.filter(is_verified=True).order_by('block', 'flat_number')
        form = VisitorRegistrationForm()
        return render(request, self.template_name, {
            'form': form,
            'residents': residents,
        })

    def post(self, request):
        form = VisitorRegistrationForm(request.POST, request.FILES)
        residents = Resident.objects.filter(is_verified=True).order_by('block', 'flat_number')

        if not form.is_valid():
            return render(request, self.template_name, {
                'form': form,
                'residents': residents,
                'errors': form.errors,
            })

        return render(request, self.template_name, {
            'form': form,
            'residents': residents,
        })


# ─────────────────────────────────────────────
# STEP 2: Full Verification API
# ─────────────────────────────────────────────

@method_decorator(csrf_exempt, name='dispatch')
class VerifyVisitorAPI(View):
    """
    POST endpoint that runs full verification pipeline:
    1. Aadhaar OCR
    2. Face comparison
    3. Resident availability check
    4. NLP purpose analysis
    5. QR generation + email dispatch
    """

    def post(self, request):
        try:
            # Parse multipart form data
            aadhaar_file = request.FILES.get('aadhaar_image')
            live_photo_b64 = request.POST.get('live_photo')
            resident_id = request.POST.get('resident_id')
            purpose = request.POST.get('purpose', '').strip()
            visitor_phone = request.POST.get('phone', '').strip()
            visitor_email = request.POST.get('visitor_email', '').strip()
            gate_number = request.POST.get('gate_number', 'MAIN')

            errors = []
            if not aadhaar_file:
                errors.append('Aadhaar image is required')
            if not live_photo_b64:
                errors.append('Live photo is required')
            if not resident_id:
                errors.append('Resident is required')
            if not purpose:
                errors.append('Purpose of visit is required')

            if errors:
                return JsonResponse({'success': False, 'errors': errors}, status=400)

            # ── 1. Read and convert Aadhaar image to base64 ────────────
            import os
            from django.conf import settings

            aadhaar_bytes = aadhaar_file.read()
            aadhaar_file.seek(0)  # Reset for potential retry
            
            aadhaar_filename = f"aadhaar_{uuid.uuid4().hex}.jpg"
            aadhaar_dir = os.path.join(settings.MEDIA_ROOT, 'aadhaar_images')
            os.makedirs(aadhaar_dir, exist_ok=True)
            aadhaar_path = os.path.join(aadhaar_dir, aadhaar_filename)

            # Save the file
            with open(aadhaar_path, 'wb') as dest:
                dest.write(aadhaar_bytes)

            aadhaar_relative = f'aadhaar_images/{aadhaar_filename}'

            # ── 2. OCR Aadhaar card ───────────────────────────────────
            try:
                # Convert file bytes to base64 for OCR
                aadhaar_base64 = base64.b64encode(aadhaar_bytes).decode('utf-8')
                aadhaar_base64_data_url = f'data:image/jpeg;base64,{aadhaar_base64}'
                
                ocr_result = aadhaar_ocr.extract_aadhaar(aadhaar_base64_data_url)
                logger.info(f"OCR result: {ocr_result}")
                
                # Try OCR first, fallback to manual entry
                if ocr_result.get('success'):
                    ocr_data = {'aadhaar_number': ocr_result.get('aadhaar')}
                else:
                    # Fallback to manually entered Aadhaar
                    manual_aadhaar = request.POST.get('aadhaar_number', '').replace(' ', '')
                    if not manual_aadhaar or len(manual_aadhaar) != 12:
                        logger.warning(f"OCR failed and no valid manual Aadhaar provided: {manual_aadhaar}")
                        return JsonResponse({
                            'success': False,
                            'message': 'Could not read Aadhaar from image. Please enter your 12-digit Aadhaar number.',
                        }, status=400)
                    ocr_data = {'aadhaar_number': manual_aadhaar}
                    logger.info(f"Using manually entered Aadhaar: {manual_aadhaar}")
                    
            except Exception as e:
                logger.error(f"OCR Error: {str(e)}")
                # Try fallback manual entry
                manual_aadhaar = request.POST.get('aadhaar_number', '').replace(' ', '')
                if not manual_aadhaar or len(manual_aadhaar) != 12:
                    return JsonResponse({
                        'success': False,
                        'message': f'Aadhaar OCR failed: {str(e)}. Please enter your 12-digit Aadhaar manually.',
                    }, status=400)
                ocr_data = {'aadhaar_number': manual_aadhaar}

            # ── 2.5 AADHAAR VALIDATION & COMPARISON ────────────────────
            extracted_aadhaar = ocr_data.get('aadhaar_number', '').replace(' ', '')
            manual_aadhaar = request.POST.get('aadhaar_number', '').replace(' ', '')
            
            logger.info(f"Extracted Aadhaar: {extracted_aadhaar}, Manual Aadhaar: {manual_aadhaar}")
            
            # Validate Verhoeff checksum
            validation_result = verhoeff_validator.validate_aadhaar(extracted_aadhaar)
            aadhaar_checksum_valid = validation_result.get('valid', False)
            
            logger.info(f"Aadhaar checksum validation: {validation_result}")
            
            # Compare extracted vs manual
            aadhaar_match = extracted_aadhaar == manual_aadhaar if extracted_aadhaar else True
            aadhaar_number = extracted_aadhaar or manual_aadhaar
            
            if not aadhaar_number:
                return JsonResponse({
                    'success': False,
                    'message': 'Aadhaar number is required',
                }, status=400)
            
            aadhaar_validation_info = {
                'extracted': extracted_aadhaar,
                'manual': manual_aadhaar,
                'match': aadhaar_match,
                'checksum_valid': aadhaar_checksum_valid,
                'extraction_method': 'ocr' if ocr_data.get('aadhaar_number') else 'manual'
            }

            # ── 3. Check blocked visitors ─────────────────────────────
            aadhaar_number = ocr_data.get('aadhaar_number') or request.POST.get('aadhaar_number', '')
            if aadhaar_number and BlockedVisitor.objects.filter(aadhaar_number=aadhaar_number).exists():
                return JsonResponse({
                    'success': False,
                    'stage': 'blocked',
                    'message': 'Visitor is on the blocked list',
                })

            # ── 4. Face Verification ──────────────────────────────────
            try:
                face_result = face_verifier.verify_visitor(aadhaar_base64_data_url, live_photo_b64)
                logger.info(f"Face verification: {face_result}")
            except Exception as e:
                logger.error(f"Face Verification Error: {str(e)}")
                return JsonResponse({
                    'success': False,
                    'message': f'Face verification failed: {str(e)}',
                }, status=500)

            # ── 5. Save live photo ────────────────────────────────────
            try:
                live_filename = f"live_{uuid.uuid4().hex}.jpg"
                live_relative = save_base64_image(live_photo_b64, 'visitor_photos', live_filename)
            except Exception as e:
                logger.error(f"Live Photo Save Error: {str(e)}")
                return JsonResponse({
                    'success': False,
                    'message': f'Failed to save live photo: {str(e)}',
                }, status=500)

            # ── 6. Get Resident + Check Availability ─────────────────
            try:
                resident = Resident.objects.get(id=resident_id)
            except Resident.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': f'Resident not found with ID: {resident_id}',
                }, status=404)
            
            resident_available = resident.status == 'home'

            # ── 7. NLP Purpose Analysis ───────────────────────────────
            try:
                purpose_result = purpose_analyzer.analyze_purpose(purpose)
                logger.info(f"Purpose analysis: {purpose_result}")
            except Exception as e:
                logger.error(f"Purpose Analysis Error: {str(e)}")
                purpose_result = {'approved': True, 'category': 'general', 'risk_score': 0.5}

            # ── 8. Create Visitor record ──────────────────────────────
            with transaction.atomic():
                visitor, _ = Visitor.objects.get_or_create(
                    aadhaar_number=aadhaar_number,
                    defaults={
                        'name': request.POST.get('visitor_name', 'Unknown Visitor'),
                        'phone': visitor_phone,
                        'aadhaar_image': aadhaar_relative,
                        'live_photo': live_relative,
                    }
                )

                # Update live photo each visit
                visitor.live_photo = live_relative
                visitor.save()

                # ── 9. Determine overall result ───────────────────────
                face_passed = face_result.get('verified', False)
                purpose_passed = purpose_result.get('approved', False)
                all_passed = face_passed and resident_available and purpose_passed

                # Calculate QR expiry (4 hours from now)
                qr_expiry = timezone.now() + timedelta(hours=4) if all_passed else None

                visit_log = VisitLog.objects.create(
                    visitor=visitor,
                    resident=resident,
                    purpose=purpose,
                    purpose_category=purpose_result.get('category'),
                    purpose_risk_score=purpose_result.get('risk_score', 0),
                    face_match_score=face_result.get('confidence', 0),
                    face_verified=face_passed,
                    aadhaar_verified=bool(aadhaar_number),
                    resident_available=resident_available,
                    purpose_approved=purpose_passed,
                    status='approved' if all_passed else self._determine_failure_stage(
                        face_passed, resident_available, purpose_passed
                    ),
                    qr_valid_until=qr_expiry,
                    gate_number=gate_number,
                )

                # ── 10. Allocate Parking Slot ────────────────────────────
                parking_slot = None
                if all_passed:
                    try:
                        # Get first available parking slot
                        parking_slot = ParkingSlot.objects.filter(is_available=True).first()
                        if parking_slot:
                            parking_slot.is_available = False
                            parking_slot.save()
                            visit_log.parking_slot = parking_slot
                            visit_log.save()
                            logger.info(f"Allocated parking slot {parking_slot.slot_number} to visitor {visitor.name}")
                    except Exception as e:
                        logger.warning(f"Could not allocate parking slot: {str(e)}")

                # ── 11. Generate QR + Send Email ──────────────────────
                if all_passed:
                    qr_path = generate_visitor_qr(visit_log)
                    visit_log.qr_code = qr_path
                    visit_log.save()

                    # Send emails asynchronously (or sync here)
                    email_sent = send_visitor_approval_email(visit_log)

            # ── 11. Build Response ────────────────────────────────────
            response_data = {
                'success': all_passed,
                'visit_id': str(visit_log.id),
                'stages': {
                    'aadhaar_ocr': {
                        'passed': bool(aadhaar_number),
                        'aadhaar_number': aadhaar_number,
                        'extracted': aadhaar_validation_info.get('extracted'),
                        'manual': aadhaar_validation_info.get('manual'),
                        'match': aadhaar_validation_info.get('match'),
                        'checksum_valid': aadhaar_validation_info.get('checksum_valid'),
                        'extraction_method': aadhaar_validation_info.get('extraction_method'),
                        'message': f"Aadhaar: {'✓ Valid checksum' if aadhaar_checksum_valid else '⚠ Checksum may be invalid'}",
                    },
                    'face_verification': {
                        'passed': face_passed,
                        'confidence': face_result.get('confidence', 0),
                        'message': face_result.get('message', 'Face verification incomplete'),
                    },
                    'resident_check': {
                        'passed': resident_available,
                        'resident_name': resident.user.get_full_name() if resident.user else 'Unknown',
                        'flat': resident.flat_number,
                        'block': resident.block,
                        'status': resident.status,
                        'message': f'Resident is {resident.status}',
                    },
                    'purpose_analysis': {
                        'passed': purpose_passed,
                        'category': purpose_result.get('category', 'general'),
                        'risk_score': purpose_result.get('risk_score', 0),
                        'message': purpose_result.get('message', 'Purpose analyzed'),
                    },
                },
                'parking_slot': {
                    'slot_number': parking_slot.slot_number if parking_slot else None,
                    'location': parking_slot.location if parking_slot else None,
                } if parking_slot else None,
                'qr_generated': all_passed and bool(visit_log.qr_code),
                'email_sent': all_passed,
                'qr_valid_until': qr_expiry.isoformat() if qr_expiry else None,
                'message': 'Access Granted' if all_passed else 'Access Denied',
            }

            if all_passed and visit_log.qr_code:
                from .utils import get_qr_as_base64
                response_data['qr_base64'] = get_qr_as_base64(visit_log)

            return JsonResponse(response_data, status=200)

        except Exception as e:
            logger.exception(f"Verification error: {e}")
            return JsonResponse({
                'success': False,
                'message': f'Verification failed: {str(e)}',
            }, status=500)

    def _determine_failure_stage(self, face_ok, resident_ok, purpose_ok):
        if not face_ok:
            return 'face_failed'
        if not resident_ok:
            return 'resident_unavailable'
        if not purpose_ok:
            return 'purpose_rejected'
        return 'denied'


# ─────────────────────────────────────────────
# Dashboard Views
# ─────────────────────────────────────────────

@login_required
def guard_dashboard(request):
    """Security guard dashboard showing recent visitors"""
    recent_visits = VisitLog.objects.select_related(
        'visitor', 'resident', 'resident__user'
    ).order_by('-created_at')[:50]

    today_visits = VisitLog.objects.filter(
        created_at__date=timezone.now().date()
    )

    context = {
        'recent_visits': recent_visits,
        'total_today': today_visits.count(),
        'approved_today': today_visits.filter(status='approved').count(),
        'denied_today': today_visits.filter(status__in=['face_failed', 'denied', 'purpose_rejected']).count(),
        'pending_today': today_visits.filter(status='pending').count(),
    }
    return render(request, 'visitor_verification/dashboard.html', context)


@login_required
def resident_dashboard(request):
    """Resident view of incoming visitors"""
    try:
        resident = request.user.resident_profile
    except Resident.DoesNotExist:
        messages.error(request, "No resident profile found.")
        return redirect('/')

    visits = VisitLog.objects.filter(resident=resident).order_by('-created_at')[:30]
    return render(request, 'visitor_verification/resident_dashboard.html', {
        'resident': resident,
        'visits': visits,
    })


def verify_qr_token(request, token):
    """Verify a QR code token at the gate scanner"""
    visit_log = get_object_or_404(VisitLog, qr_token=token)

    is_valid = (
        visit_log.status == 'approved'
        and not visit_log.qr_used
        and visit_log.qr_valid_until
        and timezone.now() < visit_log.qr_valid_until
    )

    if is_valid:
        visit_log.check_in_time = timezone.now()
        visit_log.qr_used = True
        visit_log.status = 'completed'
        visit_log.save()

    return JsonResponse({
        'valid': is_valid,
        'visitor': visit_log.visitor.name,
        'resident': visit_log.resident.full_address,
        'purpose': visit_log.purpose,
        'reason': 'Access granted' if is_valid else 'QR expired or already used',
    })
