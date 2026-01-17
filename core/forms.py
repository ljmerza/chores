from typing import Dict, List

from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.validators import UnicodeUsernameValidator
from households.models import Household
from chores.models import ChoreTemplate
from .models import User

TAILWIND_INPUT_CLASS = 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent transition-all duration-200'
TAILWIND_TEXTAREA_CLASS = 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent transition-all duration-200 resize-none'
TAILWIND_SELECT_CLASS = 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent transition-all duration-200 bg-white'

username_validator = UnicodeUsernameValidator()


class SetupWizardForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        validators=[username_validator],
        widget=forms.TextInput(attrs={'class': TAILWIND_INPUT_CLASS, 'placeholder': 'username'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': TAILWIND_INPUT_CLASS, 'placeholder': 'you@email.com'})
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
        username = (self.cleaned_data.get('username') or '').strip()
        if not username:
            raise forms.ValidationError("Username is required.")
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip()
        if not email:
            raise forms.ValidationError("Email is required to create a household owner account.")
        if User.objects.filter(email__iexact=email).exists():
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


class HouseholdSignupForm(SetupWizardForm):
    """
    Mirrors the setup wizard fields/validation but is used for the public
    create-household flow (no staff/superuser defaults are applied here).
    """


class InviteCodeForm(forms.Form):
    invite_code = forms.CharField(
        max_length=8,
        widget=forms.TextInput(attrs={'class': TAILWIND_INPUT_CLASS, 'placeholder': '8-character code'})
    )

    def clean_invite_code(self):
        code = (self.cleaned_data.get('invite_code') or '').strip().upper()
        if not code:
            raise forms.ValidationError("Invite code is required.")
        household = Household.objects.filter(invite_code=code).first()
        if not household:
            raise forms.ValidationError("Invalid invite code. Please check with your household admin.")
        self.household = household
        return code


class InviteAccountForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        validators=[username_validator],
        widget=forms.TextInput(attrs={'class': TAILWIND_INPUT_CLASS, 'placeholder': 'Pick a username'})
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

    def clean_username(self):
        username = (self.cleaned_data.get('username') or '').strip()
        if not username:
            raise forms.ValidationError("Username is required.")
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            if User.objects.filter(email__iexact=email).exists():
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

    username = forms.CharField(
        required=False,
        max_length=150,
        validators=[username_validator],
        widget=forms.TextInput(attrs={'class': TAILWIND_INPUT_CLASS, 'placeholder': 'username'})
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
        email = (self.cleaned_data.get('email') or '').strip()
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email

    def clean_username(self):
        username = (self.cleaned_data.get('username') or '').strip()
        if not username:
            return username
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if password:
            validate_password(password)
        return password

    def clean(self):
        cleaned_data = super().clean()
        if self.is_blank():
            return cleaned_data
        role = (cleaned_data.get('role') or 'member')
        email = (cleaned_data.get('email') or '').strip()
        if role in ['admin', 'member'] and not email:
            self.add_error('email', "Email is required for admins/parents.")
        if not (cleaned_data.get('username') or '').strip():
            raise forms.ValidationError("Username is required for each account.")
        return cleaned_data

    def is_blank(self):
        """
        Helper to skip entirely empty rows in the formset.
        """
        fields = ['username', 'first_name', 'last_name', 'email', 'password']
        return all(not self.data.get(self.add_prefix(field)) for field in fields)


AdditionalAccountFormSet = forms.formset_factory(
    AdditionalAccountForm,
    extra=3,
    max_num=8,
    validate_max=True
)


class LoginForm(forms.Form):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': TAILWIND_INPUT_CLASS,
            'placeholder': 'your username'
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
        'invalid_login': "We couldn't find an account with that username/password.",
        'inactive': "This account is inactive.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._user = None

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')

        if username and password:
            self._user = authenticate(username=username, password=password)
            if self._user is None:
                raise forms.ValidationError(self.error_messages['invalid_login'])
            if not self._user.is_active:
                raise forms.ValidationError(self.error_messages['inactive'])

        return cleaned_data

    def get_user(self):
        return self._user


class HomeAssistantTargetForm(forms.Form):
    """
    Edit per-user Home Assistant notify targets for a household.
    """
    FIELD_PREFIX = "ha_target"

    def __init__(self, *args, users=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.users = users or []
        for user in self.users:
            field_name = self.field_name(user.id)
            self.fields[field_name] = forms.CharField(
                required=False,
                max_length=150,
                label=user.display_name,
                widget=forms.TextInput(attrs={
                    'class': TAILWIND_INPUT_CLASS,
                    'placeholder': 'notify.mobile_app_your_device',
                }),
                help_text="Home Assistant notify service name",
            )
            if getattr(user, "homeassistant_target", None):
                self.initial[field_name] = user.homeassistant_target

    @classmethod
    def field_name(cls, user_id: int) -> str:
        return f"{cls.FIELD_PREFIX}_{user_id}"

    def cleaned_targets(self) -> Dict[int, str]:
        targets: Dict[int, str] = {}
        for user in self.users:
            raw = self.cleaned_data.get(self.field_name(user.id), "") or ""
            targets[user.id] = raw.strip()
        return targets


class HomeAssistantSettingsForm(forms.ModelForm):
    """
    Household-level Home Assistant configuration (per-household).
    """
    class Meta:
        model = Household
        fields = ['ha_base_url', 'ha_token', 'ha_default_target', 'ha_verify_ssl']
        widgets = {
            'ha_base_url': forms.URLInput(attrs={'class': TAILWIND_INPUT_CLASS, 'placeholder': 'http://homeassistant.local:8123'}),
            'ha_token': forms.TextInput(attrs={'class': TAILWIND_INPUT_CLASS, 'placeholder': 'Long-lived access token'}),
            'ha_default_target': forms.TextInput(attrs={'class': TAILWIND_INPUT_CLASS, 'placeholder': 'notify.mobile_app_default'}),
            'ha_verify_ssl': forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-primary border-gray-300 rounded focus:ring-primary'}),
        }


class TemplateSelectionForm(forms.Form):
    """
    Form for selecting pre-made chore templates during setup.
    """
    templates = forms.MultipleChoiceField(
        required=False,
        widget=forms.CheckboxSelectMultiple()
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        templates = ChoreTemplate.objects.filter(
            household__isnull=True, is_public=True
        ).order_by('category', 'title')
        self.fields['templates'].choices = [
            (str(t.id), t.title) for t in templates
        ]
        self.template_objects = {str(t.id): t for t in templates}

    def get_selected_templates(self) -> List[ChoreTemplate]:
        """Return the selected ChoreTemplate instances."""
        selected_ids = self.cleaned_data.get('templates', [])
        return [self.template_objects[tid] for tid in selected_ids if tid in self.template_objects]
