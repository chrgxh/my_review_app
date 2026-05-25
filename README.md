# Revlytio — Feedback & Review App

A small FastAPI app that lets a business collect customer feedback by email.

A logged-in business user sends a feedback request to a customer; the customer
opens a one-time link, picks a score, and leaves a comment. Happy customers can
be redirected to a public review page, and the business owner gets a
notification email plus an analytics dashboard of all responses.

**Stack:** FastAPI · SQLModel + SQLite (async) · Jinja2 templates · Resend for
email · cookie-based auth with signed session tokens · NGINX reverse proxy.

## How it works

- **Auth** — business users log in with email/password; sessions are signed
  cookies. Includes forgot-password / reset-password by email.
- **Request feedback** — `POST /request-feedback` emails the customer a unique
  tokenized link.
- **Collect feedback** — `GET /feedback/{token}` shows the form; the customer
  submits via `POST /submit-feedback`.
- **Analytics** — `/analytics` and `/analytics/records` summarize responses.
- **Rate limiting** — per-IP limits on the public/sensitive endpoints (see below).

## Configuration

Create a `.env` file in the repo root (it is gitignored):

```env
RESEND_API_KEY=your_resend_api_key
FROM_EMAIL=you@example.com
BASE_URL=http://127.0.0.1:8000
SECRET_KEY=a_long_random_secret
```

## Running

### Local (development)

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# create the first business + user from scripts/seed_config.yaml
python scripts/seed.py

uvicorn main:app --reload
```

App runs at http://127.0.0.1:8000. The SQLite database is created under `data/`.

### Docker (production)

```bash
docker compose up -d --build
```

This starts the app (uvicorn on port 8000) behind NGINX on ports 80/443.
For TLS certificate setup, see [HTTPS_SETUP.md](HTTPS_SETUP.md).

## Rate limiting

Per-IP limits are enforced with [slowapi](https://github.com/laurentS/slowapi).
The client IP is taken from the `X-Forwarded-For` header set by NGINX (falling
back to the socket address), so the NGINX proxy headers in `nginx.conf` are
required for limits to key on the real visitor.

| Endpoint                  | Limit       |
| ------------------------- | ----------- |
| `POST /login`             | 5 / minute  |
| `POST /forgot-password`   | 3 / hour    |
| `POST /reset-password`    | 5 / minute  |
| `POST /request-feedback`  | 10 / minute |
| `GET  /feedback/{token}`  | 30 / minute |
| `POST /submit-feedback`   | 10 / minute |
| `GET  /analytics/records` | 60 / minute |

Exceeding a limit returns HTTP 429. Storage is in-memory, which counts per
process — fine for a single worker. Running multiple workers/containers later
means switching the limiter to Redis (`storage_uri="redis://..."` in
`helpers/rate_limit.py`).
