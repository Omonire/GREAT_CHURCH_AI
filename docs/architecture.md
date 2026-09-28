# GREAT_CHURCH_AI Architecture

## Goal

A Christian study and prayer assistant that is grounded in real Scripture,
honest about what it is, and usable with no paid service configured.

The guiding constraint: **the backend never fabricates Scripture and never
presents a fixed template as a generated answer.**

## Shape

A single Python package serves both the API and the static frontend, so there is
one process, one origin, and no build step.

```
Browser  ──GET /api/...──────────►  Flask API  ──►  bible/  (KJV corpus)
   │                                        │
   ├──POST /api/ai/*  (JSON in)             ├──►  ai/     (prompt building)
   │                                        │
   └──script[src=/js/core.js]  ◄── static ──┴──►  apps/web/  (no framework)
```

## Layering

| Package | Responsibility |
| --- | --- |
| `main.py` | App factory, static serving, SPA/API 404 split, security headers |
| `config.py` | Environment-driven settings; no secret ever has a working production default |
| `bible/books.py` | The 66 canonical books, aliases, chapter counts |
| `bible/corpus.py` | Lazy, thread-safe load of the bundled KJV; chapter and search index |
| `bible/reference.py` | Parse loose input (`ps 23`, `please read John 3:16`) into a reference |
| `bible/service.py` | Passage reads, search, daily verse, structured errors |
| `ai/context.py` | Persona, Scripture-integrity rules, safety framing |
| `ai/prompts.py` | Intent/theme detection and prompt construction |
| `ai/provider.py` | Optional OpenAI-compatible server completion |
| `api/*` | Thin HTTP layer: validate, delegate, return JSON |
| `services/*` | Prayer topics and offline assembly, sermon notes and disclaimers |

## Scripture

The corpus is `pythonbible_kjv`, public domain, bundled as a package dependency:
66 books, 31,102 verses, no network call and no rate limit.

Load is lazy and guarded by a lock so the first request pays the cost once.
Chapters are indexed by the verse ids that actually exist rather than by
iterating up to a book's chapter count — `John 3` has 36 verses but only 21
chapters, so a guessed bound would silently drop verses. A test walks all 1,189
chapters and asserts the total equals the corpus verse count.

Failures are typed: `ScriptureError` carries an HTTP status and a code, so a
malformed reference is `400`, a missing passage is `404`, and an unavailable
corpus is `503`. The API layer never leaks a stack trace.

## AI

The backend builds prompts. It does not pretend to be the model.

1. A request arrives with an optional passage.
2. The relevant passage text is read from the local corpus.
3. `ai/prompts.py` assembles a system prompt from the persona plus the
   Scripture-integrity rules plus the passage, and returns messages + context.
4. If `AI_PROVIDER_BASE_URL` and `AI_PROVIDER_API_KEY` are both set, the server
   may also complete the prompt. Otherwise the response is `mode: "browser"`
   and the page runs it through Puter.js.

Every AI response carries a `disclaimer`, and the mode is explicit so the UI
can say which happened. If neither path is available, the page falls back to
offline content that is labelled `offline` with `degraded: true`.

## Error handling

Unknown `/api/...` paths return a JSON 404; unknown static paths return a plain
404. An API client can therefore trust that a 404 from `/api` is a real error
and never a stray HTML page.

## Security

- `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
  `Referrer-Policy: strict-origin-when-cross-origin`, a restrictive
  `Permissions-Policy`, and a CSP that allows only the app's own assets plus
  the Puter and Google Fonts origins. `object-src 'none'`, `frame-ancestors
  'none'`, `form-action 'self'`, and a single `base-uri 'self'`.
- Request bodies are size-capped, and all input is validated with Pydantic.
- AI keys stay server-side and are never sent to the browser.
- `SECRET_KEY` has an insecure development default that must be replaced before
  a public deployment.
- All model text reaches the DOM through `textContent`, so Scripture and AI
  output cannot inject markup.

## Testing

`apps/api/tests` uses the Flask test client with no network access. Coverage is
grouped by concern: `test_bible.py` (parsing, corpus completeness, reference
endpoints), `test_ai.py` (identity framing, intent, prompts, AI endpoints),
`test_prayer.py` (topic fallbacks, offline labelling, anchor warnings),
`test_sermons.py` (demo labelling, outline grounding, refusals), `test_app.py`
(pages, assets, security headers, configuration), and `test_health.py`.
