from django.contrib import admin
from .models import (
    Household, HouseholdMembership, UserScore,
    PointTransaction, Leaderboard, StreakBonus
)


@admin.register(Household)
class HouseholdAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_by', 'invite_code', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'invite_code']
    readonly_fields = ['invite_code', 'created_at', 'updated_at']


@admin.register(HouseholdMembership)
class HouseholdMembershipAdmin(admin.ModelAdmin):
    list_display = ['user', 'household', 'role', 'joined_at']
    list_filter = ['role', 'joined_at']
    search_fields = ['user__username', 'household__name']


@admin.register(UserScore)
class UserScoreAdmin(admin.ModelAdmin):
    list_display = ['user', 'household', 'current_points', 'lifetime_points', 'current_streak', 'total_chores_completed']
    list_filter = ['household']
    search_fields = ['user__username', 'household__name']
    readonly_fields = ['updated_at']


@admin.register(PointTransaction)
class PointTransactionAdmin(admin.ModelAdmin):
    list_display = ['user', 'household', 'transaction_type', 'amount', 'balance_after', 'created_at']
    list_filter = ['transaction_type', 'source_type', 'created_at']
    search_fields = ['user__username', 'household__name', 'description']
    readonly_fields = ['created_at']


@admin.register(Leaderboard)
class LeaderboardAdmin(admin.ModelAdmin):
    list_display = ['household', 'user', 'period', 'rank', 'points', 'chores_completed']
    list_filter = ['period', 'household']
    search_fields = ['user__username', 'household__name']


@admin.register(StreakBonus)
class StreakBonusAdmin(admin.ModelAdmin):
    list_display = ['household', 'streak_days', 'bonus_points', 'bonus_percentage', 'is_active']
    list_filter = ['is_active', 'household']
    search_fields = ['household__name', 'description']
