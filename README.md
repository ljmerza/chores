# Chore Manager

A Django-based chore management system that gamifies household tasks through points, rewards, and flexible assignment options.

## Features

- **User Management**: Multi-user support with roles (admin, member, child)
- **Household System**: Create and manage multiple households with invite codes
- **Chore Management**:
  - Assigned, global (anyone can claim), and rotating chores
  - One-time and recurring chores
  - Chore templates for easy creation
  - Photo verification support
  - Chore transfer between users
- **Gamification**:
  - Points system with difficulty multipliers
  - Streak tracking and bonuses
  - Leaderboards (daily, weekly, monthly, all-time)
- **Rewards**: Point-based reward redemption system
- **Notifications**: Track chore assignments, transfers, and achievements
- **Accounts**: Email-only accounts (no usernames)

## Technology Stack

- **Backend**: Django 5.2, Django REST Framework
- **Database**: MySQL 8.0 (PostgreSQL and SQLite also supported)
- **Frontend**: Django Templates with Tailwind CSS
- **Deployment**: Docker & Docker Compose
- **API Authentication**: Not implemented yet (endpoints currently unauthenticated; add before production)

## Quick Start with Docker

### Prerequisites

- Docker
- Docker Compose

### Installation

1. **Clone the repository** (or navigate to the project directory):
   ```bash
   cd /media/cubxi/docker/projects/chores
   ```

2. **Build and start the containers** (database is internal-only; access via the `web` service or docker exec):
   ```bash
   docker-compose up --build
   ```

3. **Find the random port** assigned to the web app:
   ```bash
   docker-compose ps
   ```
   Look for the port mapping (e.g., `0.0.0.0:xxxxx->8000/tcp`)

4. **Access the application**:
   - Open your browser to `http://localhost:xxxxx` (replace xxxxx with the random port)
   - You'll be redirected to the setup wizard to create your owner account

5. **Complete the setup wizard**:
   - Create your admin account
   - Set up your first household
   - Start managing chores!

### Stopping the Application

```bash
docker-compose down
```

### Removing All Data (including database)

```bash
docker-compose down -v
```

## Local Development (without Docker)

### Prerequisites

- Python 3.12+
- MySQL 8.0 (or use SQLite for development)

### Setup

1. **Create a virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

4. **Run migrations**:
   ```bash
   python manage.py migrate
   ```

5. **Start the development server**:
   ```bash
   python manage.py runserver
   ```

6. **Access the application**:
   - Open `http://localhost:8000`
   - Complete the setup wizard

## Database Configuration

### MySQL (Docker - Default)

The docker-compose.yml is pre-configured with MySQL (no host port exposed; services communicate on the Docker network). No additional setup needed.

### MySQL (Local Development)

Update your `.env` file:
```env
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=choremanager
MYSQL_USER=your_user
MYSQL_PASSWORD=your_password
```

### SQLite (Local Development)

Remove or leave empty the `MYSQL_HOST` variable in `.env`:
```env
MYSQL_HOST=
```

## Project Structure

```
chores/
├── choremanager/          # Main project settings
├── core/                  # User management (Django user model)
│   ├── models.py         # Custom User model
│   ├── views.py          # Setup wizard, home views
│   └── forms.py          # Setup wizard form
├── households/            # Household & scoring system
│   └── models.py         # Household, Membership, UserScore, PointTransaction, Leaderboard, StreakBonus
├── chores/                # Chore management
│   └── models.py         # Chore, ChoreInstance, ChoreTransfer, ChoreTemplate, Notification
├── rewards/               # Rewards system
│   └── models.py         # Reward, RewardRedemption
├── templates/             # HTML templates
│   ├── base.html         # Base template with Tailwind CSS
│   └── core/
│       ├── setup_wizard.html
│       └── home.html
├── docker-compose.yml     # Docker orchestration
├── Dockerfile            # Docker image definition
├── requirements.txt      # Python dependencies
├── PLANNING.md           # Detailed project planning document
└── README.md             # This file
```

## Database Models

### Core App
- **User**: Extended Django user with role and avatar

### Households App
- **Household**: Household/group entity
- **HouseholdMembership**: User membership in households
- **UserScore**: Points and statistics per user per household
- **PointTransaction**: Audit trail for all point changes
- **Leaderboard**: Denormalized rankings for performance
- **StreakBonus**: Configurable streak bonuses

### Chores App
- **ChoreTemplate**: Reusable chore templates
- **Chore**: Main chore entity
- **ChoreInstance**: Individual occurrences of chores (for recurring)
- **ChoreTransfer**: Chore transfer requests between users
- **Notification**: User notifications

### Rewards App
- **Reward**: Redeemable rewards
- **RewardRedemption**: Reward redemption tracking

## Admin Interface

Access the Django admin at `/admin/` to:
- Manage users, households, and memberships
- Create and assign chores
- Configure rewards
- View point transactions and leaderboards
- Manage notifications

Default superuser is created through the setup wizard.

## Git Housekeeping

If you previously committed files that are now ignored (e.g., `db.sqlite3`, `media/`, `staticfiles/`), remove them from the index before the next commit:
```bash
git rm --cached path/to/file
```

## API (Coming Soon)

REST API endpoints will be available at `/api/` including:
- Authentication (JWT)
- Household management
- Chore CRUD operations
- Point transactions
- Rewards and redemptions
- Leaderboards

## Environment Variables

Key environment variables (see `.env.example`):

```env
# Django
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
MYSQL_HOST=db
MYSQL_PORT=3306
MYSQL_DATABASE=choremanager
MYSQL_USER=choreuser
MYSQL_PASSWORD=chorepass123

# JWT
JWT_ACCESS_TOKEN_LIFETIME=60      # minutes
JWT_REFRESH_TOKEN_LIFETIME=1440   # minutes

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
```

## Docker Services

### Web Service
- **Container**: `chores_web`
- **Port**: Random (mapped from 8000)
- **Depends on**: MySQL database

### Database Service
- **Container**: `chores_mysql`
- **Port**: 3306
- **Image**: MySQL 8.0
- **Volume**: Persistent data storage

## Volumes

- `mysql_data`: MySQL database files
- `static_volume`: Static files (CSS, JS, images)
- `media_volume`: User-uploaded media (avatars, photos)

## Points System

Points are awarded based on chore difficulty:
- **Easy**: 1x multiplier
- **Medium**: 2x multiplier
- **Hard**: 3x multiplier
- **Expert**: 5x multiplier

Additional bonuses for:
- Consecutive day streaks
- Early completion
- Quality verification

## Security Notes

- Change `SECRET_KEY` in production
- Set `DEBUG=False` in production
- Use strong database passwords
- Configure `ALLOWED_HOSTS` properly
- Enable HTTPS in production

## Troubleshooting

### Container won't start
```bash
docker-compose logs web
docker-compose logs db
```

### Database connection issues
- Ensure MySQL container is healthy: `docker-compose ps`
- Check database credentials in docker-compose.yml
- Wait a few seconds after `docker-compose up` for MySQL to initialize

### Port already in use
- Stop the container: `docker-compose down`
- The app uses a random port, so conflicts should be rare
- Check `docker-compose ps` to find the assigned port

### Migrations not applied
```bash
docker-compose exec web python manage.py migrate
```

### Need to reset everything
```bash
docker-compose down -v  # WARNING: Deletes all data
docker-compose up --build
```

## Future Enhancements

See `PLANNING.md` for detailed roadmap including:
- Mobile apps (iOS/Android)
- Advanced gamification (achievements, badges, challenges)
- Smart scheduling and automation
- Weather-based chore activation
- Calendar integration
- Social features (family feed, comments)
- Analytics dashboard
- Multi-language support

## Contributing

This is a personal project, but suggestions and feedback are welcome!

## License

All rights reserved.

## Support

For issues or questions, please create an issue in the repository.

---

**Built with Django 5.2, Tailwind CSS, and MySQL**
