from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    """Custom manager using email as the username field (optional)."""

    def create_user(self, email=None, password=None, **extra_fields):
        email = self.normalize_email(email) if email else None
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        # Superusers should still have an email for admin access
        if not email:
            raise ValueError("Superuser must have an email.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Custom user model using email instead of username.
    """
    username = None
    email = models.EmailField(unique=True, null=True, blank=True)

    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('member', 'Member'),
        ('child', 'Child'),
    ]

    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='member')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        db_table = 'users'
        ordering = ['-created_at']

    def __str__(self):
        """
        Graceful string representation even when email is missing.
        """
        return self.full_name or f"User {self.id}"

    @property
    def full_name(self):
        name = f"{self.first_name} {self.last_name}".strip()
        return name or self.email or f"User {self.id}"
