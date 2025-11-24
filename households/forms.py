from django import forms
from django.contrib.auth.password_validation import validate_password
from core.forms import TAILWIND_INPUT_CLASS, TAILWIND_TEXTAREA_CLASS, TAILWIND_SELECT_CLASS
from core.models import User
from .models import Household


def _apply_error_styles(form):
    """
    Add red border styles to fields with errors to match Tailwind styling.
    """
    if form.errors:
        for name, field in form.fields.items():
            if name in form.errors:
                existing = field.widget.attrs.get('class', '')
                field.widget.attrs['class'] = f"{existing} border-red-400 focus:border-red-400 focus:ring-red-300".strip()


class HouseholdDetailsForm(forms.ModelForm):
    class Meta:
        model = Household
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': TAILWIND_INPUT_CLASS, 'placeholder': 'Household name'}),
            'description': forms.Textarea(attrs={
                'class': TAILWIND_TEXTAREA_CLASS,
                'rows': 3,
                'placeholder': 'Add a short description for members'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_error_styles(self)


class InviteMemberForm(forms.Form):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
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
        widget=forms.EmailInput(attrs={'class': TAILWIND_INPUT_CLASS, 'placeholder': 'member@email.com'})
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_error_styles(self)

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
