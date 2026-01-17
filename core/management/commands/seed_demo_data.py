from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import User
from core.services.points import adjust_points
from households.models import Household, HouseholdMembership, UserScore
from chores.models import Chore, ChoreInstance, ChoreRotation, ChoreTemplate
from rewards.models import Reward, RewardRedemption


DEMO_HOUSEHOLD_NAME = "Demo Household"


class Command(BaseCommand):
    help = "Seed a rich set of demo data (household, users, chores, rewards) for local/docker development."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Recreate the demo household even if it already exists.",
        )

    def handle(self, *args, **options):
        force = options["force"]
        now = timezone.now()

        existing = Household.objects.filter(name=DEMO_HOUSEHOLD_NAME).first()
        if existing and not force:
            self.stdout.write(
                self.style.WARNING(
                    f'"{DEMO_HOUSEHOLD_NAME}" already exists. Use --force to recreate the demo data.'
                )
            )
            return

        if existing and force:
            self.stdout.write(self.style.WARNING("Removing existing demo household..."))
            existing.delete()

        users = self._create_users()
        household = self._create_household(created_by=users["admin_one"])
        self._create_memberships(household, users)
        self._seed_starting_points(household, users)
        self._create_templates(household, users["admin_one"])
        chores = self._create_chores(household, users, now)
        rewards = self._create_rewards(household, users, now)
        self._create_redemptions(household, users, rewards, now)

        self.stdout.write(
            self.style.SUCCESS(
                f"Demo data created: household '{household.name}', "
                f"{len(users)} users, {len(chores)} chores, {len(rewards)} rewards."
            )
        )
        self.stdout.write(self.style.SUCCESS(f"Household invite code: {household.invite_code}"))
        self.stdout.write(self.style.SUCCESS(f"User password for all demo accounts: {settings.DEMO_USER_PASSWORD}"))
        self._print_user_credentials(users)

    # User and household helpers -------------------------------------------------
    def _create_users(self):
        user_definitions = self._user_definitions()

        users = {}
        for definition in user_definitions:
            defaults = {
                "username": definition["username"],
                "first_name": definition["first_name"],
                "last_name": definition["last_name"],
                "role": definition["role"],
                "is_staff": definition.get("is_staff", False),
                "is_superuser": definition.get("is_superuser", False),
                "email": definition["email"],
            }
            user = User.objects.filter(username=definition["username"]).first()
            if not user and definition["email"]:
                user = User.objects.filter(email=definition["email"]).first()
            if not user:
                user = User.objects.create_user(
                    username=definition["username"],
                    email=definition["email"],
                    password=settings.DEMO_USER_PASSWORD,
                    first_name=definition["first_name"],
                    last_name=definition["last_name"],
                    role=definition["role"],
                    is_staff=definition.get("is_staff", False),
                    is_superuser=definition.get("is_superuser", False),
                )
            else:
                updates = []
                for field, value in defaults.items():
                    if getattr(user, field) != value:
                        setattr(user, field, value)
                        updates.append(field)
                if updates:
                    user.save(update_fields=updates)
                if not user.has_usable_password():
                    user.set_password(settings.DEMO_USER_PASSWORD)
                    user.save(update_fields=["password"])

            users[definition["key"]] = user

        return users

    def _user_definitions(self):
        return [
            {
                "key": "admin_one",
                "username": "alex.admin",
                "email": "alex.admin@example.com",
                "first_name": "Alex",
                "last_name": "Admin",
                "role": "admin",
                "is_staff": True,
                "is_superuser": True,
            },
            {
                "key": "admin_two",
                "username": "casey.captain",
                "email": "casey.captain@example.com",
                "first_name": "Casey",
                "last_name": "Captain",
                "role": "admin",
                "is_staff": True,
                "is_superuser": False,
            },
            {
                "key": "member_one",
                "username": "morgan.member",
                "email": "morgan.member@example.com",
                "first_name": "Morgan",
                "last_name": "Member",
                "role": "member",
            },
            {
                "key": "member_two",
                "username": "taylor.member",
                "email": "taylor.member@example.com",
                "first_name": "Taylor",
                "last_name": "Member",
                "role": "member",
            },
            {
                "key": "child_one",
                "username": "riley.child",
                "email": "riley.child@example.com",
                "first_name": "Riley",
                "last_name": "Child",
                "role": "child",
            },
            {
                "key": "child_two",
                "username": "jamie.child",
                "email": "jamie.child@example.com",
                "first_name": "Jamie",
                "last_name": "Child",
                "role": "child",
            },
        ]

    def _print_user_credentials(self, users):
        self.stdout.write("Demo users (username / email / role):")
        for definition in self._user_definitions():
            user = users[definition["key"]]
            self.stdout.write(f"  - {user.username} / {user.email}  ({user.role})")

    def _create_household(self, created_by):
        household = Household.objects.create(
            name=DEMO_HOUSEHOLD_NAME,
            description="Demo household seeded for local testing.",
            created_by=created_by,
        )
        return household

    def _create_memberships(self, household, users):
        membership_plan = [
            (users["admin_one"], "admin"),
            (users["admin_two"], "admin"),
            (users["member_one"], "member"),
            (users["member_two"], "member"),
            (users["child_one"], "member"),
            (users["child_two"], "member"),
        ]

        for user, role in membership_plan:
            HouseholdMembership.objects.get_or_create(
                household=household,
                user=user,
                defaults={"role": role},
            )
            UserScore.objects.get_or_create(user=user, household=household)

    def _seed_starting_points(self, household, users):
        starting_balances = {
            users["admin_one"]: 260,
            users["admin_two"]: 230,
            users["member_one"]: 200,
            users["member_two"]: 190,
            users["child_one"]: 160,
            users["child_two"]: 150,
        }

        for user, amount in starting_balances.items():
            adjust_points(
                user=user,
                household=household,
                amount=amount,
                transaction_type="bonus",
                source_type="manual",
                description="Starting demo balance",
            )

    # Templates ------------------------------------------------------------------
    def _create_templates(self, household, created_by):
        templates = [
            {
                "title": "Daily Dishes Reset",
                "category": "cleaning",
                "difficulty": "easy",
                "points": 10,
                "is_public": True,
            },
            {
                "title": "Kitchen Deep Clean",
                "category": "cleaning",
                "difficulty": "hard",
                "points": 45,
                "is_public": False,
            },
            {
                "title": "Yard Work Hour",
                "category": "outdoor",
                "difficulty": "medium",
                "points": 30,
                "is_public": True,
            },
            {
                "title": "Grocery Run",
                "category": "shopping",
                "difficulty": "medium",
                "points": 25,
                "is_public": False,
            },
            {
                "title": "Pet Care Shift",
                "category": "pet_care",
                "difficulty": "easy",
                "points": 12,
                "is_public": True,
            },
            {
                "title": "Fix-It Session",
                "category": "maintenance",
                "difficulty": "expert",
                "points": 60,
                "is_public": False,
            },
        ]

        for template in templates:
            ChoreTemplate.objects.create(
                household=household if not template["is_public"] else None,
                title=template["title"],
                description=f"Template: {template['title']}",
                category=template["category"],
                difficulty=template["difficulty"],
                suggested_points=template["points"],
                estimated_minutes=30,
                is_public=template["is_public"],
                created_by=created_by,
            )

    # Chores ---------------------------------------------------------------------
    def _create_chores(self, household, users, now):
        title_pool = [
            "Wipe Kitchen Counters",
            "Load Dishwasher",
            "Empty Dishwasher",
            "Sweep Downstairs Hall",
            "Vacuum Living Room",
            "Mop Kitchen Floor",
            "Clean Microwave",
            "Take Out Trash",
            "Recycle Sorting",
            "Dust Shelves",
            "Clean Windows",
            "Scrub Bathroom Sink",
            "Scrub Shower",
            "Clean Toilet",
            "Replace Towels",
            "Laundry: Wash Darks",
            "Laundry: Wash Whites",
            "Fold Laundry",
            "Put Away Laundry",
            "Make Beds",
            "Change Bed Sheets",
            "Water Houseplants",
            "Rake Leaves",
            "Mow Lawn",
            "Weed Garden",
            "Walk Dog",
            "Feed Pets",
            "Brush Pets",
            "Clean Litter Box",
            "Restock Pantry",
            "Meal Plan",
            "Grocery Pickup",
            "Clean Fridge",
            "Organize Pantry Shelf",
            "Sweep Garage",
            "Clean Car Interior",
            "Wash Car Exterior",
            "Take Out Compost",
            "Declutter Entryway",
            "Vacuum Stairs",
            "Clean Mirrors",
            "Organize Toys",
            "Homework Check",
            "Practice Instrument",
            "Read for 20 Minutes",
            "Prep School Lunches",
            "Pack Backpacks",
            "Sanitize Doorknobs",
            "Refill Soap and TP",
            "Quick Bathroom Refresh",
        ]

        status_cycle = ["pending", "in_progress", "pending", "completed", "verified", "pending", "cancelled"]
        assignment_cycle = ["assigned", "global", "assigned", "rotating", "global", "assigned", "rotating"]
        recurrence_cycle = ["none", "weekly", "daily", "monthly", "none", "biweekly", "custom"]
        priority_cycle = ["medium", "high", "low", "urgent"]
        instance_status_cycle = ["available", "claimed", "in_progress", "completed", "verified", "expired"]
        due_offsets = [-4, -2, -1, 0, 1, 2, 3, 5, 7, 10]

        category_choices = [choice[0] for choice in Chore.CATEGORY_CHOICES]
        difficulty_choices = [choice[0] for choice in Chore.DIFFICULTY_CHOICES]

        assignees = [
            users["admin_one"],
            users["admin_two"],
            users["member_one"],
            users["member_two"],
            users["child_one"],
            users["child_two"],
        ]
        rotation_pool = [
            users["admin_two"],
            users["member_one"],
            users["member_two"],
            users["child_one"],
            users["child_two"],
        ]

        chores = []
        for idx, title in enumerate(title_pool):
            category = category_choices[idx % len(category_choices)]
            difficulty = difficulty_choices[idx % len(difficulty_choices)]
            status = status_cycle[idx % len(status_cycle)]
            assignment_type = assignment_cycle[idx % len(assignment_cycle)]
            recurrence_pattern = recurrence_cycle[idx % len(recurrence_cycle)]
            priority = priority_cycle[idx % len(priority_cycle)]
            due_date = now + timedelta(days=due_offsets[idx % len(due_offsets)], hours=idx % 6)

            assigned_to = None
            if assignment_type == "assigned":
                assigned_to = assignees[idx % len(assignees)]
            elif assignment_type == "rotating":
                assigned_to = rotation_pool[idx % len(rotation_pool)]

            base_points = self._base_points_for_difficulty(difficulty) + (idx % 4) * 2

            chore = Chore.objects.create(
                household=household,
                title=title,
                description=f"{title} for the demo household.",
                category=category,
                difficulty=difficulty,
                base_points=base_points,
                status=status,
                assignment_type=assignment_type,
                assigned_to=assigned_to if assignment_type != "global" else None,
                created_by=users["admin_one"],
                due_date=due_date,
                recurrence_pattern=recurrence_pattern,
                recurrence_data={"days": ["sat", "sun"]} if recurrence_pattern == "custom" else None,
                requires_verification=difficulty in ("hard", "expert"),
                verification_photo_required=difficulty == "expert" or idx % 7 == 0,
                estimated_minutes=15 + (idx % 6) * 5,
                priority=priority,
                current_rotation_index=idx % len(rotation_pool) if assignment_type == "rotating" else 0,
            )

            if assignment_type == "rotating":
                for pos, user in enumerate(rotation_pool):
                    ChoreRotation.objects.create(
                        chore=chore,
                        user=user,
                        position=pos,
                        is_active=True,
                    )

            instance_status = instance_status_cycle[idx % len(instance_status_cycle)]
            instance_due = due_date
            if instance_status == "expired":
                instance_due = due_date - timedelta(days=2)

            claimed_by = None
            assigned_instance_user = assigned_to if assignment_type != "global" else None
            if assignment_type == "global" and instance_status in ("claimed", "in_progress", "completed", "verified"):
                claimed_by = assignees[(idx + 2) % len(assignees)]
            elif assignment_type == "rotating":
                assigned_instance_user = rotation_pool[(idx + chore.current_rotation_index) % len(rotation_pool)]

            started_at = None
            completed_at = None
            verified_at = None
            verified_by = None
            points_awarded = None

            if instance_status in ("claimed", "in_progress", "completed", "verified"):
                started_at = instance_due - timedelta(hours=2)
            if instance_status in ("completed", "verified"):
                completed_at = instance_due - timedelta(hours=1)
                points_awarded = base_points + (idx % 3) * 3
            if instance_status == "verified":
                verified_at = completed_at + timedelta(minutes=40)
                verified_by = users["admin_two"]

            instance = ChoreInstance.objects.create(
                chore=chore,
                assigned_to=assigned_instance_user,
                claimed_by=claimed_by,
                status=instance_status,
                due_date=instance_due,
                started_at=started_at,
                completed_at=completed_at,
                verified_at=verified_at,
                verified_by=verified_by,
                completion_notes="Demo data" if completed_at else "",
                points_awarded=points_awarded,
            )

            if instance_status in ("completed", "verified"):
                awarded_to = claimed_by or assigned_instance_user or users["admin_one"]
                adjust_points(
                    user=awarded_to,
                    household=household,
                    amount=points_awarded,
                    transaction_type="earned",
                    source_type="chore",
                    source_id=instance.id,
                    description=f"Completed '{chore.title}'",
                    increment_completed=True,
                    completed_at=completed_at,
                )

            chores.append(chore)

        return chores

    def _base_points_for_difficulty(self, difficulty):
        return {
            "easy": 10,
            "medium": 20,
            "hard": 35,
            "expert": 55,
        }.get(difficulty, 10)

    # Rewards --------------------------------------------------------------------
    def _create_rewards(self, household, users, now):
        titles = [
            "Extra Screen Time",
            "Choose Dinner",
            "Skip One Chore",
            "Movie Night",
            "Ice Cream Trip",
            "Board Game Pick",
            "Bedtime Extension",
            "Pizza Friday",
            "Choose Family Activity",
            "Stay Up Late",
            "Craft Supply Budget",
            "Bake Cookies",
            "Pick Dessert",
            "Invite Friend Over",
            "Park Trip",
            "Weekend Brunch Pick",
            "Choose Music Playlist",
            "Controller Time",
            "Book Purchase",
            "Toy Shop Coupon",
            "Choose Family Movie",
            "Weekend Sleepover",
            "No Dishes Pass",
            "Outdoor Adventure",
            "Takeout Choice",
            "New App Download",
            "Ride in Front Seat",
            "Karaoke Night",
            "Puzzle Night",
            "Bonus Allowance",
        ]

        categories = [choice[0] for choice in Reward.CATEGORY_CHOICES]
        rewards = []
        for idx, title in enumerate(titles):
            category = categories[idx % len(categories)]
            point_cost = 20 + (idx % 10) * 10 + (idx // 10) * 5
            quantity_available = 5 if idx % 4 == 0 else None
            quantity_remaining = quantity_available

            reward = Reward.objects.create(
                household=household,
                title=title,
                description=f"Demo reward: {title}",
                instructions="Show this to an admin when redeeming.",
                point_cost=point_cost,
                category=category,
                quantity_available=quantity_available,
                quantity_remaining=quantity_remaining,
                per_user_limit=2 if idx % 5 == 0 else None,
                cooldown_days=7 if idx % 6 == 0 else None,
                low_stock_threshold=1 if quantity_available else None,
                tags="demo,fun",
                is_featured=idx % 7 == 0,
                requires_approval=idx % 3 != 0,
                created_by=users["admin_two"],
                is_active=True,
                available_from=now - timedelta(days=5),
                available_until=now + timedelta(days=45) if idx % 6 == 0 else None,
            )
            rewards.append(reward)

        return rewards

    def _create_redemptions(self, household, users, rewards, now):
        redemption_plan = [
            {
                "reward": rewards[0],
                "user": users["child_one"],
                "status": "pending",
                "note": "Can I use this on Friday movie night?",
            },
            {
                "reward": rewards[1],
                "user": users["member_one"],
                "status": "approved",
                "note": "Family dinner choice this weekend.",
            },
            {
                "reward": rewards[2],
                "user": users["member_two"],
                "status": "fulfilled",
                "note": "Used after finishing weekly chores.",
            },
            {
                "reward": rewards[3],
                "user": users["child_two"],
                "status": "denied",
                "note": "Need more points saved up first.",
            },
            {
                "reward": rewards[4],
                "user": users["admin_two"],
                "status": "cancelled",
                "note": "Cancelled after plans changed.",
            },
        ]

        for idx, item in enumerate(redemption_plan):
            reward = item["reward"]
            user = item["user"]
            points_spent = reward.point_cost

            adjust_points(
                user=user,
                household=household,
                amount=-points_spent,
                transaction_type="spent",
                source_type="reward",
                source_id=reward.id,
                description=f"Redeemed '{reward.title}'",
            )

            processed_at = now - timedelta(hours=6 - idx)
            fulfilled_at = processed_at + timedelta(hours=2)

            redemption = RewardRedemption.objects.create(
                reward=reward,
                user=user,
                household=household,
                points_spent=points_spent,
                status=item["status"],
                user_note=item["note"],
                decision_note="Demo redemption",
                processed_by=users["admin_one"] if item["status"] in ("approved", "fulfilled", "denied") else None,
                processed_at=processed_at if item["status"] in ("approved", "fulfilled", "denied") else None,
                fulfilled_by=users["admin_two"] if item["status"] == "fulfilled" else None,
                fulfilled_at=fulfilled_at if item["status"] == "fulfilled" else None,
                refunded_at=None,
            )

            if reward.quantity_remaining is not None and reward.quantity_remaining > 0:
                reward.quantity_remaining = max(reward.quantity_remaining - 1, 0)
                reward.save(update_fields=["quantity_remaining"])

            self.stdout.write(
                f"Created redemption {redemption.id} for {user.full_name} -> {reward.title} ({redemption.status})"
            )
