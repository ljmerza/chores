from django.db import models
from django.conf import settings
from households.models import Household


class ChoreTemplate(models.Model):
    """
    Templates for commonly used chores
    """
    CATEGORY_CHOICES = [
        ('cleaning', 'Cleaning'),
        ('cooking', 'Cooking'),
        ('outdoor', 'Outdoor'),
        ('shopping', 'Shopping'),
        ('pet_care', 'Pet Care'),
        ('maintenance', 'Maintenance'),
        ('other', 'Other'),
    ]

    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
        ('expert', 'Expert'),
    ]

    household = models.ForeignKey(
        Household,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='chore_templates',
        help_text="Null means system-wide template"
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES)
    suggested_points = models.PositiveIntegerField(default=10)
    estimated_minutes = models.PositiveIntegerField(null=True, blank=True)
    is_public = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_templates'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chore_templates'
        ordering = ['category', 'title']

    def __str__(self):
        return f"{self.title} ({self.category})"


class Chore(models.Model):
    """
    Main chore model
    """
    CATEGORY_CHOICES = ChoreTemplate.CATEGORY_CHOICES
    DIFFICULTY_CHOICES = ChoreTemplate.DIFFICULTY_CHOICES

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('verified', 'Verified'),
        ('cancelled', 'Cancelled'),
    ]

    ASSIGNMENT_TYPE_CHOICES = [
        ('assigned', 'Assigned'),
        ('global', 'Global (Anyone)'),
        ('rotating', 'Rotating'),
    ]

    RECURRENCE_CHOICES = [
        ('none', 'None'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('biweekly', 'Bi-weekly'),
        ('monthly', 'Monthly'),
        ('custom', 'Custom'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    household = models.ForeignKey(
        Household,
        on_delete=models.CASCADE,
        related_name='chores'
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES)
    base_points = models.PositiveIntegerField(default=10)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    assignment_type = models.CharField(max_length=10, choices=ASSIGNMENT_TYPE_CHOICES, default='assigned')
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_chores'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_chores'
    )
    due_date = models.DateTimeField(null=True, blank=True)
    recurrence_pattern = models.CharField(
        max_length=10,
        choices=RECURRENCE_CHOICES,
        default='none'
    )
    recurrence_data = models.JSONField(
        null=True,
        blank=True,
        help_text="Additional recurrence configuration"
    )
    requires_verification = models.BooleanField(default=False)
    verification_photo_required = models.BooleanField(default=False)
    estimated_minutes = models.PositiveIntegerField(null=True, blank=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'chores'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['household', 'status', 'priority']),
            models.Index(fields=['household', 'assignment_type']),
        ]

    def __str__(self):
        return f"{self.title} ({self.household.name})"


class ChoreInstance(models.Model):
    """
    Individual instances of chores (especially useful for recurring chores)
    """
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('claimed', 'Claimed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('verified', 'Verified'),
        ('expired', 'Expired'),
    ]

    chore = models.ForeignKey(
        Chore,
        on_delete=models.CASCADE,
        related_name='instances'
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_chore_instances'
    )
    claimed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='claimed_chore_instances',
        help_text="User who claimed a global chore"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    due_date = models.DateTimeField()
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_chore_instances'
    )
    completion_photo = models.ImageField(
        upload_to='chore_completions/',
        null=True,
        blank=True
    )
    completion_notes = models.TextField(blank=True)
    points_awarded = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chore_instances'
        ordering = ['due_date', '-created_at']
        indexes = [
            models.Index(fields=['status', 'due_date']),
            models.Index(fields=['status', 'assigned_to']),
        ]

    def __str__(self):
        return f"{self.chore.title} - {self.due_date.date()} ({self.status})"

    @property
    def assigned_user(self):
        """Get the user assigned to this instance (either assigned or claimed)"""
        return self.claimed_by or self.assigned_to


class ChoreTransfer(models.Model):
    """
    Tracks chore transfer requests between users
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]

    chore_instance = models.ForeignKey(
        ChoreInstance,
        on_delete=models.CASCADE,
        related_name='transfers'
    )
    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_transfers'
    )
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_transfers'
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    reason = models.TextField(blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'chore_transfers'
        ordering = ['-requested_at']

    def __str__(self):
        return f"{self.chore_instance.chore.title}: {self.from_user} -> {self.to_user} ({self.status})"


class Notification(models.Model):
    """
    User notifications
    """
    NOTIFICATION_TYPE_CHOICES = [
        ('chore_assigned', 'Chore Assigned'),
        ('chore_due', 'Chore Due Soon'),
        ('chore_overdue', 'Chore Overdue'),
        ('transfer_request', 'Transfer Request'),
        ('transfer_accepted', 'Transfer Accepted'),
        ('transfer_rejected', 'Transfer Rejected'),
        ('reward_approved', 'Reward Approved'),
        ('reward_rejected', 'Reward Rejected'),
        ('points_awarded', 'Points Awarded'),
        ('streak_milestone', 'Streak Milestone'),
        ('leaderboard_rank', 'Leaderboard Update'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    household = models.ForeignKey(
        Household,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPE_CHOICES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user}: {self.title}"
