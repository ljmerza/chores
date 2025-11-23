from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user model extending Django's AbstractUser
    """
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('member', 'Member'),
        ('child', 'Child'),
    ]

    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='member')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users'
        ordering = ['-created_at']

    def __str__(self):
        return self.username

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username
