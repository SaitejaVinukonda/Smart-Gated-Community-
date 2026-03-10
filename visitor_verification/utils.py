"""
Utilities: QR Code Generation, Email Sending, Image Processing
"""

import qrcode
import qrcode.image.svg
from io import BytesIO
import base64
import os
from datetime import datetime, timedelta
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from PIL import Image
import uuid
import logging

logger = logging.getLogger(__name__)


def generate_visitor_qr(visit_log) -> str:
    """
    Generate a QR code for an approved visit.
    Embeds visit token, visitor name, flat number, and expiry.
    Returns the file path of the saved QR code.
    """
    # QR data payload
    qr_data = {
        'token': str(visit_log.qr_token),
        'visitor': visit_log.visitor.name,
        'resident': visit_log.resident.full_address,
        'purpose': visit_log.purpose_category or visit_log.purpose[:50],
        'valid_until': visit_log.qr_valid_until.isoformat() if visit_log.qr_valid_until else '',
        'visit_id': str(visit_log.id),
    }

    # Format QR payload string
    payload = (
        f"VISITOR_ACCESS_TOKEN\n"
        f"Token: {qr_data['token']}\n"
        f"Visitor: {qr_data['visitor']}\n"
        f"Destination: {qr_data['resident']}\n"
        f"Purpose: {qr_data['purpose']}\n"
        f"Valid Until: {qr_data['valid_until']}"
    )

    # Create QR code with custom styling
    qr = qrcode.QRCode(
        version=2,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(payload)
    qr.make(fit=True)

    qr_image = qr.make_image(
        fill_color='#0f0f23',
        back_color='#ffffff'
    )

    # Save to media
    filename = f"qr_{visit_log.id}_{uuid.uuid4().hex[:8]}.png"
    qr_dir = os.path.join(settings.MEDIA_ROOT, 'qr_codes')
    os.makedirs(qr_dir, exist_ok=True)
    filepath = os.path.join(qr_dir, filename)

    qr_image.save(filepath)

    return f'qr_codes/{filename}'


def send_visitor_approval_email(visit_log) -> bool:
    """
    Send approval email to visitor with QR code attached.
    Also sends notification to resident.
    """
    try:
        visitor = visit_log.visitor
        resident = visit_log.resident
        qr_absolute_path = os.path.join(settings.MEDIA_ROOT, str(visit_log.qr_code))

        # ── Email to Visitor ──────────────────────────────────────────
        visitor_subject = f"✅ Visit Approved — {resident.full_address}"
        visitor_context = {
            'visitor_name': visitor.name,
            'resident_name': resident.user.get_full_name(),
            'flat': resident.full_address,
            'purpose': visit_log.purpose,
            'valid_until': visit_log.qr_valid_until,
            'face_confidence': visit_log.face_match_score,
            'token': str(visit_log.qr_token),
        }

        visitor_html = render_to_string(
            'visitor_verification/emails/approval_visitor.html',
            visitor_context
        )
        visitor_text = f"""
Visit Approved!
Visitor: {visitor.name}
Visiting: {resident.user.get_full_name()} at {resident.full_address}
Purpose: {visit_log.purpose}
QR Valid Until: {visit_log.qr_valid_until}
Token: {visit_log.qr_token}
Please show the attached QR code at the gate.
        """

        visitor_email = EmailMultiAlternatives(
            subject=visitor_subject,
            body=visitor_text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[visitor.phone + '@placeholder.com'],  # Use actual visitor email if stored
        )
        visitor_email.attach_alternative(visitor_html, 'text/html')

        # Attach QR code image
        if os.path.exists(qr_absolute_path):
            with open(qr_absolute_path, 'rb') as qr_file:
                visitor_email.attach(
                    filename='visitor_qr_code.png',
                    content=qr_file.read(),
                    mimetype='image/png'
                )

        visitor_email.send(fail_silently=False)

        # ── Notification to Resident ──────────────────────────────────
        resident_subject = f"🔔 Visitor Alert — {visitor.name} at your gate"
        resident_context = {
            'resident_name': resident.user.get_full_name(),
            'visitor_name': visitor.name,
            'purpose': visit_log.purpose,
            'purpose_category': visit_log.purpose_category,
            'face_score': visit_log.face_match_score,
            'visit_id': str(visit_log.id),
        }
        resident_html = render_to_string(
            'visitor_verification/emails/notification_resident.html',
            resident_context
        )

        resident_email = EmailMultiAlternatives(
            subject=resident_subject,
            body=f"Visitor {visitor.name} has been approved to visit you.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[resident.user.email],
        )
        resident_email.attach_alternative(resident_html, 'text/html')
        resident_email.send(fail_silently=False)

        logger.info(f"Emails sent for visit {visit_log.id}")
        return True

    except Exception as e:
        logger.error(f"Email sending failed for visit {visit_log.id}: {e}")
        return False


def save_base64_image(base64_string: str, directory: str, filename: str) -> str:
    """Save a base64 encoded image to media directory"""
    if ',' in base64_string:
        base64_string = base64_string.split(',')[1]

    image_data = base64.b64decode(base64_string)
    image = Image.open(BytesIO(image_data))

    # Ensure directory exists
    full_dir = os.path.join(settings.MEDIA_ROOT, directory)
    os.makedirs(full_dir, exist_ok=True)

    filepath = os.path.join(full_dir, filename)
    image.save(filepath, 'JPEG', quality=95)

    return f'{directory}/{filename}'


def get_qr_as_base64(visit_log) -> str:
    """Return QR code as base64 string for inline display"""
    qr_path = os.path.join(settings.MEDIA_ROOT, str(visit_log.qr_code))
    if os.path.exists(qr_path):
        with open(qr_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    return ''
