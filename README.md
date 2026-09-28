# GREAT_CHURCH_AI

A Christian study and prayer assistant for everyday believers. Great Church AI
reads Scripture, helps you study a passage, drafts a prayer, and organises a
sermon outline — grounded in the text, honest about what it is, and free to run.

## What it does

| Area | Page | What you get |
| --- | --- | --- |
| Chat | `/chat.html` | A conversation grounded in the passage you are reading, with a visible AI disclaimer |
| Bible | `/bible.html` | All 66 books, full chapter reader, reference search, full-text search, daily verse |
| Study | `/study.html` | Six study actions on any passage: explain, summarise, themes, reflect, related, outline |
| Prayer | `/prayer.html` | Ten topics anchored to real KJV passages, custom references, share and download |
| Sermons | `/sermons.html` | Blank template, demonstration notes, and a passage-grounded outline generator |
| About | `/about.html` | What the app does, privacy, and the limits of the advice it gives |

## Design principles

**Scripture first.** Every passage in the app is read from a bundled public-domain
King James Version (66 books, 31,102 verses). Nothing is invented, and nothing
requires a network call or an API key to read.

**AI is optional and labelled.** The server prepares a prompt; the browser runs it
through Puter.js. If a server AI provider is configured, the server may also
reply. The app always says which happened, and a fixed template is never
presented as a generated prayer or sermon.

**Honest about limits.** Great Church AI is a software tool. It does not claim to
be God, a pastor, or a prophet, it never fabricates a verse, and it tells you to
contact local emergency services in a crisis.

**Free and private by default.** No paid service is required. The bundled corpus
and the offline prayer and sermon templates work with no configuration at all.

## Quick start

```bash
git clone https://github.com/<owner>/GREAT_CHURCH_AI.git
cd GREAT_CHURCH_AI
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # macOS / Linux

pip install -e apps/api
copy .env.example .env            # Windows
# cp .env.example .env            # macOS / Linux

python -m church_ai_api           # http://127.0.0.1:8000
```

There is no frontend build step. Flask serves the static frontend from
`apps/web` on the same origin, so the app works with a single process.

Run the tests:

```bash
cd apps/api
python -m pytest -q
```

## Configuration

Everything is environment-driven; see `.env.example`. The defaults run the whole
app with no keys. To move AI generation server-side, set both of:

```
AI_PROVIDER_BASE_URL=https://api.openai.com/v1
AI_PROVIDER_API_KEY=...
```

Set `SECRET_KEY` to a real random value and `APP_ENV=production` before any
public deployment. `CORS_ORIGINS` is only needed if you serve the frontend from
a different origin than the API.

## Deploying

The app is a stateless WSGI service, so it needs only a Python runtime and a
static path. The `python -m church_ai_api` entry point is for local
development; production should use gunicorn against the app factory:

```
gunicorn church_ai_api.main:create_app() --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120
```

Use one worker with threads. The KJV corpus is loaded once per worker, so
extra workers each pay that cost for no benefit on a small instance.

Settings that matter in production:

| Variable | Value | Why |
| --- | --- | --- |
| `APP_ENV` | `production` | Disables the dev server and debug |
| `SECRET_KEY` | random 48 bytes | Required; the default is a development value |
| `WEB_DIST` | `./apps/web` | Removes any ambiguity about the static path |
| `PORT` | set by the host | Gunicorn must bind to it |

Set the health check to `/api/health`. On a free instance expect the service to
sleep when idle, so the first request after a quiet period pays the corpus load.

## API

All responses are JSON. Errors carry `{"error": {"code", "message", "fields"}}`.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Liveness and corpus status |
| GET | `/api/bible/books` | Book names and chapter counts |
| GET | `/api/bible/book` | One chapter, verse by verse |
| GET | `/api/bible/reference` | One verse, a range, or a whole chapter |
| GET | `/api/bible/search` | Full-text search |
| GET | `/api/bible/verse-of-the-day` | Deterministic verse of the day |
| POST | `/api/ai/chat` | Ground a message in a passage and return a prompt |
| POST | `/api/ai/study` | Build a study prompt for an action |
| GET | `/api/ai/starters` | Suggested prompts |
| GET | `/api/prayer/topics` | Prayer topics with anchoring passages |
| POST | `/api/prayer` | Prayer prompt plus an offline fallback |
| POST | `/api/ai/prayer-draft` | Draft a prayer around a situation |
| GET | `/api/sermons` | Demonstration sermon notes |
| GET | `/api/sermons/template` | Blank sermon note template |
| POST | `/api/sermons/outline` | Passage-grounded outline prompt |
| POST | `/api/sermons/summarise` | Prompt to tidy operator notes |

See `docs/architecture.md` for the design and `docs/roadmap.md` for what is
planned next.

## Disclaimer

Great Church AI provides Scripture and study tools for personal use. It is not
an ordained ministry, does not provide pastoral or medical advice, and does not
speak for God. Check Scripture, doctrine, and life decisions in person with a
qualified local church.
