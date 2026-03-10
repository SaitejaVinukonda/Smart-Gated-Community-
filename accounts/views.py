from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import User

@login_required
def profile(request):
    """User profile page - handles /accounts/profile/ redirect"""
    user = request.user
    context = {
        'user': user,
        'role_display': user.get_role_display() if hasattr(user, 'get_role_display') else user.role,
    }
    return render(request, 'accounts/profile.html', context)
