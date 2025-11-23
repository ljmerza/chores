from django import forms
from django.utils import timezone
from core.models import User
from households.models import Household, HouseholdMembership
from .models import Chore

TAILWIND_INPUT_CLASS = 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent transition-all duration-200'
TAILWIND_SELECT_CLASS = 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent transition-all duration-200 bg-white'
TAILWIND_TEXTAREA_CLASS = 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent transition-all duration-200 resize-none'

DAY_OF_WEEK_CHOICES = [
    ('mon', 'Monday'),
    ('tue', 'Tuesday'),
    ('wed', 'Wednesday'),
    ('thu', 'Thursday'),
    ('fri', 'Friday'),
    ('sat', 'Saturday'),
    ('sun', 'Sunday'),
]

WEEK_OF_MONTH_CHOICES = [
    ('first', 'First'),
    ('second', 'Second'),
    ('third', 'Third'),
    ('fourth', 'Fourth'),
    ('last', 'Last'),
]

MONTH_CHOICES = [
    ('1', 'Jan'), ('2', 'Feb'), ('3', 'Mar'), ('4', 'Apr'),
    ('5', 'May'), ('6', 'Jun'), ('7', 'Jul'), ('8', 'Aug'),
    ('9', 'Sep'), ('10', 'Oct'), ('11', 'Nov'), ('12', 'Dec'),
]


class CreateChoreForm(forms.Form):
    title = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': TAILWIND_INPUT_CLASS, 'placeholder': 'e.g., Vacuum living room'})
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': TAILWIND_TEXTAREA_CLASS, 'rows': 3, 'placeholder': 'Details or reminders'})
    )
    household = forms.ModelChoiceField(
        queryset=Household.objects.none(),
        widget=forms.Select(attrs={'class': TAILWIND_SELECT_CLASS})
    )
    assignment_type = forms.ChoiceField(
        choices=Chore.ASSIGNMENT_TYPE_CHOICES,
        initial='global',
        widget=forms.Select(attrs={'class': TAILWIND_SELECT_CLASS})
    )
    assigned_to = forms.ModelChoiceField(
        queryset=User.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': TAILWIND_SELECT_CLASS})
    )
    rotation_users = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': TAILWIND_SELECT_CLASS})
    )
    base_points = forms.IntegerField(
        min_value=1,
        initial=10,
        widget=forms.NumberInput(attrs={'class': TAILWIND_INPUT_CLASS})
    )
    difficulty = forms.ChoiceField(
        choices=Chore.DIFFICULTY_CHOICES,
        initial='medium',
        widget=forms.Select(attrs={'class': TAILWIND_SELECT_CLASS})
    )
    priority = forms.ChoiceField(
        choices=Chore.PRIORITY_CHOICES,
        initial='medium',
        widget=forms.Select(attrs={'class': TAILWIND_SELECT_CLASS})
    )
    anytime = forms.BooleanField(required=False)
    due_date = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'class': TAILWIND_INPUT_CLASS, 'type': 'datetime-local'})
    )
    requires_verification = forms.BooleanField(required=False)
    verification_photo_required = forms.BooleanField(required=False)

    # Recurrence
    is_recurring = forms.BooleanField(initial=True, required=False)
    frequency = forms.ChoiceField(
        choices=[('daily', 'Daily'), ('weekly', 'Weekly'), ('monthly', 'Monthly')],
        initial='weekly',
        widget=forms.Select(attrs={'class': TAILWIND_SELECT_CLASS})
    )
    days_of_week = forms.MultipleChoiceField(
        choices=DAY_OF_WEEK_CHOICES,
        required=False,
        widget=forms.SelectMultiple(attrs={'class': TAILWIND_SELECT_CLASS})
    )
    day_of_month = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=31,
        widget=forms.NumberInput(attrs={'class': TAILWIND_INPUT_CLASS})
    )
    monthly_mode = forms.ChoiceField(
        choices=[('day', 'On day of month'), ('weekday', 'On weekday pattern')],
        initial='day',
        widget=forms.Select(attrs={'class': TAILWIND_SELECT_CLASS})
    )
    week_of_month = forms.ChoiceField(
        required=False,
        choices=WEEK_OF_MONTH_CHOICES,
        widget=forms.Select(attrs={'class': TAILWIND_SELECT_CLASS})
    )
    weekday_of_month = forms.ChoiceField(
        required=False,
        choices=DAY_OF_WEEK_CHOICES,
        widget=forms.Select(attrs={'class': TAILWIND_SELECT_CLASS})
    )
    interval_value = forms.IntegerField(
        required=False,
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={'class': TAILWIND_INPUT_CLASS})
    )
    months_of_year = forms.MultipleChoiceField(
        choices=MONTH_CHOICES,
        required=False,
        widget=forms.SelectMultiple(attrs={'class': TAILWIND_SELECT_CLASS})
    )

    def __init__(self, *args, user=None, household=None, instance=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            households = Household.objects.filter(memberships__user=user).distinct()
            self.fields['household'].queryset = households
            if household:
                self.fields['household'].initial = household.id

            self.fields['assigned_to'].queryset = User.objects.filter(
                household_memberships__household__in=households
            ).distinct()
            self.fields['assigned_to'].label_from_instance = (
                lambda obj: obj.full_name or obj.email or f"User {obj.id}"
            )
            self.fields['rotation_users'].queryset = self.fields['assigned_to'].queryset
            self.fields['rotation_users'].label_from_instance = (
                lambda obj: obj.full_name or obj.email or f"User {obj.id}"
            )
            if not self.is_bound:
                self.fields['rotation_users'].initial = list(self.fields['rotation_users'].queryset.values_list('id', flat=True))

        if instance and not self.is_bound:
            self.fields['title'].initial = instance.title
            self.fields['description'].initial = instance.description
            self.fields['household'].initial = instance.household_id
            self.fields['assignment_type'].initial = instance.assignment_type
            self.fields['assigned_to'].initial = instance.assigned_to_id
            self.fields['priority'].initial = instance.priority
            self.fields['base_points'].initial = instance.base_points
            self.fields['difficulty'].initial = instance.difficulty
            self.fields['due_date'].initial = instance.due_date
            self.fields['anytime'].initial = instance.due_date is None and (instance.recurrence_pattern == 'none')
            self.fields['requires_verification'].initial = instance.requires_verification
            self.fields['verification_photo_required'].initial = instance.verification_photo_required
            self.fields['rotation_users'].initial = list(
                instance.rotations.values_list('user_id', flat=True)
            )

            # Recurrence initial
            pattern = instance.recurrence_pattern or 'weekly'
            data = instance.recurrence_data or {}
            interval = data.get('interval', 1)
            months = data.get('months_of_year') or []
            self.fields['is_recurring'].initial = pattern != 'none'
            self.fields['frequency'].initial = pattern if pattern in ['daily', 'weekly', 'monthly'] else 'weekly'
            self.fields['interval_value'].initial = interval
            self.fields['days_of_week'].initial = data.get('days_of_week') or []
            self.fields['months_of_year'].initial = months

            if pattern == 'monthly':
                mode = data.get('monthly_mode', 'day')
                self.fields['monthly_mode'].initial = mode
                if mode == 'day':
                    self.fields['day_of_month'].initial = data.get('day_of_month')
                else:
                    self.fields['week_of_month'].initial = data.get('week_of_month')
                    self.fields['weekday_of_month'].initial = data.get('weekday_of_month')

        # Default selections for convenience (only when creating)
        if not self.is_bound and not instance:
            today = timezone.localdate()
            weekday_idx = today.weekday()  # 0=Mon
            weekday_map = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
            self.fields['days_of_week'].initial = [weekday_map[weekday_idx]]
            self.fields['day_of_month'].initial = today.day
            self.fields['anytime'].initial = False

        # Add error styling if needed
        if self.errors:
            for name, field in self.fields.items():
                if name in self.errors:
                    existing = field.widget.attrs.get('class', '')
                    field.widget.attrs['class'] = f"{existing} border-red-400 focus:border-red-400 focus:ring-red-300".strip()

    def clean(self):
        cleaned = super().clean()

        assignment_type = cleaned.get('assignment_type')
        assigned_to = cleaned.get('assigned_to')

        if assignment_type == 'assigned' and not assigned_to:
            self.add_error('assigned_to', 'Select a user for an assigned chore.')

        if cleaned.get('due_date') and cleaned['due_date'] < timezone.now():
            self.add_error('due_date', 'Due date cannot be in the past.')

        if cleaned.get('anytime'):
            cleaned['due_date'] = None
            cleaned['is_recurring'] = False
            cleaned['recurrence_pattern'] = 'none'
            cleaned['recurrence_data'] = {}
            return cleaned

        is_recurring = cleaned.get('is_recurring')
        frequency = cleaned.get('frequency')
        interval = cleaned.get('interval_value') or 1

        if not is_recurring:
            cleaned['recurrence_pattern'] = 'none'
            cleaned['recurrence_data'] = {}
            return cleaned

        if interval and interval < 1:
            self.add_error('interval_value', 'Interval must be at least 1.')

        recurrence_data = {'interval': interval}

        if frequency == 'daily':
            cleaned['recurrence_pattern'] = 'daily'

        elif frequency == 'weekly':
            recurrence_data['days_of_week'] = cleaned.get('days_of_week') or []
            cleaned['recurrence_pattern'] = 'weekly'

        elif frequency == 'monthly':
            mode = cleaned.get('monthly_mode') or 'day'
            recurrence_data['monthly_mode'] = mode
            if mode == 'day':
                day = cleaned.get('day_of_month')
                if not day:
                    self.add_error('day_of_month', 'Pick a day of the month.')
                recurrence_data['day_of_month'] = day
            else:
                wom = cleaned.get('week_of_month')
                wom_day = cleaned.get('weekday_of_month')
                if not wom or not wom_day:
                    self.add_error('week_of_month', 'Pick which week of the month.')
                    self.add_error('weekday_of_month', 'Pick a weekday.')
                recurrence_data['week_of_month'] = wom
                recurrence_data['weekday_of_month'] = wom_day
            cleaned['recurrence_pattern'] = 'monthly'

        else:
            # fallback
            cleaned['recurrence_pattern'] = 'custom'

        recurrence_data['interval_unit'] = frequency

        if cleaned.get('assignment_type') == 'rotating':
            rotation_pool = cleaned.get('rotation_users')
            if not rotation_pool:
                self.add_error('rotation_users', 'Select at least one user for rotation.')
            recurrence_data['rotation_user_ids'] = list(rotation_pool.values_list('id', flat=True)) if rotation_pool else []

        if cleaned.get('months_of_year'):
            recurrence_data['months_of_year'] = cleaned['months_of_year']

        cleaned['recurrence_data'] = recurrence_data
        return cleaned
