from django.urls import path
from . import views
app_name = 'visitor_verify'

urlpatterns = [
    # The endpoint your frontend 'fetch' call hits
    path('api/register-visitor/', views.register_visitor, name='register_visitor'),
]