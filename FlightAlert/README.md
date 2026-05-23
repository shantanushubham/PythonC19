# FlightAlert

Django REST API for flight price alerts.

## Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/)
- Docker (for PostgreSQL and Redis)

## Quick start

### 1. Start database and Redis

```bash
docker compose up -d
```

### 2. Install dependencies

```bash
uv sync
```

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env` if needed. Defaults work for local development.

### 4. Run migrations

```bash
uv run python manage.py migrate
```

### 5. Start the API server

```bash
uv run python manage.py runserver
```

The app runs at [http://127.0.0.1:8000](http://127.0.0.1:8000).

## Verify it works

- Admin: [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)
- Register: `POST /api/users/register/`
- Login: `POST /api/users/login/`

Create an admin user (optional):

```bash
uv run python manage.py createsuperuser
```

## Background jobs (optional)

Price alert checks run via Celery. Start these in separate terminals:

```bash
uv run celery -A flightalert worker -l info
```

```bash
uv run celery -A flightalert beat -l info
```

## Run tests

```bash
uv run pytest
```
