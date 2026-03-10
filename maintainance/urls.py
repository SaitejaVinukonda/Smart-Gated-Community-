# maintenance/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("create/", views.create_maintenance_request, name="create_maintenance_request"),
    path("<int:pk>/", views.maintenance_detail, name="maintenance_detail"),
    path("my-tasks/", views.my_tasks, name="my_tasks"), 
    path('tasks/<int:assignment_id>/action/', views.task_action, name='task_action'),  # ✅ CORRECT
    path('tasks/<int:assignment_id>/complete/', views.staff_complete_task, name='staff_complete_task'),
    path('list/', views.maintenance_list, name='maintenance_list'),
]
