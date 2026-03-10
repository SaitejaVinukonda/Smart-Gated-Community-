from django.urls import path
from . import views

app_name = 'visitor_verification'

urlpatterns = [
    path('', views.VisitorFormView.as_view(), name='visitor_form'),
    path('api/residents/', views.ResidentsListAPI.as_view(), name='api_residents'),
    path('verify/', views.VerifyVisitorAPI.as_view(), name='verify_visitor'),
    # Add other paths here
]
