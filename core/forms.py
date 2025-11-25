from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from households.models import Household
from .models import User

TAILWIND_INPUT_CLASS = 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent transition-all duration-200'
TAILWIND_TEXTAREA_CLASS = 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent transition-all duration-200 resize-none'
TAILWIND_SELECT_CLASS = 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent transition-all duration-200 bg-white'


class SetupWizardForm(forms.Form):
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'class': TAILWIND_INPUT_CLASS, 'placeholder': 'your@email.com (optional)'})
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

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
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


class InviteSignupForm(forms.Form):
    invite_code = forms.CharField(
        max_length=8,
        widget=forms.TextInput(attrs={'class': TAILWIND_INPUT_CLASS, 'placeholder': '8-character code'})
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'class': TAILWIND_INPUT_CLASS, 'placeholder': 'your@email.com (optional)'})
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
        widget=forms.PasswordInput(attrs={'class': TAILWIND_INPUT_CLASS, 'placeholder': 'Create a password'})
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': TAILWIND_INPUT_CLASS, 'placeholder': 'Confirm password'})
    )

    def clean_invite_code(self):
        code = (self.cleaned_data.get('invite_code') or '').strip().upper()
        if not code:
            raise forms.ValidationError("Invite code is required.")
        if not Household.objects.filter(invite_code=code).exists():
            raise forms.ValidationError("Invalid invite code. Please check with your household admin.")
        return code

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
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


class AdditionalAccountForm(forms.Form):
    ROLE_CHOICES = [
        ('admin', 'Owner / Admin'),
        ('member', 'Member'),
        ('child', 'Child'),
    ]

    first_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': TAILWIND_INPUT_CLASS, 'placeholder': 'First name'})
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={'class': TAILWIND_INPUT_CLASS, 'placeholder': 'Last name (optional)'})
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'class': TAILWIND_INPUT_CLASS, 'placeholder': 'Email (optional)'})
    )
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        initial='member',
        widget=forms.Select(attrs={'class': TAILWIND_SELECT_CLASS})
    )
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'class': TAILWIND_INPUT_CLASS, 'placeholder': 'Set a password (optional)'})
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if password:
            validate_password(password)
        return password

    def is_blank(self):
        """
        Helper to skip entirely empty rows in the formset.
        """
        fields = ['first_name', 'last_name', 'email', 'password']
        return all(not self.data.get(self.add_prefix(field)) for field in fields)


AdditionalAccountFormSet = forms.formset_factory(
    AdditionalAccountForm,
    extra=3,
    max_num=8,
    validate_max=True
)


class LoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': TAILWIND_INPUT_CLASS,
            'placeholder': 'you@example.com'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': TAILWIND_INPUT_CLASS,
            'placeholder': 'Your password'
        })
    )
    remember_me = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'h-4 w-4 text-primary border-gray-300 rounded focus:ring-primary'
        })
    )

    error_messages = {
        'invalid_login': "We couldn't find an account with that email/password.",
        'inactive': "This account is inactive.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._user = None

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')

        if email and password:
            self._user = authenticate(email=email, password=password)
            if self._user is None:
                raise forms.ValidationError(self.error_messages['invalid_login'])
            if not self._user.is_active:
                raise forms.ValidationError(self.error_messages['inactive'])

        return cleaned_data

    def get_user(self):
        return self._user
