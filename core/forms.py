from django import forms
from django.contrib.auth.password_validation import validate_password
from .models import User

TAILWIND_INPUT_CLASS = 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent transition-all duration-200'
TAILWIND_TEXTAREA_CLASS = 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent transition-all duration-200 resize-none'


class SetupWizardForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': TAILWIND_INPUT_CLASS, 'placeholder': 'Choose a username'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': TAILWIND_INPUT_CLASS, 'placeholder': 'your@email.com'})
    )
    first_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': TAILWIND_INPUT_CLASS, 'placeholder': 'First name'})
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={'class': TAILWIND_INPUT_CLASS, 'placeholder': 'Last name (optional)'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': TAILWIND_INPUT_CLASS, 'placeholder': 'Choose a strong password'})
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': TAILWIND_INPUT_CLASS, 'placeholder': 'Confirm password'})
    )
    household_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': TAILWIND_INPUT_CLASS, 'placeholder': 'e.g., Smith Family, Apartment 4B'})
    )
    household_description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': TAILWIND_TEXTAREA_CLASS,
            'placeholder': 'Optional description of your household',
            'rows': 3
        })
    )

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email

    def clean_password(self):
        password = self.cleaned_data.get('password')
        validate_password(password)
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError("Passwords do not match.")

        return cleaned_data
