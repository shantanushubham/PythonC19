# Running the Ledger App in Docker

## Prerequisites

- Docker Desktop is running
- You are in the project root: `ledger_app/`

---

## Step 1 — Start Postgres and Redis

```bash
docker compose up db redis -d
```

---

## Step 2 — Build the Linux container image

```bash
docker build -t ledger_app .
```

---

## Step 3 — Run the container

```bash
docker run -it \
  --network ledger_app_default \
  -p 8000:8000 \
  ledger_app bash
```

---

## Step 4 — Inside the container

### Set up the virtual environment and install dependencies

```bash
cd /app
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Fix the database connection in .env

```bash
sed -i 's/DB_HOST=localhost/DB_HOST=db/' .env
sed -i 's/DB_PORT=5433/DB_PORT=5432/' .env
sed -i 's|redis://localhost|redis://redis|g' .env
echo "SECURE_SSL_REDIRECT=False" >> .env
```

### Run migrations

```bash
python manage.py migrate
```

### Start the app

**Option A — Uvicorn (ASGI)**
```bash
uvicorn ledger_project.asgi:application --host 0.0.0.0 --port 8000
```

**Option B — Gunicorn (WSGI)**
```bash
gunicorn ledger_project.wsgi:application --bind 0.0.0.0:8000 --workers 3
```

---

## Step 5 — Test in Postman or browser

```
http://localhost:8000/api/auth/login/
```

> Always use `http://` not `https://` — there is no TLS terminator in this setup.

---

## Resuming after a restart

If you stopped the container and want to get back in:

```bash
# Find your container ID
docker ps -a

# Start and re-attach
docker start <container_id>
docker attach <container_id>
```

Or commit the container state as a new image to preserve your changes permanently:

```bash
docker commit <container_id> ledger_app_with_data

docker run -it \
  --network ledger_app_default \
  -p 8000:8000 \
  ledger_app_with_data bash
```
