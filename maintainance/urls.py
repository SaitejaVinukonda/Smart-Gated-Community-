# maintenance/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("create/", views.create_maintenance_request, name="create_maintenance_request"),
    path("<int:pk>/", views.maintenance_detail, name="maintenance_detail"),
    path("my-tasks/", views.my_tasks, name="my_tasks"), 
]
