from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import TemplateView
from households.models import Household, HouseholdMembership
from .forms import RewardForm
from .models import Reward


class CreateRewardView(LoginRequiredMixin, TemplateView):
    template_name = 'rewards/create_reward.html'
    login_url = '/admin/login/'

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
