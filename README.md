# Real-time Chat App

A real-time chat application built with **Python**, **Django**, and
**Django Channels**. It supports one-to-one chats, group rooms, typing
indicators, online presence, and file sharing — messages travel instantly
over WebSockets, and everything is stored in the database.

## Features

- **User accounts** — signup, login, logout (Django auth)
- **One-to-one chat** — start a private conversation by username
- **Group chat rooms** — create rooms with any members
- **Instant messaging** — WebSockets via Django Channels, no page refresh
- **Typing indicator** — see "user is typing..." live
- **Online/offline presence** — join/leave announcements in each room
- **Message history** — last 50 messages load when you open a room
- **File/image sharing** — upload a file, it is broadcast to the room
- **Token-secured WebSockets** — each browser gets a personal token

## Tech Stack

| Layer        | Technology                              |
|--------------|-----------------------------------------|
| Web          | Django 5, Django templates, vanilla JS  |
| Real-time    | Django Channels, WebSockets             |
| ASGI server  | Daphne (serves HTTP + WebSocket)        |
| Database     | PostgreSQL (prod), SQLite (dev/tests)   |
| Message bus  | Redis channel layer (prod), in-memory (dev/tests) |
| Tests        | pytest, pytest-django, pytest-asyncio    |
| Deploy       | Docker, Docker Compose                  |

## Project Structure

```
chat-app/
├── manage.py
├── pytest.ini
├── config/
│   ├── settings.py        # env-based settings (DB, Redis, secret key)
│   ├── settings_test.py   # isolated test settings (SQLite, in-memory layer)
│   ├── asgi.py            # ProtocolTypeRouter: HTTP + WebSocket
│   ├── urls.py
│   └── wsgi.py
├── chat/
│   ├── models.py          # ChatRoom, Message, Token
│   ├── consumers.py       # ChatConsumer: WebSocket connect/receive/disconnect
│   ├── middleware.py      # TokenAuthMiddleware (?token=... -> user)
│   ├── routing.py         # ws/chat/<room_id>/ route
│   ├── views.py           # signup, rooms, chat page, file upload
│   ├── forms.py
│   ├── admin.py
│   └── templates/chat/    # base, signup, login, room_list, chat (JS client)
├── tests/                 # auth, rooms, and live WebSocket tests
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Quick Start (Docker)

```bash
cp .env.example .env
docker compose up --build
```

Open http://localhost:8000, sign up two accounts (use two browsers or an
incognito window), and chat between them live.

## Quick Start (local)

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver        # serves WebSockets too (daphne in INSTALLED_APPS)
# or, like production:
daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

For Postgres + Redis locally, set in `.env`:

```
DB_ENGINE=postgres
POSTGRES_DB=chatapp
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
REDIS_URL=redis://localhost:6379/0
```

## How to Use

1. Sign up at `/signup/` (a WebSocket token is created for you).
2. On `/rooms/`, start a one-to-one chat by username or create a group room.
3. Open a room: the last 50 messages load, then new messages arrive instantly.
4. Type to see the typing indicator; share files with the upload button.

The browser opens `ws://host/ws/chat/<room_id>/?token=<key>`. The token
middleware turns the key into a user; only room members are allowed in.

## Running Tests

```bash
pytest tests/ -v
```

15 tests: signup/login, room creation, direct-room reuse, message ordering,
non-member access control, file upload, plus 5 live WebSocket tests
(send/receive, broadcast to a second member, typing indicator, and
connection rejection without a token or for non-members). Tests use an
isolated SQLite database and the in-memory channel layer — no Postgres or
Redis needed.

## Design Notes

- **Consumers are thin**: `ChatConsumer` handles the socket lifecycle;
  database work goes through `database_sync_to_async` helpers.
- **Channel groups per room**: each room is a group named `chat_<id>`;
  sending = one `group_send`, and every member's socket gets the event.
- **Presence and typing are ephemeral**: broadcast through the channel
  layer only, never written to the database.
- **Uploads reuse the bus**: the HTTP upload view saves the Message, then
  pushes the same `chat_message` event the consumer uses — one code path
  for live delivery.
- **Auth split by transport**: HTTP views use Django sessions;
  WebSockets use per-user tokens in the query string.

## Possible Extensions

- Read receipts and unread-message counters
- Message editing/deletion with live updates
- Private typing indicator only to relevant users
- Push notifications for offline users
- Rate limiting on message sending
