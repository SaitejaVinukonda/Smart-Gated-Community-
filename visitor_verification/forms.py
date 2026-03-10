from django import forms
from .models import Visitor, VisitLog


class VisitorRegistrationForm(forms.Form):
    visitor_name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'placeholder': 'Full name as on Aadhaar'})
    )
    phone = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={'placeholder': '+91 XXXXX XXXXX'})
    )
    visitor_email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'placeholder': 'visitor@email.com'})
    )
    aadhaar_number = forms.CharField(
        max_length=12,
        min_length=12,
        widget=forms.TextInput(attrs={'placeholder': '12-digit Aadhaar number'})
    )
    aadhaar_image = forms.ImageField(
        help_text='Upload Aadhaar card front side (JPG/PNG)'
    )
    purpose = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'Describe your purpose of visit...'
        })
    )
    resident_id = forms.IntegerField(widget=forms.HiddenInput())

    def clean_aadhaar_number(self):
        aadhaar = self.cleaned_data['aadhaar_number'].replace(' ', '')
        if not aadhaar.isdigit() or len(aadhaar) != 12:
            raise forms.ValidationError('Enter a valid 12-digit Aadhaar number')
        return aadhaar

    def clean_aadhaar_image(self):
        image = self.cleaned_data['aadhaar_image']
        if image.size > 5 * 1024 * 1024:  # 5MB
            raise forms.ValidationError('Aadhaar image must be less than 5MB')
        return image
