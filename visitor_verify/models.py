from django.db import models
import uuid

class Resident(models.Model):
    flat_number = models.CharField(max_length=10, unique=True)
    owner_name = models.CharField(max_length=100)
    email = models.EmailField()

    def __str__(self):
        return f"{self.flat_number} - {self.owner_name}"

class ParkingSlot(models.Model):
    slot_number = models.CharField(max_length=10, unique=True)
    is_occupied = models.BooleanField(default=False)

    def __str__(self):
        return self.slot_number

class Visitor(models.Model):
    token_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=100)
    aadhaar_number = models.CharField(max_length=12)
    purpose = models.CharField(max_length=200)
    resident_visited = models.ForeignKey(Resident, on_delete=models.CASCADE)
    allocated_parking = models.ForeignKey(ParkingSlot, on_delete=models.SET_NULL, null=True, blank=True)
    visit_time = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)