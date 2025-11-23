from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'is_staff', 'created_at']
    list_filter = ['role', 'is_staff', 'is_superuser', 'is_active']
    search_fields = ['username', 'email', 'first_name', 'last_name']

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Custom Fields', {'fields': ('role', 'avatar')}),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Custom Fields', {'fields': ('role', 'avatar')}),
    )
