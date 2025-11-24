# Django Chore Management App - Planning Document

## Project Overview
A Django-based chore management system that gamifies household tasks through points, rewards, and flexible assignment options.

---

## Shared Template Components
- Location: `templates/components/`
- `button.html`: props `label`, `href` or `type`, `variant` (`primary`, `secondary`, `success`, `danger`, `subtle`, `ghost`), `size` (`sm`, `md`, `lg`), `block` (full width), optional `icon`/`extra_classes`.
- `badge.html`: pill for statuses; `variant` (`primary`, `success`, `danger`, `warning`, `info`, `muted`), `text`.
- `alert.html`: inline notice; `variant` (`success`, `error`, `warning`, `info`), `message`, optional `title`.
- `stat_tile.html`: dashboard metric; `label`, `value`, `helper`, `tone` (`gray`, `primary`, `success`, `danger`).
- `section_header.html`: section title/subtitle with optional `action_label` + `action_href` (uses button component) or custom `action_content`.
- `empty_state.html`: neutral card with `title`, `description`, optional `icon` and CTA (`action_label`, `action_href`, `action_variant`).
- `navbar.html`: shared top nav used on home; shows app name and login/admin link based on `user`.
- `card.html`: generic surface with optional `title/subtitle/header_right`; body via `body`/`content`; accepts extra `classes`/`body_class`.
- `messages.html`: loops Django `messages` and renders them via `alert` component.
- `form_field.html`: label + widget + help + error helper; props `label`, `field`, `errors`, optional `help_text`, `for_id`, `required`, `required_text`, `label_hint`, `wrapper_classes`.

---

## Core Features

### 1. User Management
- User authentication and profiles
- Household/group management
- User roles (admin, member, child)
- User statistics and performance tracking

### 2. Chore Management
- Create, assign, and track chores
- Recurring vs one-time chores
- Global chores (anyone can claim)
- Chore transfer between users
- Chore difficulty levels
- Due dates and reminders

### 3. Points & Ranking System
- Points awarded on chore completion
- Leaderboards (daily, weekly, monthly, all-time)
- Streak bonuses
- Difficulty multipliers
- Point history tracking

### 4. Rewards System
- Create redeemable rewards
- Point-based reward costs
- Reward redemption tracking
- Reward availability (limited quantity, time-based)

### 5. Additional Features
- Notifications (chore reminders, assignments)
- Chore verification (require approval)
- Photo proof of completion
- Chore templates
- Activity feed/history
- Analytics dashboard

---

## Database Schema

### User Model (extends Django's AbstractUser)
```python
User:
    - id (PK)
    - email (unique)
    - password
    - first_name
    - last_name
    - role (admin/member/child)
    - avatar (optional image)
    - created_at
    - updated_at
```

### Household Model
```python
Household:
    - id (PK)
    - name
    - description
    - created_by (FK -> User)
    - invite_code (unique)
    - created_at
    - updated_at
```

### HouseholdMembership Model
```python
HouseholdMembership:
    - id (PK)
    - household (FK -> Household)
    - user (FK -> User)
    - role (admin/member)
    - joined_at

    UNIQUE: (household, user)
```

### Chore Model
```python
Chore:
    - id (PK)
    - household (FK -> Household)
    - title
    - description
    - category (cleaning/cooking/outdoor/shopping/other)
    - difficulty (easy/medium/hard/expert)
    - base_points (integer)
    - status (pending/in_progress/completed/verified/cancelled)
    - assignment_type (assigned/global/rotating)
    - assigned_to (FK -> User, nullable for global chores)
    - created_by (FK -> User)
    - due_date (nullable)
    - recurrence_pattern (none/daily/weekly/monthly/custom)
    - recurrence_data (JSON for complex patterns)
    - requires_verification (boolean)
    - verification_photo_required (boolean)
    - estimated_minutes (integer, nullable)
    - priority (low/medium/high/urgent)
    - created_at
    - updated_at
    - completed_at (nullable)
```

### ChoreInstance Model
```python
ChoreInstance:
    - id (PK)
    - chore (FK -> Chore)
    - assigned_to (FK -> User, nullable)
    - claimed_by (FK -> User, nullable) # For global chores
    - status (available/claimed/in_progress/completed/verified/expired)
    - due_date
    - started_at (nullable)
    - completed_at (nullable)
    - verified_at (nullable)
    - verified_by (FK -> User, nullable)
    - completion_photo (image, nullable)
    - completion_notes (text, nullable)
    - points_awarded (integer, nullable)
    - created_at
```

### ChoreTransfer Model
```python
ChoreTransfer:
    - id (PK)
    - chore_instance (FK -> ChoreInstance)
    - from_user (FK -> User)
    - to_user (FK -> User)
    - status (pending/accepted/rejected)
    - reason (text, optional)
    - requested_at
    - responded_at (nullable)
```

### PointTransaction Model
```python
PointTransaction:
    - id (PK)
    - user (FK -> User)
    - household (FK -> Household)
    - transaction_type (earned/spent/bonus/penalty/transfer)
    - amount (integer, can be negative)
    - balance_after (integer)
    - source_type (chore/reward/streak/manual/transfer)
    - source_id (integer, nullable) # Generic FK
    - description
    - created_at
    - created_by (FK -> User, nullable)
```

### UserScore Model
```python
UserScore:
    - id (PK)
    - user (FK -> User)
    - household (FK -> Household)
    - current_points (integer)
    - lifetime_points (integer)
    - current_streak (integer)
    - longest_streak (integer)
    - total_chores_completed (integer)
    - last_chore_completed_at (nullable)
    - updated_at

    UNIQUE: (user, household)
```

### Leaderboard Model (denormalized for performance)
```python
Leaderboard:
    - id (PK)
    - household (FK -> Household)
    - user (FK -> User)
    - period (daily/weekly/monthly/all_time)
    - period_start_date
    - period_end_date (nullable)
    - points
    - chores_completed
    - rank
    - created_at
    - updated_at

    UNIQUE: (household, user, period, period_start_date)
```

### Reward Model
```python
Reward:
    - id (PK)
    - household (FK -> Household)
    - title
    - description
    - point_cost (integer)
    - category (privilege/item/activity/other)
    - quantity_available (integer, nullable) # null = unlimited
    - quantity_remaining (integer, nullable)
    - icon (optional image)
    - is_active (boolean)
    - available_from (datetime, nullable)
    - available_until (datetime, nullable)
    - max_redemptions_per_user (integer, nullable)
    - created_by (FK -> User)
    - created_at
    - updated_at
```

### RewardRedemption Model
```python
RewardRedemption:
    - id (PK)
    - reward (FK -> Reward)
    - user (FK -> User)
    - household (FK -> Household)
    - points_spent (integer)
    - status (pending/approved/rejected/fulfilled/cancelled)
    - redemption_notes (text, nullable)
    - approved_by (FK -> User, nullable)
    - approved_at (nullable)
    - fulfilled_at (nullable)
    - created_at
```

### ChoreTemplate Model
```python
ChoreTemplate:
    - id (PK)
    - household (FK -> Household, nullable) # null = system template
    - title
    - description
    - category
    - difficulty
    - suggested_points
    - estimated_minutes
    - is_public (boolean)
    - created_by (FK -> User, nullable)
    - created_at
```

### Notification Model
```python
Notification:
    - id (PK)
    - user (FK -> User)
    - household (FK -> Household)
    - notification_type (chore_assigned/chore_due/transfer_request/reward_approved/etc)
    - title
    - message
    - link (nullable)
    - is_read (boolean)
    - created_at
```

### StreakBonus Model
```python
StreakBonus:
    - id (PK)
    - household (FK -> Household)
    - streak_days (integer)
    - bonus_points (integer)
    - bonus_percentage (decimal, nullable)
    - description
    - is_active (boolean)
```

---

## Additional Ideas & Features

### Gamification Enhancements
1. **Achievements/Badges**
   - First chore completed
   - 7-day streak
   - 100 chores completed
   - Master of [category]
   - Early bird (complete before due date)

2. **Challenges**
   - Time-limited group challenges
   - Individual goals
   - Family challenges with collective rewards

3. **Power-ups**
   - Point multipliers
   - Skip-a-chore tokens
   - Extend deadline items

### Advanced Chore Features
1. **Chore Dependencies**
   - Some chores require others to be completed first
   - Sequential chore chains

2. **Collaborative Chores**
   - Multi-person chores
   - Split points between participants

3. **Random Chore Assignment**
   - "Chore Wheel" feature
   - Fair distribution algorithm

4. **Chore Swap Marketplace**
   - Users can offer chores for trade
   - Negotiable point adjustments

### Scheduling & Automation
1. **Smart Scheduling**
   - Auto-assign based on user availability
   - Balance workload across household members

2. **Seasonal Chores**
   - Automatically activate/deactivate by season

3. **Weather-Based Chores**
   - Outdoor chores adjust based on weather API

### Social & Family Features
1. **Family Feed**
   - Activity stream of completions
   - Congratulations and comments
   - Photo sharing of completed chores

2. **Parent Controls**
   - Approve/reject completions
   - Adjust point values
   - Set spending limits on rewards

3. **Allowance Integration**
   - Convert points to real money
   - Track virtual allowance

### Analytics & Insights
1. **Performance Dashboard**
   - Personal productivity stats
   - Time spent on chores
   - Most productive times/days
   - Category breakdown

2. **Household Analytics**
   - Overall completion rates
   - Bottleneck identification
   - Fair distribution reports

3. **Predictive Features**
   - Estimate time to reach reward
   - Predict chore completion likelihood

### Integration Ideas
1. **Calendar Integration**
   - Export chores to Google Calendar
   - Sync due dates

2. **Smart Home Integration**
   - Verify chore completion via IoT devices
   - Reminders via smart speakers

3. **Mobile App**
   - Push notifications
   - Quick chore claiming
   - Photo upload for verification

### Reward Enhancements
1. **Tiered Rewards**
   - Bronze/Silver/Gold levels
   - Unlock higher tiers with achievements

2. **Mystery Rewards**
   - Random reward boxes
   - Surprise bonuses

3. **Group Rewards**
   - Rewards that benefit entire household
   - Require collective point contribution

4. **Wish List**
   - Users can request custom rewards
   - Parents/admins can approve and set prices

---

## Technology Stack

### Backend
- Django 5.x
- Django REST Framework (for API)
- PostgreSQL (production) / SQLite (development)
- Celery (for scheduled tasks, notifications)
- Redis (caching, Celery broker)
- Django Channels (real-time updates, optional)

### Frontend Options
- Django Templates (simple, traditional)
- React/Vue.js + DRF (SPA)
- HTMX (modern, minimal JS)

### Additional Libraries
- Pillow (image handling)
- django-celery-beat (scheduled tasks)
- django-filter (API filtering)
- django-cors-headers (if using SPA)
- django-crispy-forms (form rendering)
- django-storages (cloud media storage)

---

## API Endpoints (REST)

### Authentication (deferred)
- API authentication is not implemented yet; endpoints remain open. Add auth later when requirements are clear.

### Households
- GET /api/households/
- POST /api/households/
- GET /api/households/{id}/
- PUT /api/households/{id}/
- DELETE /api/households/{id}/
- POST /api/households/{id}/join/
- GET /api/households/{id}/members/

### Chores
- GET /api/chores/
- POST /api/chores/
- GET /api/chores/{id}/
- PUT /api/chores/{id}/
- DELETE /api/chores/{id}/
- POST /api/chores/{id}/claim/ (for global chores)
- POST /api/chores/{id}/start/
- POST /api/chores/{id}/complete/
- POST /api/chores/{id}/verify/
- POST /api/chores/{id}/transfer/

### Points & Leaderboard
- GET /api/users/me/score/
- GET /api/leaderboard/{household_id}/
- GET /api/transactions/

### Rewards
- GET /api/rewards/
- POST /api/rewards/
- GET /api/rewards/{id}/
- POST /api/rewards/{id}/redeem/
- GET /api/redemptions/
- POST /api/redemptions/{id}/approve/

### Notifications
- GET /api/notifications/
- PUT /api/notifications/{id}/mark-read/
- PUT /api/notifications/mark-all-read/

---

## Implementation Phases

### Phase 1: MVP (Minimum Viable Product)
- User authentication
- Household creation and management
- Basic chore CRUD
- Chore assignment (manual)
- Simple point system
- Basic leaderboard
- Mark chores complete

### Phase 2: Core Gamification
- Point transactions
- Streak tracking
- Reward system
- Reward redemption
- Global chores
- Chore transfer

### Phase 3: Advanced Features
- Recurring chores
- Chore verification
- Photo uploads
- Notifications
- Chore templates
- Analytics dashboard

### Phase 4: Polish & Enhancement
- Achievements/badges
- Challenges
- Mobile optimization
- Advanced analytics
- Smart scheduling
- API optimization

---

## Security Considerations

1. **Authentication**
   - Secure password hashing (Django default)
   - JWT tokens with expiration
   - CSRF protection

2. **Authorization**
   - Household-level permissions
   - User role enforcement
   - Object-level permissions

3. **Data Validation**
   - Input sanitization
   - Point manipulation prevention
   - Photo upload validation

4. **Rate Limiting**
   - API throttling
   - Prevent point farming

5. **Privacy**
   - Household data isolation
   - User data protection
   - GDPR compliance considerations

---

## Testing Strategy

1. **Unit Tests**
   - Model methods
   - Utility functions
   - Point calculations

2. **Integration Tests**
   - API endpoints
   - User workflows
   - Point transactions

3. **E2E Tests**
   - Critical user journeys
   - Chore lifecycle
   - Reward redemption

---

## Deployment Considerations

1. **Environment Variables**
   - Secret keys
   - Database credentials
   - Email settings
   - Cloud storage keys

2. **Static Files**
   - WhiteNoise or cloud CDN
   - Media file storage (S3, etc.)

3. **Networking**
   - Keep database ports internal-only; services should communicate over the Docker network (no host port exposure).

3. **Background Tasks**
   - Celery workers
   - Scheduled task processing
   - Email sending

4. **Monitoring**
   - Error tracking (Sentry)
   - Performance monitoring
   - Database query optimization

---

## Future Enhancements

- Multi-language support
- Mobile native apps (iOS/Android)
- AI-powered chore suggestions
- Voice assistant integration
- Gamification store (buy power-ups)
- Social features (friend households, comparisons)
- Export data (CSV, PDF reports)
- Email digests (weekly summary)
- Customizable themes
- Accessibility improvements (WCAG compliance)

---

## Questions to Consider

1. Should points be household-specific or global across all households a user belongs to?
2. How should point inflation be handled over time?
3. Should there be a maximum points cap?
4. Can users belong to multiple households?
5. Should there be age restrictions or parental controls?
6. How to handle timezone differences in households?
7. Should completed chores be archived or kept indefinitely?
8. What happens to points when a user leaves a household?
9. Should there be a "bank" for saving points separately from spendable points?
10. How to prevent gaming the system (e.g., fake completions)?

---

## Next Steps

1. Set up Django project structure
2. Configure database settings
3. Create initial models
4. Set up Django admin interface
5. Create basic views and templates
6. Implement authentication
7. Build core chore functionality
8. Add point system
9. Implement rewards
10. Polish UI/UX
