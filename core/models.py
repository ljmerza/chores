from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models


class UserManager(BaseUserManager):
    """Custom manager using username for authentication and optional email."""

    use_in_migrations = True

    def create_user(self, username, email=None, password=None, **extra_fields):
        username = (username or '').strip()
        if not username:
            raise ValueError("Users must have a username.")

        email = self.normalize_email(email) if email else None
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        username = (username or '').strip()
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        if not username:
            raise ValueError("Superuser must have a username.")

        # Superusers should still have an email for admin access
        if not email:
            raise ValueError("Superuser must have an email.")

        return self.create_user(username, email, password, **extra_fields)


class User(AbstractUser):
    """
    Custom user model using username for login with optional email.
    """
    username_validator = UnicodeUsernameValidator()

    username = models.CharField(
        max_length=150,
        unique=True,
        validators=[username_validator],
        error_messages={
            'unique': "A user with that username already exists.",
        },
    )
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

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    objects = UserManager()

    class Meta:
        db_table = 'users'
        ordering = ['-created_at']

    def __str__(self):
        """
        Graceful string representation even when email is missing.
        """
        return self.display_name

    @property
    def full_name(self):
        name = f"{self.first_name} {self.last_name}".strip()
        return name or self.username or self.email

    @property
    def display_name(self):
        return self.full_name or self.username or self.email or f"User {self.id}"
