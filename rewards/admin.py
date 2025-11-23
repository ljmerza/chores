from django.contrib import admin
from .models import Reward, RewardRedemption


@admin.register(Reward)
class RewardAdmin(admin.ModelAdmin):
    list_display = ['title', 'household', 'point_cost', 'category', 'quantity_remaining', 'is_active']
    list_filter = ['category', 'is_active', 'household']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(RewardRedemption)
class RewardRedemptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'reward', 'household', 'points_spent', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['user__username', 'reward__title']
    readonly_fields = ['created_at', 'approved_at', 'fulfilled_at']
