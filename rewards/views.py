from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import F, Q
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import TemplateView
from households.models import Household, HouseholdMembership, UserScore
from .forms import RewardForm
from .models import Reward


class CreateRewardView(LoginRequiredMixin, TemplateView):
    template_name = 'rewards/create_reward.html'
    login_url = reverse_lazy('login')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('home')

        self.households = Household.objects.filter(memberships__user=request.user).distinct()
        if not self.households.exists():
            return redirect('home')

        self.selected_household = self._selected_household()
        if self.selected_household and not self._is_admin_for(self.selected_household):
            messages.error(request, "You need to be an admin to add rewards for this household.")
            return redirect('home')

        return super().dispatch(request, *args, **kwargs)

    def _selected_household(self):
        requested = self.request.GET.get('household')
        if requested:
            return self.households.filter(id=requested).first() or self.households.first()
        return self.households.first()

    def _is_admin_for(self, household):
        return (
            HouseholdMembership.objects.filter(
                household=household,
                user=self.request.user,
                role='admin'
            ).exists()
            or self.request.user.is_staff
            or self.request.user.role == 'admin'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        selected = getattr(self, 'selected_household', None) or self._selected_household()
        context['form'] = kwargs.get('form') or RewardForm(user=self.request.user, household=selected)
        context['households'] = self.households
        context['selected_household'] = selected
        context['edit_mode'] = False
        return context

    def post(self, request):
        selected = self._selected_household()
        if not self._is_admin_for(selected):
            messages.error(request, "You need to be an admin to add rewards for this household.")
            home_url = reverse('home')
            return redirect(f"{home_url}?household={selected.id}")
        form = RewardForm(request.POST, user=request.user, household=selected)
        if form.is_valid():
            data = form.cleaned_data
            reward = Reward.objects.create(
                household=data['household'],
                title=data['title'],
                description=data.get('description', ''),
                instructions=data.get('instructions', ''),
                point_cost=data['point_cost'],
                category=data['category'],
                quantity_available=data.get('quantity_available'),
                quantity_remaining=data.get('quantity_available'),
                per_user_limit=data.get('per_user_limit'),
                cooldown_days=data.get('cooldown_days'),
                low_stock_threshold=data.get('low_stock_threshold'),
                tags=data.get('tags', ''),
                is_featured=data.get('is_featured', False),
                requires_approval=data.get('requires_approval', True),
                is_active=data.get('is_active', True),
                available_from=data.get('available_from'),
                available_until=data.get('available_until'),
                created_by=request.user,
            )
            allowed_members = data.get('allowed_members')
            if allowed_members:
                reward.allowed_members.set(allowed_members)
            messages.success(request, f'Reward "{reward.title}" created.')
            home_url = reverse('home')
            return redirect(f"{home_url}?household={reward.household.id}")

        return self.render_to_response(self.get_context_data(form=form))


class EditRewardView(LoginRequiredMixin, TemplateView):
    template_name = 'rewards/create_reward.html'
    login_url = reverse_lazy('login')

    def dispatch(self, request, pk, *args, **kwargs):
        self.reward = get_object_or_404(Reward, pk=pk)
        if not request.user.is_authenticated:
            return redirect('home')

        if not self._is_admin_for(self.reward.household):
            messages.error(request, "You need to be an admin to edit rewards for this household.")
            return redirect('home')

        self.households = Household.objects.filter(memberships__user=request.user).distinct()
        self.selected_household = self.reward.household
        return super().dispatch(request, *args, **kwargs)

    def _is_admin_for(self, household):
        return (
            HouseholdMembership.objects.filter(
                household=household,
                user=self.request.user,
                role='admin'
            ).exists()
            or self.request.user.is_staff
            or self.request.user.role == 'admin'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        reward = self.reward
        context['form'] = kwargs.get('form') or RewardForm(
            user=self.request.user,
            household=reward.household,
            instance=reward
        )
        context['households'] = self.households
        context['selected_household'] = reward.household
        context['edit_mode'] = True
        context['reward'] = reward
        return context

    def post(self, request, pk):
        reward = self.reward
        form = RewardForm(
            request.POST,
            user=request.user,
            household=reward.household,
            instance=reward
        )

        if form.is_valid():
            data = form.cleaned_data

            reward.title = data['title']
            reward.description = data.get('description', '')
            reward.instructions = data.get('instructions', '')
            reward.household = data['household']
            reward.point_cost = data['point_cost']
            reward.category = data['category']
            reward.per_user_limit = data.get('per_user_limit')
            reward.cooldown_days = data.get('cooldown_days')
            reward.low_stock_threshold = data.get('low_stock_threshold')
            reward.tags = data.get('tags', '')
            reward.requires_approval = data.get('requires_approval', True)
            reward.is_featured = data.get('is_featured', False)
            reward.is_active = data.get('is_active', True)
            reward.available_from = data.get('available_from')
            reward.available_until = data.get('available_until')

            unlimited = data.get('unlimited_quantity')
            quantity_available = data.get('quantity_available')
            if unlimited:
                reward.quantity_available = None
                reward.quantity_remaining = None
            else:
                reward.quantity_available = quantity_available
                # Keep remaining within bounds; set default if it was unlimited before.
                if reward.quantity_remaining is None:
                    reward.quantity_remaining = quantity_available
                else:
                    reward.quantity_remaining = min(reward.quantity_remaining, quantity_available)

            reward.save()

            allowed_members = data.get('allowed_members')
            if allowed_members:
                reward.allowed_members.set(allowed_members)
            else:
                reward.allowed_members.clear()

            messages.success(request, f'Reward "{reward.title}" updated.')
            home_url = reverse('home')
            return redirect(f"{home_url}?household={reward.household.id}")

        return self.render_to_response(self.get_context_data(form=form))


class ManageRewardsView(LoginRequiredMixin, TemplateView):
    template_name = 'rewards/manage.html'
    login_url = reverse_lazy('login')

    def dispatch(self, request, *args, **kwargs):
        self.households = self._household_queryset()
        if not self.households.exists():
            messages.error(request, "Join or create a household to manage rewards.")
            return redirect('home')

        self.selected_household = self._selected_household()
        if not self.selected_household:
            messages.error(request, "Select a household to manage rewards.")
            return redirect('home')

        if not self._is_admin(request.user, self.selected_household):
            messages.error(request, "You need to be an admin to manage rewards.")
            return redirect('home')

        return super().dispatch(request, *args, **kwargs)

    def _household_queryset(self):
        user = self.request.user
        if user.is_staff or user.role == 'admin':
            return Household.objects.all()
        return Household.objects.filter(memberships__user=user).distinct()

    def _selected_household(self):
        requested = self.request.GET.get('household')
        if requested:
            return self.households.filter(id=requested).first()
        return self.households.first()

    def _is_admin(self, user, household):
        return (
            HouseholdMembership.objects.filter(
                household=household,
                user=user,
                role='admin'
            ).exists()
            or user.is_staff
            or user.role == 'admin'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        selected = self.selected_household
        status_filter = self.request.GET.get('status') or 'all'
        category_filter = self.request.GET.get('category') or 'all'
        availability_filter = self.request.GET.get('availability') or 'all'
        search_query = (self.request.GET.get('q') or '').strip()

        now = timezone.now()
        rewards_qs = Reward.objects.filter(household=selected)

        if status_filter != 'all':
            rewards_qs = rewards_qs.filter(is_active=(status_filter == 'active'))

        if category_filter != 'all':
            rewards_qs = rewards_qs.filter(category=category_filter)

        if availability_filter == 'available':
            rewards_qs = rewards_qs.filter(
                is_active=True,
                ).filter(
                Q(available_from__isnull=True) | Q(available_from__lte=now),
                Q(available_until__isnull=True) | Q(available_until__gte=now),
            ).filter(Q(quantity_remaining__isnull=True) | Q(quantity_remaining__gt=0))
        elif availability_filter == 'low_stock':
            rewards_qs = rewards_qs.filter(
                low_stock_threshold__isnull=False,
                quantity_remaining__isnull=False,
                quantity_remaining__lte=F('low_stock_threshold')
            )

        if search_query:
            rewards_qs = rewards_qs.filter(
                Q(title__icontains=search_query)
                | Q(description__icontains=search_query)
                | Q(instructions__icontains=search_query)
                | Q(tags__icontains=search_query)
            )

        rewards_qs = rewards_qs.order_by('-is_active', 'point_cost', 'title')

        base_qs = Reward.objects.filter(household=selected)
        counts = {
            'total': base_qs.count(),
            'active': base_qs.filter(is_active=True).count(),
            'inactive': base_qs.filter(is_active=False).count(),
            'featured': base_qs.filter(is_featured=True).count(),
            'low_stock': base_qs.filter(
                low_stock_threshold__isnull=False,
                quantity_remaining__isnull=False,
                quantity_remaining__lte=F('low_stock_threshold')
            ).count(),
            'available': base_qs.filter(
                is_active=True,
            ).filter(
                Q(available_from__isnull=True) | Q(available_from__lte=now),
                Q(available_until__isnull=True) | Q(available_until__gte=now),
            ).filter(Q(quantity_remaining__isnull=True) | Q(quantity_remaining__gt=0)).count(),
        }

        context.update({
            'households': self.households,
            'selected_household': selected,
            'rewards': rewards_qs,
            'category_choices': Reward.CATEGORY_CHOICES,
            'status_filter': status_filter,
            'category_filter': category_filter,
            'availability_filter': availability_filter,
            'search_query': search_query,
            'visible_count': rewards_qs.count(),
            'counts': counts,
        })
        return context


class RedeemRewardsView(LoginRequiredMixin, TemplateView):
    template_name = 'rewards/redeem.html'
    login_url = reverse_lazy('login')

    def dispatch(self, request, *args, **kwargs):
        self.households = self._household_queryset()
        if not self.households.exists():
            messages.error(request, "Join or create a household to view rewards.")
            return redirect('home')

        self.selected_household = self._selected_household()
        if not self.selected_household:
            messages.error(request, "Select a household to view rewards.")
            return redirect('home')

        if not self._is_member(request.user, self.selected_household):
            messages.error(request, "You need to be part of this household to redeem rewards.")
            return redirect('home')

        return super().dispatch(request, *args, **kwargs)

    def _household_queryset(self):
        user = self.request.user
        if user.is_staff or user.role == 'admin':
            return Household.objects.all()
        return Household.objects.filter(memberships__user=user).distinct()

    def _selected_household(self):
        requested = self.request.GET.get('household')
        if requested:
            return self.households.filter(id=requested).first()
        return self.households.first()

    def _is_member(self, user, household):
        return (
            HouseholdMembership.objects.filter(household=household, user=user).exists()
            or user.is_staff
            or user.role == 'admin'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        selected = self.selected_household
        status_filter = self.request.GET.get('status') or 'active'
        availability_filter = self.request.GET.get('availability') or 'available'
        category_filter = self.request.GET.get('category') or 'all'
        search_query = (self.request.GET.get('q') or '').strip()

        now = timezone.now()
        rewards_qs = Reward.objects.filter(household=selected).select_related(
            'household', 'created_by'
        ).prefetch_related('allowed_members')

        if status_filter != 'all':
            rewards_qs = rewards_qs.filter(is_active=(status_filter == 'active'))

        if category_filter != 'all':
            rewards_qs = rewards_qs.filter(category=category_filter)

        if availability_filter == 'available':
            rewards_qs = rewards_qs.filter(
                is_active=True,
            ).filter(
                Q(available_from__isnull=True) | Q(available_from__lte=now),
                Q(available_until__isnull=True) | Q(available_until__gte=now),
            ).filter(Q(quantity_remaining__isnull=True) | Q(quantity_remaining__gt=0))
        elif availability_filter == 'low_stock':
            rewards_qs = rewards_qs.filter(
                low_stock_threshold__isnull=False,
                quantity_remaining__isnull=False,
                quantity_remaining__lte=F('low_stock_threshold')
            )

        if search_query:
            rewards_qs = rewards_qs.filter(
                Q(title__icontains=search_query)
                | Q(description__icontains=search_query)
                | Q(instructions__icontains=search_query)
                | Q(tags__icontains=search_query)
            )

        rewards_qs = rewards_qs.order_by('-is_active', 'point_cost', 'title')

        base_qs = Reward.objects.filter(household=selected)
        counts = {
            'total': base_qs.count(),
            'active': base_qs.filter(is_active=True).count(),
            'inactive': base_qs.filter(is_active=False).count(),
            'available': base_qs.filter(
                is_active=True,
            ).filter(
                Q(available_from__isnull=True) | Q(available_from__lte=now),
                Q(available_until__isnull=True) | Q(available_until__gte=now),
            ).filter(Q(quantity_remaining__isnull=True) | Q(quantity_remaining__gt=0)).count(),
            'low_stock': base_qs.filter(
                low_stock_threshold__isnull=False,
                quantity_remaining__isnull=False,
                quantity_remaining__lte=F('low_stock_threshold')
            ).count(),
        }

        user_score = UserScore.objects.filter(
            user=self.request.user,
            household=selected
        ).first()

        context.update({
            'households': self.households,
            'selected_household': selected,
            'rewards': rewards_qs,
            'category_choices': Reward.CATEGORY_CHOICES,
            'status_filter': status_filter,
            'category_filter': category_filter,
            'availability_filter': availability_filter,
            'search_query': search_query,
            'visible_count': rewards_qs.count(),
            'counts': counts,
            'user_score': user_score,
        })
        return context
