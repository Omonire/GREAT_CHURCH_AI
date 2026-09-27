# Great Church AI Web

Vanilla HTML/CSS/JavaScript frontend for the realtime church media console.

## UI stack

- HTML5
- Vanilla JavaScript
- Custom CSS for layout/positioning/animation
- Tailwind CSS CDN for utility classes and typography
- Font Awesome CDN for icons
- Google Fonts / Inter

The frontend connects to the Flask-Sock WebSocket endpoint at:

`/ws/sessions/<session_id>`

It intentionally contains no framework runtime. The UI is built to remain lightweight and easy to hand to a church media operator.
