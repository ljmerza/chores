from django.db import models
from django.conf import settings
from households.models import Household


class Reward(models.Model):
    """
    Rewards that can be redeemed using points
    """
    CATEGORY_CHOICES = [
        ('privilege', 'Privilege'),
        ('item', 'Item'),
        ('activity', 'Activity'),
        ('other', 'Other'),
    ]

    household = models.ForeignKey(
        Household,
        on_delete=models.CASCADE,
        related_name='rewards'
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    point_cost = models.PositiveIntegerField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    quantity_available = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Leave blank for unlimited quantity"
    )
    quantity_remaining = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Auto-calculated based on quantity_available"
    )
    icon = models.ImageField(upload_to='reward_icons/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    available_from = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Reward becomes available from this date"
    )
    available_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Reward available until this date"
    )
    max_redemptions_per_user = models.IntegerField(
        null=True,
        blank=True,
        help_text="Max times a single user can redeem this reward"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_rewards'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'rewards'
        ordering = ['point_cost', 'title']
        constraints = [
            models.CheckConstraint(
                check=models.Q(quantity_available__isnull=True) | models.Q(quantity_remaining__isnull=True) | models.Q(quantity_remaining__lte=models.F('quantity_available')),
                name='reward_quantity_remaining_lte_available'
            ),
        ]

    def __str__(self):
        return f"{self.title} ({self.point_cost} pts)"

    def save(self, *args, **kwargs):
        if (
            self.pk is None
            and self.quantity_available is not None
            and self.quantity_remaining is None
        ):
            self.quantity_remaining = self.quantity_available
        super().save(*args, **kwargs)

    @property
    def is_available(self):
        """Check if reward is currently available"""
        from django.utils import timezone
        now = timezone.now()

        if not self.is_active:
            return False
        if self.available_from and now < self.available_from:
            return False
        if self.available_until and now > self.available_until:
            return False
        if self.quantity_remaining is not None and self.quantity_remaining <= 0:
            return False

        return True


class RewardRedemption(models.Model):
    """
    Tracks reward redemptions
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('fulfilled', 'Fulfilled'),
        ('cancelled', 'Cancelled'),
    ]

    reward = models.ForeignKey(
        Reward,
        on_delete=models.CASCADE,
        related_name='redemptions'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reward_redemptions'
    )
    household = models.ForeignKey(
        Household,
        on_delete=models.CASCADE,
        related_name='reward_redemptions'
    )
    points_spent = models.PositiveIntegerField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    redemption_notes = models.TextField(blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_redemptions'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    fulfilled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'reward_redemptions'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} - {self.reward.title} ({self.status})"
