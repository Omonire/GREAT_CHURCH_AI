# Product Roadmap

## Done — MVP

- **Scripture core.** Bundled KJV, 66-book metadata, reference parsing, canonical
  display, chapter reader, verse and range lookup, full-text search, daily verse.
- **Chat.** Scripture-grounded conversation with history, retry, copy, starter
  prompts, and an honest state when no AI engine is available.
- **Study.** Explain, summarise, themes, reflect, related, outline — six actions
  on any passage.
- **Prayer.** Ten topics anchored to real passages, custom references, situation
  drafts, share and download, and labelled offline templates.
- **Sermons.** Blank template, demonstration notes, and a passage-grounded outline
  generator that refuses to guess an unreadable reference.
- **Frontend.** Six pages plus a landing page, warm ivory/navy/gold design
  system, responsive navigation, skip links, and accessible controls.
- **Integrity.** Typed Scripture errors, explicit AI mode and disclaimers, offline
  content never presented as generated, security headers, body limits, and
  XSS-safe rendering.
- **Tests.** 153 tests across Scripture, AI prompting, prayer, sermons, the app
  factory, and health.

## Next — Beta

- Progress feedback for long passages on slow connections.
- Search highlighting that survives copy and print.
- Print-friendly Scripture and sermon layouts.
- Offline service worker for reading Scripture without a connection.
- A second bundled translation alongside the KJV.
- Structured logging with request IDs.

## Later

- Optional account sync so a user's notes and highlights follow them between
  devices, with everything staying local by default.
- Church-provided resource library (own articles, statements, study material)
  scoped to one congregation.
- Small-group discussion generator that stays traceable to a passage.
- Reading-plan scheduling with spaced review.
- Optional transcription of a recorded sermon into Scripture-aware study notes.
- Deployment automation, load testing, and observability dashboards.

## Deliberately out of scope

- Claiming pastoral authority, prophecy, or a divine role.
- Generating Scripture, quotes, or citations that are not in the bundled text.
- Denominational doctrine decided on the user's behalf. The app surfaces passages
  and context; it does not settle questions that belong to a local church.
- Replacing a local congregation, pastor, or counsellor.
