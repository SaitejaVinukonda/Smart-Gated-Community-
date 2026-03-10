from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Assignment
from maintainance.models import StaffPerformance

@receiver(post_save, sender=Assignment)
def update_staff_performance(sender, instance, created, **kwargs):
    # ✅ SAFE: Only update on COMPLETED assignments
    if created or not hasattr(instance, 'status'):
        return  # Skip if no status field
    
    if getattr(instance, 'status', None) == 'COMPLETED' and instance.staff:
        performance, _ = StaffPerformance.objects.get_or_create(
            staff=instance.staff,
            defaults={'total_services': 1}
        )
        performance.total_services += 1
        performance.save()
