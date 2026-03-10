from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from .models import VisitRequest, Resident
from .ml_engine import xgboost_engine
import uuid
import qrcode
from django.core.mail import send_mail
import json

@csrf_exempt
def ai_security_gate(request):
    """Main 6-Layer AI Security Gate"""
    return render(request, 'visitors/ai_gate.html')

@require_http_methods(["POST"])
@csrf_exempt
def verify_six_layers(request):
    """6-Layer XGBoost verification API"""
    
    try:
        # Extract form data
        data = {
            'name': request.POST.get('name', ''),
            'phone': request.POST.get('phone', ''),
            'email': request.POST.get('email', ''),
            'id_number': request.POST.get('id_number', ''),
            'flat_number': request.POST.get('flat_number', ''),
            'purpose': request.POST.get('purpose', ''),
            'live_photo': request.POST.get('live_photo_b64', ''),
            'id_photo': request.POST.get('id_photo_b64', ''),
        }
        
        print(f"🔍 AI Gate: Verifying {data['name']} → {data['flat_number']}")
        
        # Run 6-layer XGBoost verification
        result = xgboost_engine.verify_visitor(data)
        
        print(f"🎯 XGBoost Result: {result['confidence']:.1%} ({result['approved']})")
        
        # Create VisitRequest record
        visit = VisitRequest.objects.create(
            visitor_name=data['name'],
            visitor_phone=data['phone'],
            visitor_email=data['email'],
            resident_flat=data['flat_number'],
            purpose=data['purpose'],
            live_photo=data['live_photo'],
            id_photo=data['id_photo'],
            **result['layer_scores'],
            overall_confidence=result['confidence'],
            status='approved' if result['approved'] else 'denied'
        )
        
        # Generate QR code
        qr_data = f"VISIT:{visit.id}:{data['flat_number']}"
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_data)
        qr.make(fit=True)
        qr_image = qr.make_image(fill_color="black", back_color="white")
        qr_b64 = self._image_to_b64(qr_image)
        
        visit.qr_code_data = qr_data
        visit.save()
        
        # Send QR via email (production)
        if data['email'] and result['approved']:
            self._send_qr_email(data['email'], qr_data, data['name'])
        
        response = {
            'approved': result['approved'],
            'confidence': result['confidence'],
            'message': '✅ ACCESS APPROVED - Show QR to security' if result['approved'] else '❌ ACCESS DENIED',
            'qr_data': qr_data,
            'visit_id': str(visit.id),
            'layer_scores': result['layer_scores'],
            'weakest_layer': result['weakest_layer']
        }
        
        return JsonResponse(response)
    
    except Exception as e:
        print(f"❌ Verification Error: {str(e)}")
        return JsonResponse({'approved': False, 'error': str(e)}, status=500)

def _image_to_b64(self, image):
    """Convert PIL image to base64"""
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/png;base64,{img_str}"

def _send_qr_email(self, email, qr_data, name):
    """Send QR code via email"""
    try:
        send_mail(
            f'✅ Access Approved - {name}',
            f'Your QR code: {qr_data}\nValid for 24 hours.',
            'noreply@community.com',
            [email],
            fail_silently=True,
        )
    except:
        pass  # Log error
