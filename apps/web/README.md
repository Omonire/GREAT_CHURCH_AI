# Great Church AI Web

Static frontend for the Christian study and prayer assistant. Plain HTML, CSS,
and JavaScript with no framework and no build step — Flask serves these files
directly from the same origin as the API.

## Pages

| File | Controller | Role |
| --- | --- | --- |
| `index.html` | `js/home.js` | Landing page |
| `chat.html` | `js/chat.js` | Scripture-grounded conversation |
| `bible.html` | `js/bible.js` | Reader, reference, search, daily verse |
| `study.html` | `js/study.js` | Six study actions on a passage |
| `prayer.html` | `js/prayer.js` | Topics, custom prayer, share/download |
| `sermons.html` | `js/sermons.js` | Template, demo notes, outline generator |
| `about.html` | — | Purpose, privacy, limits |

## Structure

- `js/core.js` — shared DOM helpers, `api` client, Puter.js bootstrap, nav.
  Every other module imports from here; it is loaded first on every page.
- `css/app.css` — the whole design system: tokens, buttons, cards, forms,
  split layouts, and the responsive breakpoints. No Tailwind, no icon font.

## Conventions

- Read the shared bundle before a page module: `<script type="module"
  src="/js/core.js">` then the page's own module.
- Render all model text with `textContent` / the `el()` helper, never
  `innerHTML`, so Scripture and AI text can never inject markup.
- Get everything from `api.*`; pages hold no direct `fetch` calls.
- Set `data-require-ai` on any control that needs a working AI engine so the
  shared `core.js` gate can disable it honestly when Puter is unavailable.

## Running it

Open `http://127.0.0.1:8000` after starting the API. Opening the HTML files
directly from disk will not work — the pages call same-origin `/api` routes.

Puter.js requires a signed-in Puter account in the browser. Without one, the
reading, search, offline prayer, and demonstration-note features still work and
any AI-only control is disabled with an explanation.
