"""
URL configuration for choremanager project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core.views import (
    HomeView,
    LoginView,
    InviteSignupView,
    AdminHubView,
    SetupWizardView,
    SetupWizardMembersView,
    logout_view,
    claim_chore,
    complete_chore,
    redeem_reward
)
from chores.views import CreateChoreView, EditChoreView, ManageChoresView, ManageNotificationsView
from households.views import ManageHouseholdView
from rewards.views import CreateRewardView, EditRewardView, ManageRewardsView
from rewards.views import RedeemRewardsView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', logout_view, name='logout'),
    path('setup/', SetupWizardView.as_view(), name='setup_wizard'),
    path('setup/members/', SetupWizardMembersView.as_view(), name='setup_wizard_members'),
    path('invite/', InviteSignupView.as_view(), name='invite_signup'),
    path('admin-hub/', AdminHubView.as_view(), name='admin_hub'),
    path('households/manage/', ManageHouseholdView.as_view(), name='manage_household'),
    path('chores/manage/', ManageChoresView.as_view(), name='manage_chores'),
    path('notifications/manage/', ManageNotificationsView.as_view(), name='manage_notifications'),
    path('chores/create/', CreateChoreView.as_view(), name='create_chore'),
    path('chores/<int:pk>/edit/', EditChoreView.as_view(), name='edit_chore'),
    path('chores/<int:pk>/claim/', claim_chore, name='claim_chore'),
    path('chores/<int:pk>/complete/', complete_chore, name='complete_chore'),
    path('rewards/<int:pk>/redeem/', redeem_reward, name='redeem_reward'),
    path('rewards/redeem/', RedeemRewardsView.as_view(), name='redeem_rewards'),
    path('rewards/manage/', ManageRewardsView.as_view(), name='manage_rewards'),
    path('rewards/<int:pk>/edit/', EditRewardView.as_view(), name='edit_reward'),
    path('rewards/create/', CreateRewardView.as_view(), name='create_reward'),
    path('', HomeView.as_view(), name='home'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
