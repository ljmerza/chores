"""
View mixins for household-based permission checking.

These mixins consolidate duplicated household selection and permission
checking logic across multiple views.
"""
from django.contrib import messages
from django.shortcuts import redirect

from households.models import Household, HouseholdMembership


class HouseholdViewMixin:
    """
    Base mixin for views that operate on a selected household.

    Provides common methods for household selection and permission checking.
    Subclasses should set class attributes to configure behavior.

    Attributes:
        admin_only_households: If True, only show households where user is admin
        require_admin: If True, require admin permission to access
        no_household_redirect: URL name to redirect to if no household found
        no_permission_redirect: URL name to redirect to if permission denied
        no_household_message: Message shown when no household found
        no_permission_message: Message shown when permission denied
    """
    admin_only_households = False
    require_admin = True
    no_household_redirect = 'home'
    no_permission_redirect = 'home'
    no_household_message = "Join or create a household first."
    no_permission_message = "You need to be an admin to access this page."

    def dispatch(self, request, *args, **kwargs):
        self.households = self.get_household_queryset()

        if not self.households.exists():
            messages.error(request, self.no_household_message)
            return redirect(self.no_household_redirect)

        self.selected_household = self.get_selected_household()
        if not self.selected_household:
            messages.error(request, "Select a household.")
            return redirect(self.no_household_redirect)

        if self.require_admin and not self.is_admin(request.user, self.selected_household):
            messages.error(request, self.no_permission_message)
            return redirect(self.no_permission_redirect)

        return super().dispatch(request, *args, **kwargs)

    def get_household_queryset(self):
        """
        Get households accessible to the current user.

        Returns all households for staff/global admins, otherwise returns
        households where the user is a member (or admin if admin_only_households=True).
        """
        user = self.request.user
        if user.is_staff or user.role == 'admin':
            return Household.objects.all()

        if self.admin_only_households:
            return Household.objects.filter(
                memberships__user=user,
                memberships__role='admin'
            ).distinct()

        return Household.objects.filter(
            memberships__user=user
        ).distinct()

    def get_selected_household(self):
        """
        Get the selected household from request params or default to first.

        Checks POST 'household_id', then GET 'household' param.
        """
        requested = (
            self.request.POST.get('household_id') or
            self.request.GET.get('household')
        )
        if requested:
            return self.households.filter(id=requested).first()
        return self.households.first()

    def is_admin(self, user, household):
        """Check if user has admin access to household."""
        if user.is_staff or user.role == 'admin':
            return True
        return HouseholdMembership.objects.filter(
            household=household,
            user=user,
            role='admin'
        ).exists()

    def is_member(self, user, household):
        """Check if user is a member of household (any role)."""
        if user.is_staff or user.role == 'admin':
            return True
        return HouseholdMembership.objects.filter(
            household=household,
            user=user
        ).exists()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['households'] = self.households
        context['selected_household'] = self.selected_household
        return context


class HouseholdAdminViewMixin(HouseholdViewMixin):
    """
    Mixin for views that require admin access to the selected household.

    Use this for management views like ManageChoresView, ManageRewardsView, etc.
    """
    admin_only_households = True
    require_admin = True
    no_permission_message = "You need to be an admin to access management tools."


class HouseholdMemberViewMixin(HouseholdViewMixin):
    """
    Mixin for views that only require membership (not admin) access.

    Use this for views like RedeemRewardsView where any member can access.
    """
    admin_only_households = False
    require_admin = False
    no_permission_message = "You need to be a member of this household."

    def dispatch(self, request, *args, **kwargs):
        self.households = self.get_household_queryset()

        if not self.households.exists():
            messages.error(request, self.no_household_message)
            return redirect(self.no_household_redirect)

        self.selected_household = self.get_selected_household()
        if not self.selected_household:
            messages.error(request, "Select a household.")
            return redirect(self.no_household_redirect)

        if not self.is_member(request.user, self.selected_household):
            messages.error(request, self.no_permission_message)
            return redirect(self.no_permission_redirect)

        return super(HouseholdViewMixin, self).dispatch(request, *args, **kwargs)
