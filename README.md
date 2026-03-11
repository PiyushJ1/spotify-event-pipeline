# Spotify Event Pipeline

Event-driven pipeline that fetches recently played Spotify tracks, pushes them to SQS (LocalStack), and persists them in PostgreSQL.

## End-to-End User Flow
1. Start local infra: PostgreSQL + LocalStack.
2. Start FastAPI poller service.
3. Open `/login` and complete Spotify OAuth.
4. FastAPI stores tokens in Postgres.
5. Hit `/recent-songs?user_id=<id>`.
6. FastAPI fetches Spotify history and sends messages to SQS.
7. Start consumer worker.
8. Consumer reads SQS messages and writes to `tracks` + `listening_history`.
9. Duplicate play events are skipped via unique constraint on `(track_id, played_at)`.

## Project Structure
```text
spotify-event-pipeline/
├── docker-compose.yml
├── requirements.txt
├── src/
│   ├── common/
│   │   ├── db.py                # SQLAlchemy engine/session setup
│   │   └── models.py            # ORM models + constraints
│   ├── poller/
│   │   ├── main.py              # FastAPI app + Spotify polling endpoint
│   │   └── auth.py              # OAuth/token logic
│   ├── worker/
│   │   └── consumer.py          # SQS consumer -> Postgres writer
│   └── scripts/
│       └── init_db.py           # create_all bootstrap script
└── volume/                      # LocalStack state
```

## Prerequisites
- Python 3.11+
- Docker Desktop
- Spotify app credentials

## Environment Variables
Create `.env` in project root:

```env
SPOTIFY_CLIENT_ID=...
SPOTIFY_CLIENT_SECRET=...
SPOTIFY_CALLBACK_URL=http://127.0.0.1:8000/callback
DATABASE_URL=postgresql://admin:password@localhost:5432/spotify_db
```

## Run Commands
Run all commands from project root.

### 1) Install dependencies
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2) Start Docker services
```bash
docker compose up -d
docker ps
```

### 3) Initialize DB schema
```bash
python3 -m src.scripts.init_db
```

### 4) Start FastAPI server
```bash
fastapi run src/poller/main.py --reload
```
Server: `http://0.0.0.0:8000`

### 5) Complete OAuth and enqueue songs
Use browser:
- `http://127.0.0.1:8000/login`

After auth, callback redirects to `/recent-songs?user_id=<id>` and sends messages to SQS.

### 6) Start consumer
In a second terminal:
```bash
python3 -m src.worker.consumer
```

Expected logs:
- `Saved: ...` for new events
- `Duplicate track, skipped: ...` for already-ingested `(track_id, played_at)`

## Useful Verification Commands

### Check newest ingested rows
```bash
docker exec -it spotify-event-pipeline-postgres-1 psql -U admin -d spotify_db -c \
"SELECT played_at, ingested_at, track_id FROM listening_history ORDER BY ingested_at DESC LIMIT 20;"
```

### Check row counts
```bash
docker exec -it spotify-event-pipeline-postgres-1 psql -U admin -d spotify_db -c \
"SELECT COUNT(*) AS tracks FROM tracks; SELECT COUNT(*) AS history FROM listening_history;"
```

### View latest joined track names
```bash
docker exec -it spotify-event-pipeline-postgres-1 psql -U admin -d spotify_db -c \
"SELECT lh.played_at, t.name FROM listening_history lh JOIN tracks t ON t.id = lh.track_id ORDER BY lh.played_at DESC LIMIT 20;"
```

## Common Gotchas
- If you see `SSL connection has been closed unexpectedly`, your `DATABASE_URL` is likely pointing to Neon/remote DB instead of local Docker Postgres.
- `SELECT * FROM listening_history;` in `psql` may show older rows first. Use `ORDER BY ingested_at DESC` for newest records.
- FastAPI `--reload` can restart on file changes and recreate queue client logs; this is normal in dev.

## Features that still need to be added
- JWT auth or any other way to prevent users from accessing the listening history of other users

