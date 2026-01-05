# visitors/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("create/", views.create_visit_request, name="create_visit_request"),
    path("<int:pk>/", views.visit_request_detail, name="visit_request_detail"),
]
