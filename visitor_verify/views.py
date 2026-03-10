import os
import qrcode
from io import BytesIO
from django.core.files.storage import FileSystemStorage
from django.core.mail import EmailMessage
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from .models import Resident, ParkingSlot, Visitor
from .ml_utils import validate_aadhaar_number, verify_faces


def visitor_page(request):
    # This renders the index.html when you first visit the site
    return render(request, 'index.html')

@csrf_exempt
def register_visitor(request):
    print(f"--- DEBUG: Request Method is {request.method} ---")
    print(f"--- DEBUG: Full Path is {request.get_full_path()} ---")
    if request.method == 'POST':
        name = request.POST.get('name')
        aadhaar_num = request.POST.get('aadhaar_number')
        flat_number = request.POST.get('flat_number')
        purpose = request.POST.get('purpose')
        
        live_photo = request.FILES.get('live_photo')
        aadhaar_photo = request.FILES.get('aadhaar_photo')

        # 1. Validate Aadhaar Number format
        if not validate_aadhaar_number(aadhaar_num):
            return JsonResponse({'status': 'error', 'message': 'Invalid Aadhaar Number format.'})

        # 2. Check if Resident exists
        try:
            resident = Resident.objects.get(flat_number=flat_number)
        except Resident.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Resident/Flat not found.'})

        # Save images temporarily for ML processing
        fs = FileSystemStorage()
        live_path = fs.save(f"temp/live_{aadhaar_num}.jpg", live_photo)
        aadhaar_path = fs.save(f"temp/id_{aadhaar_num}.jpg", aadhaar_photo)
        
        full_live_path = fs.path(live_path)
        full_aadhaar_path = fs.path(aadhaar_path)

        # 3. Machine Learning Face Verification
        is_match = verify_faces(full_live_path, full_aadhaar_path)
        
        # Cleanup temp files securely
        os.remove(full_live_path)
        os.remove(full_aadhaar_path)

        if not is_match:
            return JsonResponse({'status': 'error', 'message': 'Face mismatch! Live photo does not match ID.'})

        # 4. Allocate Parking Slot
        available_slot = ParkingSlot.objects.filter(is_occupied=False).first()
        if available_slot:
            available_slot.is_occupied = True
            available_slot.save()

        # 5. Create Visitor Record
        visitor = Visitor.objects.create(
            name=name,
            aadhaar_number=aadhaar_num,
            purpose=purpose,
            resident_visited=resident,
            allocated_parking=available_slot,
            is_verified=True
        )

        # 6. Generate QR Code
        qr_data = f"Token: {visitor.token_id} | Name: {name} | Parking: {available_slot.slot_number if available_slot else 'None'}"
        qr = qrcode.make(qr_data)
        qr_io = BytesIO()
        qr.save(qr_io, format='PNG')
        qr_io.seek(0)

        # 7. Send Email to Visitor (Assuming visitor provides email, or send to resident)
        visitor_email = request.POST.get('visitor_email') # Assuming you collect this in the form
        if visitor_email:
            email = EmailMessage(
                subject='Your Gate Pass & Parking Details',
                body=f'Hello {name},\n\nYour visit to Flat {flat_number} is approved. \nParking Allocated: {available_slot.slot_number if available_slot else "No Parking Available"}.\n\nPlease show the attached QR code at the entry gate.',
                from_email='security@smartgate.com',
                to=[visitor_email],
            )
            email.attach(f'{name}_gatepass.png', qr_io.read(), 'image/png')
            email.send()

        return JsonResponse({
            'status': 'success', 
            'message': 'Verification successful. Gate pass sent to email.',
            'parking': available_slot.slot_number if available_slot else "None"
        })

    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})