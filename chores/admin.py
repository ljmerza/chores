from django.contrib import admin
from .models import (
    ChoreTemplate, Chore, ChoreInstance,
    ChoreTransfer, Notification
)


@admin.register(ChoreTemplate)
class ChoreTemplateAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'difficulty', 'suggested_points', 'household', 'is_public']
    list_filter = ['category', 'difficulty', 'is_public']
    search_fields = ['title', 'description']


@admin.register(Chore)
class ChoreAdmin(admin.ModelAdmin):
    list_display = ['title', 'household', 'category', 'difficulty', 'base_points', 'status', 'assignment_type', 'assigned_to', 'due_date']
    list_filter = ['status', 'category', 'difficulty', 'assignment_type', 'priority']
    search_fields = ['title', 'description', 'household__name']
    readonly_fields = ['created_at', 'updated_at', 'completed_at']


@admin.register(ChoreInstance)
class ChoreInstanceAdmin(admin.ModelAdmin):
    list_display = ['chore', 'assigned_user', 'status', 'due_date', 'points_awarded', 'completed_at']
    list_filter = ['status', 'due_date']
    search_fields = ['chore__title']
    readonly_fields = ['created_at', 'started_at', 'completed_at', 'verified_at']


@admin.register(ChoreTransfer)
class ChoreTransferAdmin(admin.ModelAdmin):
    list_display = ['chore_instance', 'from_user', 'to_user', 'status', 'requested_at']
    list_filter = ['status', 'requested_at']
    search_fields = ['from_user__username', 'to_user__username', 'chore_instance__chore__title']
    readonly_fields = ['requested_at', 'responded_at']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'household', 'notification_type', 'title', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['user__username', 'title', 'message']
    readonly_fields = ['created_at']
