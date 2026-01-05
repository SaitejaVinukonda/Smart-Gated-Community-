# community/views.py
from django.shortcuts import render
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.contrib import messages

def home(request):
    return render(request, "base.html")
def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out successfully!")
    return redirect("home")
