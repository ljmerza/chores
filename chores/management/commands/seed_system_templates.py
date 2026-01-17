from django.core.management.base import BaseCommand
from chores.models import ChoreTemplate


SYSTEM_TEMPLATES = [
    # Cleaning
    {'title': 'Vacuum living room', 'category': 'cleaning', 'difficulty': 'easy', 'suggested_points': 10, 'estimated_minutes': 15},
    {'title': 'Vacuum bedrooms', 'category': 'cleaning', 'difficulty': 'easy', 'suggested_points': 15, 'estimated_minutes': 20},
    {'title': 'Mop floors', 'category': 'cleaning', 'difficulty': 'medium', 'suggested_points': 20, 'estimated_minutes': 30},
    {'title': 'Clean bathroom', 'category': 'cleaning', 'difficulty': 'medium', 'suggested_points': 25, 'estimated_minutes': 25},
    {'title': 'Clean kitchen', 'category': 'cleaning', 'difficulty': 'medium', 'suggested_points': 25, 'estimated_minutes': 30},
    {'title': 'Dust furniture', 'category': 'cleaning', 'difficulty': 'easy', 'suggested_points': 10, 'estimated_minutes': 15},
    {'title': 'Clean windows', 'category': 'cleaning', 'difficulty': 'medium', 'suggested_points': 20, 'estimated_minutes': 30},
    {'title': 'Empty trash cans', 'category': 'cleaning', 'difficulty': 'easy', 'suggested_points': 5, 'estimated_minutes': 5},
    {'title': 'Take out trash', 'category': 'cleaning', 'difficulty': 'easy', 'suggested_points': 5, 'estimated_minutes': 5},
    {'title': 'Clean mirrors', 'category': 'cleaning', 'difficulty': 'easy', 'suggested_points': 10, 'estimated_minutes': 10},
    {'title': 'Wipe down counters', 'category': 'cleaning', 'difficulty': 'easy', 'suggested_points': 5, 'estimated_minutes': 5},
    {'title': 'Deep clean refrigerator', 'category': 'cleaning', 'difficulty': 'hard', 'suggested_points': 40, 'estimated_minutes': 45},
    {'title': 'Organize closet', 'category': 'cleaning', 'difficulty': 'hard', 'suggested_points': 35, 'estimated_minutes': 60},
    {'title': 'Make bed', 'category': 'cleaning', 'difficulty': 'easy', 'suggested_points': 5, 'estimated_minutes': 3},
    {'title': 'Change bed sheets', 'category': 'cleaning', 'difficulty': 'easy', 'suggested_points': 10, 'estimated_minutes': 10},

    # Cooking
    {'title': 'Prepare breakfast', 'category': 'cooking', 'difficulty': 'easy', 'suggested_points': 10, 'estimated_minutes': 15},
    {'title': 'Prepare lunch', 'category': 'cooking', 'difficulty': 'medium', 'suggested_points': 15, 'estimated_minutes': 25},
    {'title': 'Prepare dinner', 'category': 'cooking', 'difficulty': 'medium', 'suggested_points': 25, 'estimated_minutes': 45},
    {'title': 'Wash dishes', 'category': 'cooking', 'difficulty': 'easy', 'suggested_points': 10, 'estimated_minutes': 15},
    {'title': 'Load dishwasher', 'category': 'cooking', 'difficulty': 'easy', 'suggested_points': 5, 'estimated_minutes': 5},
    {'title': 'Unload dishwasher', 'category': 'cooking', 'difficulty': 'easy', 'suggested_points': 5, 'estimated_minutes': 5},
    {'title': 'Meal prep for the week', 'category': 'cooking', 'difficulty': 'hard', 'suggested_points': 50, 'estimated_minutes': 90},
    {'title': 'Set the table', 'category': 'cooking', 'difficulty': 'easy', 'suggested_points': 5, 'estimated_minutes': 5},
    {'title': 'Clear the table', 'category': 'cooking', 'difficulty': 'easy', 'suggested_points': 5, 'estimated_minutes': 5},

    # Outdoor
    {'title': 'Mow the lawn', 'category': 'outdoor', 'difficulty': 'hard', 'suggested_points': 40, 'estimated_minutes': 60},
    {'title': 'Water plants', 'category': 'outdoor', 'difficulty': 'easy', 'suggested_points': 10, 'estimated_minutes': 15},
    {'title': 'Weed garden', 'category': 'outdoor', 'difficulty': 'medium', 'suggested_points': 25, 'estimated_minutes': 45},
    {'title': 'Rake leaves', 'category': 'outdoor', 'difficulty': 'medium', 'suggested_points': 25, 'estimated_minutes': 45},
    {'title': 'Shovel snow', 'category': 'outdoor', 'difficulty': 'hard', 'suggested_points': 40, 'estimated_minutes': 45},
    {'title': 'Sweep patio/deck', 'category': 'outdoor', 'difficulty': 'easy', 'suggested_points': 15, 'estimated_minutes': 20},
    {'title': 'Clean gutters', 'category': 'outdoor', 'difficulty': 'expert', 'suggested_points': 60, 'estimated_minutes': 60},
    {'title': 'Wash car', 'category': 'outdoor', 'difficulty': 'medium', 'suggested_points': 25, 'estimated_minutes': 40},

    # Shopping
    {'title': 'Grocery shopping', 'category': 'shopping', 'difficulty': 'medium', 'suggested_points': 25, 'estimated_minutes': 60},
    {'title': 'Make shopping list', 'category': 'shopping', 'difficulty': 'easy', 'suggested_points': 5, 'estimated_minutes': 10},
    {'title': 'Put away groceries', 'category': 'shopping', 'difficulty': 'easy', 'suggested_points': 10, 'estimated_minutes': 15},
    {'title': 'Return items to store', 'category': 'shopping', 'difficulty': 'medium', 'suggested_points': 15, 'estimated_minutes': 30},

    # Pet Care
    {'title': 'Feed pets', 'category': 'pet_care', 'difficulty': 'easy', 'suggested_points': 5, 'estimated_minutes': 5},
    {'title': 'Walk the dog', 'category': 'pet_care', 'difficulty': 'easy', 'suggested_points': 15, 'estimated_minutes': 20},
    {'title': 'Clean litter box', 'category': 'pet_care', 'difficulty': 'easy', 'suggested_points': 10, 'estimated_minutes': 10},
    {'title': 'Brush pet', 'category': 'pet_care', 'difficulty': 'easy', 'suggested_points': 10, 'estimated_minutes': 15},
    {'title': 'Clean fish tank', 'category': 'pet_care', 'difficulty': 'medium', 'suggested_points': 25, 'estimated_minutes': 30},
    {'title': 'Bathe pet', 'category': 'pet_care', 'difficulty': 'medium', 'suggested_points': 25, 'estimated_minutes': 30},
    {'title': 'Take pet to vet', 'category': 'pet_care', 'difficulty': 'hard', 'suggested_points': 35, 'estimated_minutes': 90},

    # Maintenance
    {'title': 'Do laundry', 'category': 'maintenance', 'difficulty': 'easy', 'suggested_points': 15, 'estimated_minutes': 15},
    {'title': 'Fold laundry', 'category': 'maintenance', 'difficulty': 'easy', 'suggested_points': 10, 'estimated_minutes': 20},
    {'title': 'Iron clothes', 'category': 'maintenance', 'difficulty': 'medium', 'suggested_points': 15, 'estimated_minutes': 20},
    {'title': 'Replace light bulbs', 'category': 'maintenance', 'difficulty': 'easy', 'suggested_points': 5, 'estimated_minutes': 5},
    {'title': 'Check smoke detectors', 'category': 'maintenance', 'difficulty': 'easy', 'suggested_points': 5, 'estimated_minutes': 10},
    {'title': 'Change HVAC filters', 'category': 'maintenance', 'difficulty': 'easy', 'suggested_points': 10, 'estimated_minutes': 10},
    {'title': 'Unclog drain', 'category': 'maintenance', 'difficulty': 'medium', 'suggested_points': 20, 'estimated_minutes': 20},
    {'title': 'Fix squeaky door', 'category': 'maintenance', 'difficulty': 'easy', 'suggested_points': 10, 'estimated_minutes': 10},
    {'title': 'Organize garage', 'category': 'maintenance', 'difficulty': 'expert', 'suggested_points': 60, 'estimated_minutes': 120},
    {'title': 'Sort recycling', 'category': 'maintenance', 'difficulty': 'easy', 'suggested_points': 5, 'estimated_minutes': 10},
]


class Command(BaseCommand):
    help = 'Seed system-wide chore templates'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing system templates before seeding',
        )

    def handle(self, *args, **options):
        if options['clear']:
            deleted_count, _ = ChoreTemplate.objects.filter(
                household__isnull=True, is_public=True
            ).delete()
            self.stdout.write(f"Cleared {deleted_count} existing system templates.")

        created_count = 0
        updated_count = 0

        for template_data in SYSTEM_TEMPLATES:
            obj, created = ChoreTemplate.objects.update_or_create(
                household=None,
                title=template_data['title'],
                category=template_data['category'],
                defaults={
                    'difficulty': template_data['difficulty'],
                    'suggested_points': template_data['suggested_points'],
                    'estimated_minutes': template_data.get('estimated_minutes'),
                    'is_public': True,
                    'description': template_data.get('description', ''),
                }
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {created_count} new templates, updated {updated_count} existing."
            )
        )
