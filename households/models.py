from django.db import models
from django.conf import settings
import secrets
import string


def generate_invite_code():
    """Generate a random 8-character invite code"""
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(8))


class Household(models.Model):
    """
    Represents a household or group that manages chores together
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_households'
    )
    invite_code = models.CharField(
        max_length=8,
        unique=True,
        default=generate_invite_code,
        editable=False
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    ha_base_url = models.URLField(blank=True, default='')
    ha_token = models.CharField(max_length=255, blank=True, default='')
    ha_default_target = models.CharField(max_length=150, blank=True, default='')
    ha_verify_ssl = models.BooleanField(default=True)

    class Meta:
        db_table = 'households'
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """
        Ensure invite codes are unique by regenerating on collision.
        """
        if not self.pk:
            self.invite_code = self._generate_unique_invite_code()
        super().save(*args, **kwargs)

    def regenerate_invite_code(self):
        """Regenerate the invite code for security purposes"""
        self.invite_code = self._generate_unique_invite_code()
        self.save(update_fields=['invite_code'])

    def _generate_unique_invite_code(self, max_attempts=5):
        """
        Generate an invite code and retry on collisions.
        """
        for _ in range(max_attempts):
            code = generate_invite_code()
            if not Household.objects.filter(invite_code=code).exists():
                return code
        raise ValueError("Unable to generate a unique invite code after multiple attempts.")


class HouseholdMembership(models.Model):
    """
    Represents a user's membership in a household
    """
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('member', 'Member'),
    ]

    household = models.ForeignKey(
        Household,
        on_delete=models.CASCADE,
        related_name='memberships'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='household_memberships'
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='member')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'household_memberships'
        unique_together = [['household', 'user']]
        ordering = ['-joined_at']

    def __str__(self):
        return f"{self.user} - {self.household.name} ({self.role})"


class UserScore(models.Model):
    """
    Tracks a user's points and statistics within a household
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='scores'
    )
    household = models.ForeignKey(
        Household,
        on_delete=models.CASCADE,
        related_name='user_scores'
    )
    current_points = models.IntegerField(default=0)
    lifetime_points = models.IntegerField(default=0)
    current_streak = models.IntegerField(default=0)
    longest_streak = models.IntegerField(default=0)
    total_chores_completed = models.IntegerField(default=0)
    last_chore_completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_scores'
        unique_together = [['user', 'household']]
        ordering = ['-current_points']
        constraints = [
            models.CheckConstraint(
                check=models.Q(current_points__gte=0),
                name='user_score_current_points_gte_0'
            ),
            models.CheckConstraint(
                check=models.Q(lifetime_points__gte=0),
                name='user_score_lifetime_points_gte_0'
            ),
            models.CheckConstraint(
                check=models.Q(current_streak__gte=0),
                name='user_score_current_streak_gte_0'
            ),
            models.CheckConstraint(
                check=models.Q(longest_streak__gte=0),
                name='user_score_longest_streak_gte_0'
            ),
            models.CheckConstraint(
                check=models.Q(total_chores_completed__gte=0),
                name='user_score_total_completed_gte_0'
            ),
        ]

    def __str__(self):
        return f"{self.user} - {self.household.name}: {self.current_points} pts"


class PointTransaction(models.Model):
    """
    Records all point transactions for audit trail
    """
    TRANSACTION_TYPE_CHOICES = [
        ('earned', 'Earned'),
        ('spent', 'Spent'),
        ('bonus', 'Bonus'),
        ('penalty', 'Penalty'),
        ('transfer', 'Transfer'),
        ('manual', 'Manual Adjustment'),
    ]

    SOURCE_TYPE_CHOICES = [
        ('chore', 'Chore'),
        ('reward', 'Reward'),
        ('streak', 'Streak Bonus'),
        ('manual', 'Manual'),
        ('transfer', 'Transfer'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='point_transactions'
    )
    household = models.ForeignKey(
        Household,
        on_delete=models.CASCADE,
        related_name='point_transactions'
    )
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPE_CHOICES)
    amount = models.IntegerField()
    balance_after = models.IntegerField()
    source_type = models.CharField(max_length=10, choices=SOURCE_TYPE_CHOICES)
    source_id = models.IntegerField(null=True, blank=True)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_transactions'
    )

    class Meta:
        db_table = 'point_transactions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['household', 'created_at']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(balance_after__gte=0),
                name='point_transaction_balance_after_gte_0',
            ),
        ]

    def __str__(self):
        sign = '+' if self.amount >= 0 else ''
        return f"{self.user}: {sign}{self.amount} pts ({self.transaction_type})"


class Leaderboard(models.Model):
    """
    Denormalized leaderboard for performance
    """
    PERIOD_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('all_time', 'All Time'),
    ]

    household = models.ForeignKey(
        Household,
        on_delete=models.CASCADE,
        related_name='leaderboards'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='leaderboard_entries'
    )
    period = models.CharField(max_length=10, choices=PERIOD_CHOICES)
    period_start_date = models.DateField()
    period_end_date = models.DateField(null=True, blank=True)
    points = models.IntegerField(default=0)
    chores_completed = models.IntegerField(default=0)
    rank = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'leaderboards'
        unique_together = [['household', 'user', 'period', 'period_start_date']]
        ordering = ['household', 'period', 'rank']
        indexes = [
            models.Index(fields=['household', 'period']),
            models.Index(fields=['household', 'period', 'rank']),
        ]
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(points__gte=0)
                    & models.Q(chores_completed__gte=0)
                    & models.Q(rank__gte=0)
                ),
                name='leaderboard_non_negative_fields',
            ),
        ]

    def __str__(self):
        return f"{self.household.name} - {self.period} - Rank {self.rank}: {self.user}"


class StreakBonus(models.Model):
    """
    Defines streak bonuses for households
    """
    household = models.ForeignKey(
        Household,
        on_delete=models.CASCADE,
        related_name='streak_bonuses'
    )
    streak_days = models.IntegerField()
    bonus_points = models.IntegerField(default=0)
    bonus_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Percentage bonus (e.g., 10.00 for 10%)"
    )
    description = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'streak_bonuses'
        ordering = ['household', 'streak_days']
        constraints = [
            models.CheckConstraint(
                check=models.Q(streak_days__gte=1),
                name='streak_bonus_streak_days_gte_1'
            ),
            models.CheckConstraint(
                check=models.Q(bonus_points__gte=0),
                name='streak_bonus_points_gte_0'
            ),
            models.CheckConstraint(
                check=models.Q(bonus_percentage__isnull=True) | models.Q(bonus_percentage__gte=0),
                name='streak_bonus_percentage_gte_0'
            ),
        ]

    def __str__(self):
        return f"{self.household.name}: {self.streak_days} days - {self.description}"
