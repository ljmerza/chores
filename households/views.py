from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import TemplateView
from core.models import User
from core.mixins import HouseholdAdminViewMixin
from .forms import HouseholdDetailsForm, InviteMemberForm
from .models import Household, HouseholdMembership, UserScore


class ManageHouseholdView(HouseholdAdminViewMixin, LoginRequiredMixin, TemplateView):
    template_name = 'households/manage.html'
    login_url = reverse_lazy('login')
    no_household_message = "Join or create a household before managing it."
    no_permission_message = "You need to be an admin to manage this household."

    def _redirect_self(self):
        return redirect(f"{reverse('manage_household')}?household={self.selected_household.id}")

    def get_context_data(self, details_form=None, invite_form=None, **kwargs):
        context = super().get_context_data(**kwargs)
        selected = self.selected_household
        memberships = HouseholdMembership.objects.filter(
            household=selected
        ).select_related('user').order_by('-role', 'user__first_name')

        scores = UserScore.objects.filter(household=selected)
        scores_map = {score.user_id: score for score in scores}

        member_rows = [
            {
                'membership': membership,
                'score': scores_map.get(membership.user_id)
            }
            for membership in memberships
        ]

        context.update({
            'households': self.households,
            'selected_household': selected,
            'details_form': details_form or HouseholdDetailsForm(instance=selected),
            'invite_form': invite_form or InviteMemberForm(),
            'member_rows': member_rows,
            'admin_count': memberships.filter(role='admin').count(),
            'member_count': memberships.count(),
            'total_points': sum(score.current_points or 0 for score in scores),
        })
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')

        if action == 'update_details':
            return self._handle_update_details(request)

        if action == 'invite_member':
            return self._handle_invite_member(request)

        if action == 'regenerate_invite':
            return self._handle_regenerate_invite()

        if action == 'change_role':
            return self._handle_change_role(request)

        if action == 'remove_member':
            return self._handle_remove_member(request)

        messages.error(request, "Unknown action.")
        return self._redirect_self()

    def _handle_update_details(self, request):
        form = HouseholdDetailsForm(request.POST, instance=self.selected_household)
        if form.is_valid():
            form.save()
            messages.success(request, "Household details updated.")
            return self._redirect_self()

        return self.render_to_response(self.get_context_data(details_form=form))

    def _handle_invite_member(self, request):
        form = InviteMemberForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            membership_role = 'admin' if data['role'] == 'admin' else 'member'
            with transaction.atomic():
                user = User.objects.create_user(
                    username=data['username'],
                    email=data['email'],
                    password=data.get('password') or None,
                    first_name=data.get('first_name'),
                    last_name=data.get('last_name', ''),
                    role=data.get('role') or 'member',
                )
                HouseholdMembership.objects.create(
                    household=self.selected_household,
                    user=user,
                    role=membership_role
                )
                UserScore.objects.get_or_create(
                    user=user,
                    household=self.selected_household,
                    defaults={'current_points': 0, 'lifetime_points': 0}
                )

            messages.success(request, f"{user.full_name or user.username} added to the household.")
            return self._redirect_self()

        return self.render_to_response(self.get_context_data(invite_form=form))

    def _handle_regenerate_invite(self):
        self.selected_household.regenerate_invite_code()
        messages.success(self.request, "Invite code regenerated.")
        return self._redirect_self()

    def _handle_change_role(self, request):
        membership_id = request.POST.get('membership_id')
        new_role = request.POST.get('role')

        if new_role not in ['admin', 'member']:
            messages.error(request, "Invalid role.")
            return self._redirect_self()

        membership = get_object_or_404(
            HouseholdMembership,
            id=membership_id,
            household=self.selected_household
        )

        if membership.role == new_role:
            messages.info(request, "Role unchanged.")
            return self._redirect_self()

        admin_count = HouseholdMembership.objects.filter(
            household=self.selected_household,
            role='admin'
        ).count()

        if membership.role == 'admin' and new_role != 'admin' and admin_count <= 1:
            messages.error(request, "You must keep at least one admin.")
            return self._redirect_self()

        membership.role = new_role
        membership.save(update_fields=['role'])

        if new_role == 'admin' and membership.user.role != 'admin':
            membership.user.role = 'admin'
            membership.user.save(update_fields=['role'])
        elif new_role == 'member' and membership.user.role == 'admin' and not membership.user.is_staff:
            has_other_admin = HouseholdMembership.objects.filter(
                user=membership.user,
                role='admin'
            ).exclude(id=membership.id).exists()
            if not has_other_admin:
                membership.user.role = 'member'
                membership.user.save(update_fields=['role'])

        messages.success(request, "Role updated.")
        return self._redirect_self()

    def _handle_remove_member(self, request):
        membership_id = request.POST.get('membership_id')
        membership = get_object_or_404(
            HouseholdMembership,
            id=membership_id,
            household=self.selected_household
        )

        admin_count = HouseholdMembership.objects.filter(
            household=self.selected_household,
            role='admin'
        ).count()

        if membership.role == 'admin' and admin_count <= 1:
            messages.error(request, "You must keep at least one admin.")
            return self._redirect_self()

        user = membership.user
        membership.delete()
        UserScore.objects.filter(
            user=user,
            household=self.selected_household
        ).delete()

        if user.role == 'admin' and not user.is_staff:
            has_other_admin = HouseholdMembership.objects.filter(
                user=user,
                role='admin'
            ).exists()
            if not has_other_admin:
                user.role = 'member'
                user.save(update_fields=['role'])

        messages.success(request, "Member removed.")
        return self._redirect_self()
