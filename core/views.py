from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.db import transaction
from django.db.models import Prefetch, Q
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from .models import User
from .mixins import HouseholdAdminViewMixin
from households.models import Household, HouseholdMembership, UserScore
from chores.models import Chore, ChoreTemplate, Notification
from core.services.chores import create_chores_from_templates, get_system_templates_grouped_by_category
from rewards.models import Reward
from rewards.services import request_redemption, RewardError
from .forms import (
    AdditionalAccountFormSet,
    HouseholdSignupForm,
    InviteAccountForm,
    InviteCodeForm,
    LoginForm,
    SetupWizardForm,
    TemplateSelectionForm,
)


INVITE_SESSION_KEY = 'invite_signup_household_id'


class AdminHubView(HouseholdAdminViewMixin, LoginRequiredMixin, TemplateView):
    """
    Admin-only shortcuts hub for managing the selected household.
    """
    template_name = 'core/admin_hub.html'
    login_url = reverse_lazy('login')
    no_household_message = "Join or create a household to manage it."


class SetupWizardView(TemplateView):
    template_name = 'core/setup_wizard.html'

    def dispatch(self, request, *args, **kwargs):
        if User.objects.exists():
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = SetupWizardForm()
        return context

    def post(self, request):
        form = SetupWizardForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user = User.objects.create_user(
                    username=form.cleaned_data['username'],
                    email=form.cleaned_data['email'],
                    password=form.cleaned_data['password'],
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name'],
                    role='admin',
                    is_staff=True,
                    is_superuser=True
                )

                household = Household.objects.create(
                    name=form.cleaned_data['household_name'],
                    description=form.cleaned_data.get('household_description', ''),
                    created_by=user
                )

                HouseholdMembership.objects.create(
                    household=household,
                    user=user,
                    role='admin'
                )

                UserScore.objects.create(
                    user=user,
                    household=household
                )

                login(request, user)
                request.session['setup_household_id'] = household.id
                return redirect('setup_wizard_members')

        return render(request, self.template_name, {'form': form})


class SetupWizardMembersView(LoginRequiredMixin, TemplateView):
    template_name = 'core/setup_wizard_members.html'
    login_url = reverse_lazy('login')

    def dispatch(self, request, *args, **kwargs):
        self.household_id = request.session.get('setup_household_id')
        if not self.household_id:
            return redirect('home')

        self.household = Household.objects.filter(id=self.household_id).first()
        if not self.household:
            request.session.pop('setup_household_id', None)
            return redirect('home')

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['household'] = self.household
        context['formset'] = AdditionalAccountFormSet()
        context['skip_url'] = reverse('setup_wizard_templates')
        return context

    def post(self, request):
        household_id = request.session.get('setup_household_id')
        household = Household.objects.filter(id=household_id).first()
        if not household:
            request.session.pop('setup_household_id', None)
            return redirect('home')

        formset = AdditionalAccountFormSet(request.POST)
        valid = formset.is_valid()
        emails_seen = set()
        usernames_seen = set()

        if valid:
            for form in formset:
                if not form.has_changed() or form.is_blank():
                    continue

                email = form.cleaned_data.get('email')
                username = form.cleaned_data.get('username')
                if email:
                    normalized_email = email.lower()
                    if normalized_email in emails_seen:
                        form.add_error('email', "This email is already listed.")
                        valid = False
                    emails_seen.add(normalized_email)
                if username:
                    normalized_username = username.lower()
                    if normalized_username in usernames_seen:
                        form.add_error('username', "This username is already listed.")
                        valid = False
                    usernames_seen.add(normalized_username)

        if valid:
            with transaction.atomic():
                for form in formset:
                    if not form.has_changed() or form.is_blank():
                        continue

                    data = form.cleaned_data
                    role = data.get('role') or 'member'
                    is_admin = role == 'admin'

                    user = User.objects.create_user(
                        username=data.get('username'),
                        email=data.get('email'),
                        password=data.get('password') or None,
                        first_name=data.get('first_name'),
                        last_name=data.get('last_name'),
                        role=role,
                        is_staff=is_admin,
                        is_superuser=False
                    )

                    HouseholdMembership.objects.create(
                        household=household,
                        user=user,
                        role='admin' if is_admin else 'member'
                    )

                    UserScore.objects.create(
                        user=user,
                        household=household
                    )

            return redirect('setup_wizard_templates')

        return render(request, self.template_name, {
            'formset': formset,
            'household': household
        })


class SetupWizardTemplatesView(LoginRequiredMixin, TemplateView):
    template_name = 'core/setup_wizard_templates.html'
    login_url = reverse_lazy('login')

    def dispatch(self, request, *args, **kwargs):
        self.household_id = request.session.get('setup_household_id')
        if not self.household_id:
            return redirect('home')

        self.household = Household.objects.filter(id=self.household_id).first()
        if not self.household:
            request.session.pop('setup_household_id', None)
            return redirect('home')

        if request.GET.get('skip') == '1':
            request.session.pop('setup_household_id', None)
            return redirect('home')

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        categories = get_system_templates_grouped_by_category()
        context['household'] = self.household
        context['form'] = TemplateSelectionForm(categories=categories)
        context['categories'] = categories
        return context

    def post(self, request):
        household_id = request.session.get('setup_household_id')
        household = Household.objects.filter(id=household_id).first()
        if not household:
            request.session.pop('setup_household_id', None)
            return redirect('home')

        categories = get_system_templates_grouped_by_category()
        form = TemplateSelectionForm(request.POST, categories=categories)
        if form.is_valid():
            selected_templates = form.get_selected_templates()
            if selected_templates:
                create_chores_from_templates(
                    templates=selected_templates,
                    household=household,
                    created_by=request.user,
                    assignment_type='global'
                )
                messages.success(
                    request,
                    f"Added {len(selected_templates)} chores to your household."
                )
            else:
                messages.info(
                    request,
                    "No chores added. You can add chores later from the template catalog."
                )

            request.session.pop('setup_household_id', None)
            return redirect('home')

        return render(request, self.template_name, {
            'form': form,
            'household': household,
            'categories': categories,
        })


class SignupChoiceView(TemplateView):
    template_name = 'core/signup_choice.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)


class HouseholdSignupView(TemplateView):
    template_name = 'core/signup_create_household.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = HouseholdSignupForm()
        return context

    def post(self, request):
        form = HouseholdSignupForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user = User.objects.create_user(
                    username=form.cleaned_data['username'],
                    email=form.cleaned_data['email'],
                    password=form.cleaned_data['password'],
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name'],
                    role='admin',
                    is_staff=False,
                    is_superuser=False
                )

                household = Household.objects.create(
                    name=form.cleaned_data['household_name'],
                    description=form.cleaned_data.get('household_description', ''),
                    created_by=user
                )

                HouseholdMembership.objects.create(
                    household=household,
                    user=user,
                    role='admin'
                )

                UserScore.objects.create(
                    user=user,
                    household=household
                )

                login(request, user)
                request.session['setup_household_id'] = household.id
                return redirect('setup_wizard_templates')

        return render(request, self.template_name, {'form': form})


class InviteCodeView(TemplateView):
    template_name = 'core/invite_code.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = InviteCodeForm()
        return context

    def post(self, request):
        form = InviteCodeForm(request.POST)
        if form.is_valid():
            household = form.household
            request.session[INVITE_SESSION_KEY] = household.id
            messages.info(
                request,
                f"Invite verified for {household.name}. Create your account to join."
            )
            return redirect('invite_signup')

        return render(request, self.template_name, {'form': form})


class HomeView(TemplateView):
    template_name = 'core/home.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.session.get('setup_household_id'):
            return redirect('setup_wizard_members')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        if not user.is_authenticated:
            return context

        households = Household.objects.filter(
            memberships__user=user
        ).prefetch_related(
            Prefetch('memberships', queryset=HouseholdMembership.objects.select_related('user'))
        ).distinct()

        selected_household = None
        requested_household_id = self.request.GET.get('household')

        if requested_household_id:
            selected_household = households.filter(id=requested_household_id).first()

        if not selected_household:
            selected_household = households.first()

        context['households'] = households
        context['selected_household'] = selected_household

        if not selected_household:
            return context

        membership = HouseholdMembership.objects.filter(
            household=selected_household,
            user=user
        ).first()

        is_admin = (
            (membership and membership.role == 'admin')
            or user.role == 'admin'
            or user.is_staff
        )

        user_score = UserScore.objects.filter(
            user=user,
            household=selected_household
        ).first()

        now = timezone.now()
        today = timezone.localdate()

        my_active_chores_qs = Chore.objects.filter(
            household=selected_household,
            assigned_to=user,
            status__in=['pending', 'in_progress']
        ).select_related('assigned_to', 'created_by', 'household').order_by('due_date', 'priority')

        my_active_chores = list(my_active_chores_qs)

        overdue_chores = [
            chore for chore in my_active_chores
            if chore.due_date and chore.due_date < now
        ]
        due_today_chores = [
            chore for chore in my_active_chores
            if chore.due_date and chore.due_date.date() == today
        ]
        upcoming_chores = [
            chore for chore in my_active_chores
            if chore not in overdue_chores and chore not in due_today_chores
        ]

        claimable_qs = Chore.objects.filter(
            household=selected_household,
            assignment_type='global',
            status='pending'
        ).select_related('household', 'created_by')

        claimable_chores = claimable_qs.order_by('due_date', '-priority')[:5]

        leaderboard = list(
            UserScore.objects.filter(household=selected_household)
            .select_related('user')
            .order_by('-current_points', 'user__first_name')[:10]
        )
        leaderboard_top = leaderboard[:5]

        user_rank = None
        if user_score:
            higher_count = UserScore.objects.filter(
                household=selected_household,
                current_points__gt=user_score.current_points
            ).count()
            user_rank = higher_count + 1

        available_rewards = [
            reward for reward in Reward.objects.filter(
                household=selected_household,
                is_active=True
            ).filter(
                Q(allowed_members__isnull=True) | Q(allowed_members=user)
            ).select_related('household', 'created_by').prefetch_related('allowed_members').distinct().order_by('point_cost')
            if reward.is_available
        ]

        affordable_rewards = [
            reward for reward in available_rewards
            if user_score and user_score.current_points >= reward.point_cost
        ]

        notifications = Notification.objects.filter(
            user=user,
            household=selected_household,
            is_read=False
        ).select_related('user', 'household').order_by('-created_at')[:5]

        context.update({
            'current_membership': membership,
            'is_admin': is_admin,
            'user_score': user_score,
            'user_rank': user_rank,
            'household_leaderboard': leaderboard_top,
            'my_active_chores': my_active_chores,
            'overdue_chores': overdue_chores,
            'due_today_chores': due_today_chores,
            'upcoming_chores': upcoming_chores,
            'claimable_chores': claimable_chores,
            'available_rewards': available_rewards[:6],
            'affordable_rewards': affordable_rewards[:6],
            'notifications': notifications,
            'invite_code': selected_household.invite_code,
            'summary_counts': {
                'overdue': len(overdue_chores),
                'due_today': len(due_today_chores),
                'active': len(my_active_chores),
                'claimable': claimable_qs.count(),
            }
        })

        return context


class LoginView(TemplateView):
    template_name = 'core/login.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            next_url = request.GET.get('next')
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)
            return redirect('home')

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = kwargs.get('form') or LoginForm()
        context['next'] = self.request.GET.get('next')
        return context

    def post(self, request):
        form = LoginForm(request.POST)
        next_url = request.POST.get('next') or request.GET.get('next')

        if form.is_valid():
            user = form.get_user()
            login(request, user)

            if not form.cleaned_data.get('remember_me'):
                request.session.set_expiry(0)

            target = next_url if next_url and url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure()
            ) else reverse('home')

            messages.success(request, "Welcome back! You're signed in.")
            return redirect(target)

        context = self.get_context_data(form=form)
        context['next'] = next_url
        return render(request, self.template_name, context)


class InviteSignupView(TemplateView):
    template_name = 'core/invite.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('home')

        self.household = self._get_verified_household(request)
        if not self.household:
            messages.info(request, "Enter an invite code to join a household.")
            return redirect('invite_code')

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = InviteAccountForm()
        context['household'] = self.household
        return context

    def post(self, request):
        household = self._get_verified_household(request)
        if not household:
            messages.info(request, "Enter an invite code to join a household.")
            return redirect('invite_code')

        form = InviteAccountForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user = User.objects.create_user(
                    username=form.cleaned_data['username'],
                    email=form.cleaned_data.get('email'),
                    password=form.cleaned_data['password'],
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data.get('last_name', ''),
                    role='member'
                )

                HouseholdMembership.objects.create(
                    household=household,
                    user=user,
                    role='member'
                )

                UserScore.objects.create(
                    user=user,
                    household=household
                )

                request.session.pop(INVITE_SESSION_KEY, None)

                login(request, user)
                messages.success(request, f"Welcome to {household.name}! You're all set.")
                return redirect('home')

        return render(request, self.template_name, {'form': form})

    def _get_verified_household(self, request):
        household_id = request.session.get(INVITE_SESSION_KEY)
        if not household_id:
            return None
        household = Household.objects.filter(id=household_id).first()
        if not household:
            request.session.pop(INVITE_SESSION_KEY, None)
        return household


def _ensure_membership(user, household):
    return HouseholdMembership.objects.filter(household=household, user=user).exists()


def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('login')


@login_required
def claim_chore(request, pk):
    if request.method != 'POST':
        return redirect('home')

    with transaction.atomic():
        # Lock the row to prevent race conditions when multiple users claim simultaneously
        chore = Chore.objects.select_for_update().filter(
            pk=pk, assignment_type='global', status='pending'
        ).first()

        if not chore:
            messages.error(request, "This chore is no longer available for claiming.")
            return redirect('home')

        if not _ensure_membership(request.user, chore.household):
            return redirect('home')

        chore.assigned_to = request.user
        chore.status = 'in_progress'
        chore.save(update_fields=['assigned_to', 'status'])

        messages.success(request, f"Claimed chore: {chore.title}")

    home_url = reverse('home')
    return redirect(f"{home_url}?household={chore.household.id}")


@login_required
def complete_chore(request, pk):
    if request.method != 'POST':
        return redirect('home')

    from core.services.points import adjust_points

    with transaction.atomic():
        # Lock the chore row to prevent double-completion race conditions
        chore = Chore.objects.select_for_update().filter(pk=pk).first()

        if not chore:
            messages.error(request, "Chore not found.")
            return redirect('home')

        if not _ensure_membership(request.user, chore.household):
            return redirect('home')

        # Check status inside the lock to prevent double-completion
        if chore.status in ['completed', 'verified']:
            messages.info(request, "This chore has already been completed.")
            home_url = reverse('home')
            return redirect(f"{home_url}?household={chore.household.id}")

        allowed = (
            chore.assigned_to_id == request.user.id
            or (chore.assignment_type == 'global' and (chore.assigned_to_id in [None, request.user.id]))
            or request.user.is_staff
        )

        if not allowed:
            messages.error(request, "You are not allowed to complete this chore.")
            home_url = reverse('home')
            return redirect(f"{home_url}?household={chore.household.id}")

        now = timezone.now()
        chore.status = 'completed'
        chore.completed_at = now
        chore.save(update_fields=['status', 'completed_at'])

        # Use the thread-safe points service instead of direct manipulation
        if chore.base_points:
            adjust_points(
                user=request.user,
                household=chore.household,
                amount=chore.base_points,
                transaction_type='earned',
                source_type='chore',
                source_id=chore.id,
                description=f"Completed '{chore.title}'",
                increment_completed=True,
                completed_at=now,
            )

        messages.success(request, f"Completed chore: {chore.title}")

    home_url = reverse('home')
    return redirect(f"{home_url}?household={chore.household.id}")


@login_required
def redeem_reward(request, pk):
    reward = get_object_or_404(Reward, pk=pk)
    if not _ensure_membership(request.user, reward.household):
        return redirect('home')

    if request.method == 'POST':
        try:
            redemption = request_redemption(request.user, reward, reward.household)
            if redemption.status == 'approved':
                messages.success(request, f'Reward "{reward.title}" redeemed.')
            else:
                messages.success(request, f'Reward "{reward.title}" requested. Awaiting approval.')
        except RewardError as exc:
            messages.error(request, str(exc))

    home_url = reverse('home')
    return redirect(f"{home_url}?household={reward.household.id}")


class PrivacyView(TemplateView):
    """
    Static privacy statement page.
    """
    template_name = 'core/privacy.html'


class TermsView(TemplateView):
    """
    Static terms page.
    """
    template_name = 'core/terms.html'


class FAQView(TemplateView):
    """
    Static FAQ page.
    """
    template_name = 'core/faq.html'
