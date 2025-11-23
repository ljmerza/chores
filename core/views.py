from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.views.generic import TemplateView
from django.db import transaction
from .models import User
from households.models import Household, HouseholdMembership, UserScore
from .forms import SetupWizardForm


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
                return redirect('home')

        return render(request, self.template_name, {'form': form})


class HomeView(TemplateView):
    template_name = 'core/home.html'

    def dispatch(self, request, *args, **kwargs):
        if not User.objects.exists():
            return redirect('setup_wizard')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            context['households'] = Household.objects.filter(
                memberships__user=self.request.user
            )
        return context
