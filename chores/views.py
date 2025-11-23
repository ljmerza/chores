from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.generic import TemplateView
from households.models import Household, HouseholdMembership
from core.models import User
from .models import Chore, ChoreRotation
from .forms import CreateChoreForm


class CreateChoreView(LoginRequiredMixin, TemplateView):
    template_name = 'chores/create_chore.html'
    login_url = '/admin/login/'

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
    login_url = '/admin/login/'

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
