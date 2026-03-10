#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'community.settings')
django.setup()

from visitor_verification.models import ParkingSlot

# Check if parking slots exist
slots = ParkingSlot.objects.all()
print(f"Total parking slots: {slots.count()}")

# Create sample parking slots if none exist
if slots.count() == 0:
    slots_to_create = [
        {'slot_number': 'A-001', 'location': 'Ground Floor - Near Main Gate', 'is_available': True},
        {'slot_number': 'A-002', 'location': 'Ground Floor - Near Main Gate', 'is_available': True},
        {'slot_number': 'A-003', 'location': 'Ground Floor - Near Main Gate', 'is_available': True},
        {'slot_number': 'B-001', 'location': 'Level 1 - Parking Block B', 'is_available': True},
        {'slot_number': 'B-002', 'location': 'Level 1 - Parking Block B', 'is_available': True},
        {'slot_number': 'B-003', 'location': 'Level 1 - Parking Block B', 'is_available': True},
        {'slot_number': 'C-001', 'location': 'Level 2 - Parking Block C', 'is_available': True},
        {'slot_number': 'C-002', 'location': 'Level 2 - Parking Block C', 'is_available': True},
    ]
    
    for slot_data in slots_to_create:
        ParkingSlot.objects.create(**slot_data)
    
    print(f"✅ Created {len(slots_to_create)} parking slots:")
    for slot_data in slots_to_create:
        print(f"   - Slot: {slot_data['slot_number']} - {slot_data['location']}")
else:
    print(f"✅ Parking slots already exist:")
    for slot in slots:
        print(f"   - Slot: {slot.slot_number} - {slot.location} - Available: {slot.is_available}")
