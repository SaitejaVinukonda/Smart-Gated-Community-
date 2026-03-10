from django.urls import path
from . import views

urlpatterns = [
    path('', views.ai_security_gate, name='ai_gate'),           # ✅ Main gate
    path('verify_six_layers/', views.verify_six_layers, name='verify'),  # ✅ API
    path('create/', views.ai_security_gate, name='create'),     # ✅ ADDED FOR YOU
]
