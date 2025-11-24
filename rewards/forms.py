from django import forms
from django.utils import timezone
from core.forms import (
    TAILWIND_INPUT_CLASS,
    TAILWIND_TEXTAREA_CLASS,
    TAILWIND_SELECT_CLASS,
)
from core.models import User
from households.models import Household, HouseholdMembership
from .models import Reward


class RewardForm(forms.Form):
    title = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': TAILWIND_INPUT_CLASS, 'placeholder': 'e.g., Movie Night'})
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': TAILWIND_TEXTAREA_CLASS, 'rows': 3, 'placeholder': 'Details or how to claim'})
    )
    instructions = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': TAILWIND_TEXTAREA_CLASS, 'rows': 3, 'placeholder': 'Pickup or delivery instructions'})
    )
    household = forms.ModelChoiceField(
        queryset=Household.objects.none(),
        widget=forms.Select(attrs={'class': TAILWIND_SELECT_CLASS})
    )
    point_cost = forms.IntegerField(
        min_value=1,
        initial=10,
        widget=forms.NumberInput(attrs={'class': TAILWIND_INPUT_CLASS})
    )
    category = forms.ChoiceField(
        choices=Reward.CATEGORY_CHOICES,
        initial='other',
        widget=forms.Select(attrs={'class': TAILWIND_SELECT_CLASS})
    )
    quantity_available = forms.IntegerField(
        min_value=1,
        required=False,
        widget=forms.NumberInput(attrs={'class': TAILWIND_INPUT_CLASS})
    )
    unlimited_quantity = forms.BooleanField(required=False, initial=True)
    per_user_limit = forms.IntegerField(
        min_value=1,
        required=False,
        widget=forms.NumberInput(attrs={'class': TAILWIND_INPUT_CLASS})
    )
    cooldown_days = forms.IntegerField(
        min_value=1,
        required=False,
        widget=forms.NumberInput(attrs={'class': TAILWIND_INPUT_CLASS})
    )
    low_stock_threshold = forms.IntegerField(
        min_value=1,
        required=False,
        widget=forms.NumberInput(attrs={'class': TAILWIND_INPUT_CLASS})
    )
    allowed_members = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': TAILWIND_SELECT_CLASS})
    )
    tags = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': TAILWIND_INPUT_CLASS, 'placeholder': 'fun, weekend, family'})
    )
    requires_approval = forms.BooleanField(required=False, initial=True)
    is_featured = forms.BooleanField(required=False)
    is_active = forms.BooleanField(required=False, initial=True)
    available_from = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'class': TAILWIND_INPUT_CLASS, 'type': 'datetime-local'})
    )
    available_until = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'class': TAILWIND_INPUT_CLASS, 'type': 'datetime-local'})
    )

    def __init__(self, *args, user=None, household=None, instance=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance = instance

        target_household = household or (instance.household if instance else None)

        if user:
            if user.is_staff or getattr(user, 'role', None) == 'admin':
                households = Household.objects.all()
            else:
                households = Household.objects.filter(memberships__user=user).distinct()
            self.fields['household'].queryset = households
            if target_household:
                self.fields['household'].initial = target_household.id
                self.fields['allowed_members'].queryset = User.objects.filter(
                    household_memberships__household=target_household
                ).distinct()
                self.fields['allowed_members'].label_from_instance = (
                    lambda obj: obj.full_name or obj.email or f"User {obj.id}"
                )

        if not self.is_bound:
            self.fields['category'].initial = 'other'
            self.fields['requires_approval'].initial = True
            self.fields['is_active'].initial = True
            self.fields['unlimited_quantity'].initial = True

            if instance:
                self.fields['title'].initial = instance.title
                self.fields['description'].initial = instance.description
                self.fields['instructions'].initial = instance.instructions
                self.fields['household'].initial = instance.household_id
                self.fields['point_cost'].initial = instance.point_cost
                self.fields['category'].initial = instance.category
                self.fields['quantity_available'].initial = instance.quantity_available
                self.fields['unlimited_quantity'].initial = instance.quantity_available is None
                self.fields['per_user_limit'].initial = instance.per_user_limit
                self.fields['cooldown_days'].initial = instance.cooldown_days
                self.fields['low_stock_threshold'].initial = instance.low_stock_threshold
                self.fields['allowed_members'].initial = list(instance.allowed_members.values_list('id', flat=True))
                self.fields['tags'].initial = instance.tags
                self.fields['requires_approval'].initial = instance.requires_approval
                self.fields['is_featured'].initial = instance.is_featured
                self.fields['is_active'].initial = instance.is_active
                self.fields['available_from'].initial = instance.available_from
                self.fields['available_until'].initial = instance.available_until

        if self.errors:
            for name, field in self.fields.items():
                if name in self.errors:
                    existing = field.widget.attrs.get('class', '')
                    field.widget.attrs['class'] = f"{existing} border-red-400 focus:border-red-400 focus:ring-red-300".strip()

    def clean(self):
        cleaned = super().clean()
        available_from = cleaned.get('available_from')
        available_until = cleaned.get('available_until')
        if available_from and available_until and available_until <= available_from:
            self.add_error('available_until', 'End date must be after start date.')

        unlimited = cleaned.get('unlimited_quantity')
        quantity = cleaned.get('quantity_available')
        if not unlimited and not quantity:
            self.add_error('quantity_available', 'Enter a quantity or mark as unlimited.')

        if unlimited:
            cleaned['quantity_available'] = None

        tags = cleaned.get('tags') or ''
        cleaned['tags'] = ','.join(
            part.strip() for part in tags.split(',') if part.strip()
        )

        # Normalize past availability to now if not provided.
        if available_from and available_from.tzinfo is None:
            cleaned['available_from'] = timezone.make_aware(available_from)
        if available_until and available_until.tzinfo is None:
            cleaned['available_until'] = timezone.make_aware(available_until)

        return cleaned
