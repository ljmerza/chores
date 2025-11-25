from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import F, Q
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse, reverse_lazy
from django.views.generic import TemplateView
from households.models import Household, HouseholdMembership
from core.forms import HomeAssistantSettingsForm, HomeAssistantTargetForm
from .models import Chore, ChoreRotation, Notification
from .forms import CreateChoreForm


class CreateChoreView(LoginRequiredMixin, TemplateView):
    template_name = 'chores/create_chore.html'
    login_url = reverse_lazy('login')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('home')

        self.households = Household.objects.filter(memberships__user=request.user).distinct()
        if not self.households.exists():
            return redirect('home')

        # Only admins/owners or staff can create chores
        membership = HouseholdMembership.objects.filter(
            user=request.user,
            household__in=self.households,
            role='admin'
        ).exists()
        if not (membership or request.user.is_staff or request.user.role == 'admin'):
            return redirect('home')

        return super().dispatch(request, *args, **kwargs)

    def _selected_household(self):
        requested = self.request.GET.get('household')
        if requested:
            return self.households.filter(id=requested).first() or self.households.first()
        return self.households.first()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        selected = self._selected_household()
        context['form'] = CreateChoreForm(
            user=self.request.user,
            household=selected,
        )
        context['households'] = self.households
        context['selected_household'] = selected
        context['edit_mode'] = False
        return context

    def post(self, request):
        selected = self._selected_household()
        form = CreateChoreForm(request.POST, user=request.user, household=selected)

        if form.is_valid():
            data = form.cleaned_data
            chore = Chore.objects.create(
                title=data['title'],
                description=data.get('description', ''),
                household=data['household'],
                category='other',
                difficulty=data['difficulty'],
                base_points=data['base_points'],
                status='pending',
                assignment_type=data['assignment_type'],
                assigned_to=data.get('assigned_to') if data['assignment_type'] == 'assigned' else None,
                created_by=request.user,
                due_date=data.get('due_date'),
                recurrence_pattern=data.get('recurrence_pattern', 'none'),
                recurrence_data=data.get('recurrence_data'),
                requires_verification=data.get('requires_verification', False),
                verification_photo_required=data.get('verification_photo_required', False),
                priority=data.get('priority', 'medium')
            )

            if data['assignment_type'] == 'rotating':
                rotation_users = data.get('rotation_users') or []
                for idx, user in enumerate(rotation_users):
                    chore.rotations.create(user=user, position=idx)

            messages.success(
                request,
                f'Chore "{chore.title}" created.'
            )
            return redirect(f"{redirect('home').url}?household={chore.household.id}")

        return render(request, self.template_name, {
            'form': form,
            'households': self.households,
            'selected_household': selected,
            'edit_mode': False,
        })


class EditChoreView(LoginRequiredMixin, TemplateView):
    template_name = 'chores/create_chore.html'
    login_url = reverse_lazy('login')

    def dispatch(self, request, pk, *args, **kwargs):
        self.chore = get_object_or_404(Chore, pk=pk)
        if not request.user.is_authenticated:
            return redirect('home')

        if not HouseholdMembership.objects.filter(
            household=self.chore.household,
            user=request.user,
            role='admin'
        ).exists() and not (request.user.is_staff or request.user.role == 'admin'):
            return redirect('home')

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = CreateChoreForm(
            user=self.request.user,
            household=self.chore.household,
            instance=self.chore,
        )
        context.update({
            'form': form,
            'households': [self.chore.household],
            'selected_household': self.chore.household,
            'edit_mode': True,
            'chore': self.chore,
        })
        return context

    def post(self, request, pk):
        chore = self.chore
        form = CreateChoreForm(
            request.POST,
            user=request.user,
            household=chore.household,
            instance=chore
        )

        if form.is_valid():
            data = form.cleaned_data
            chore.title = data['title']
            chore.description = data.get('description', '')
            chore.household = data['household']
            chore.difficulty = data['difficulty']
            chore.base_points = data['base_points']
            chore.status = chore.status  # no change
            chore.assignment_type = data['assignment_type']
            chore.assigned_to = data.get('assigned_to') if data['assignment_type'] == 'assigned' else None
            chore.due_date = data.get('due_date')
            chore.recurrence_pattern = data.get('recurrence_pattern', 'none')
            chore.recurrence_data = data.get('recurrence_data')
            chore.requires_verification = data.get('requires_verification', False)
            chore.verification_photo_required = data.get('verification_photo_required', False)
            chore.priority = data.get('priority', 'medium')
            chore.current_rotation_index = 0
            chore.save()

            if data['assignment_type'] == 'rotating':
                rotation_users = data.get('rotation_users') or []
                chore.rotations.all().delete()
                for idx, user in enumerate(rotation_users):
                    chore.rotations.create(user=user, position=idx)
            else:
                chore.rotations.all().delete()

            messages.success(
                request,
                f'Chore "{chore.title}" updated.'
            )
            return redirect(f"{redirect('home').url}?household={chore.household.id}")

        return render(request, self.template_name, {
            'form': form,
            'households': [chore.household],
            'selected_household': chore.household,
            'edit_mode': True,
            'chore': chore,
        })


class ManageChoresView(LoginRequiredMixin, TemplateView):
    template_name = 'chores/manage.html'
    login_url = reverse_lazy('login')

    def dispatch(self, request, *args, **kwargs):
        self.households = self._household_queryset()

        if not self.households.exists():
            messages.error(request, "Join or create a household to manage chores.")
            return redirect('home')

        self.selected_household = self._selected_household()
        if not self.selected_household:
            messages.error(request, "Select a household to manage chores.")
            return redirect('home')

        if not self._is_admin(request.user, self.selected_household):
            messages.error(request, "You need to be an admin to manage chores.")
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
        assignment_filter = self.request.GET.get('assignment') or 'all'
        search_query = (self.request.GET.get('q') or '').strip()

        chores_qs = Chore.objects.filter(household=selected).select_related('assigned_to', 'created_by')

        if status_filter != 'all':
            chores_qs = chores_qs.filter(status=status_filter)

        if assignment_filter != 'all':
            chores_qs = chores_qs.filter(assignment_type=assignment_filter)

        if search_query:
            chores_qs = chores_qs.filter(
                Q(title__icontains=search_query)
                | Q(description__icontains=search_query)
                | Q(assigned_to__first_name__icontains=search_query)
                | Q(assigned_to__last_name__icontains=search_query)
                | Q(assigned_to__email__icontains=search_query)
            )

        chores_qs = chores_qs.order_by(
            'status',
            F('due_date').asc(nulls_last=True),
            '-priority',
            '-created_at'
        )

        base_qs = Chore.objects.filter(household=selected)

        context.update({
            'households': self.households,
            'selected_household': selected,
            'chores': chores_qs,
            'status_filter': status_filter,
            'assignment_filter': assignment_filter,
            'search_query': search_query,
            'counts': {
                'total': base_qs.count(),
                'pending': base_qs.filter(status='pending').count(),
                'in_progress': base_qs.filter(status='in_progress').count(),
                'completed': base_qs.filter(status='completed').count(),
                'verified': base_qs.filter(status='verified').count(),
            },
            'visible_count': chores_qs.count(),
        })
        return context


class ManageNotificationsView(LoginRequiredMixin, TemplateView):
    template_name = 'chores/manage_notifications.html'
    login_url = reverse_lazy('login')

    def dispatch(self, request, *args, **kwargs):
        self.households = self._household_queryset()

        if not self.households.exists():
            messages.error(request, "Join or create a household to manage notifications.")
            return redirect('home')

        self.selected_household = self._selected_household()
        if not self.selected_household:
            messages.error(request, "Select a household to manage notifications.")
            return redirect('home')

        if not self._is_admin(request.user, self.selected_household):
            messages.error(request, "You need to be an admin to manage notifications.")
            return redirect('home')

        self.memberships = HouseholdMembership.objects.filter(
            household=self.selected_household
        ).select_related('user').order_by('user__first_name', 'user__username')

        return super().dispatch(request, *args, **kwargs)

    def _household_queryset(self):
        user = self.request.user
        if user.is_staff or user.role == 'admin':
            return Household.objects.all()
        return Household.objects.filter(
            memberships__user=user,
            memberships__role='admin'
        ).distinct()

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
        notifications_qs = Notification.objects.filter(
            household=self.selected_household
        ).select_related('user')

        ha_form = kwargs.get('ha_form') or self._ha_form()
        ha_settings_form = kwargs.get('ha_settings_form') or self._ha_settings_form()
        ha_rows = []
        for membership in self.memberships:
            field_name = HomeAssistantTargetForm.field_name(membership.user.id)
            ha_rows.append((membership, ha_form[field_name]))

        context.update({
            'households': self.households,
            'selected_household': self.selected_household,
            'notifications': notifications_qs.order_by('-created_at')[:50],
            'counts': {
                'total': notifications_qs.count(),
                'unread': notifications_qs.filter(is_read=False).count(),
            },
            'ha_form': ha_form,
            'ha_settings_form': ha_settings_form,
            'ha_rows': ha_rows,
            'memberships': self.memberships,
        })
        return context

    def post(self, request, *args, **kwargs):
        target_form = self._ha_form()
        settings_form = self._ha_settings_form(post=True)
        if target_form.is_valid() and settings_form.is_valid():
            settings_form.save()
            users_by_id = {m.user.id: m.user for m in self.memberships}
            updates = 0
            for user_id, target in target_form.cleaned_targets().items():
                user = users_by_id.get(user_id)
                if not user:
                    continue
                normalized = target or ""
                current = user.homeassistant_target or ""
                if normalized != current:
                    user.homeassistant_target = normalized or None
                    user.save(update_fields=["homeassistant_target"])
                    updates += 1

            if updates:
                messages.success(request, f"Saved Home Assistant mappings ({updates} updated).")
            else:
                messages.info(request, "No changes to Home Assistant mappings.")
            messages.success(request, "Household Home Assistant settings saved.")

            household_param = f"?household={self.selected_household.id}" if self.selected_household else ""
            return redirect(f"{reverse('manage_notifications')}{household_param}")

        context = self.get_context_data(ha_form=target_form, ha_settings_form=settings_form)
        return self.render_to_response(context)

    def _ha_form(self):
        users = [m.user for m in self.memberships]
        if self.request.method == "POST":
            return HomeAssistantTargetForm(self.request.POST, users=users)
        return HomeAssistantTargetForm(users=users)

    def _ha_settings_form(self, post: bool = False):
        if post or self.request.method == "POST":
            return HomeAssistantSettingsForm(self.request.POST, instance=self.selected_household)
        return HomeAssistantSettingsForm(instance=self.selected_household)
