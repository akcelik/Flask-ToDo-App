Flask ToDo App
==============

A simple to-do list web app built with Flask, Flask-SQLAlchemy and PostgreSQL.

- Register and log in with a username and password (passwords are stored hashed)
- Each user has their own private ToDo list
- Add tasks, mark them as complete (and back), and delete them
- Dashboard with total / completed / pending counts

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Settings are read from environment variables:

| Variable       | Default                                               |
| -------------- | ----------------------------------------------------- |
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/todo`  |
| `SECRET_KEY`   | `dev-secret-key-change-me` (change this in production) |
| `FLASK_DEBUG`  | unset (set to `1` to enable debug mode)               |

Tables are created automatically on startup. If you have a database from the
older version (before user accounts), a `user_id` column is added to the
`to_do` table automatically. Old ToDo items have no owner, so they won't show
up for any user; assign them with e.g.
`UPDATE to_do SET user_id = 1 WHERE user_id IS NULL;`

## Run

```bash
export DATABASE_URL=postgresql://user:password@localhost:5432/todo
export SECRET_KEY=something-random
python todo.py
# or: flask --app todo run
```

Then open http://127.0.0.1:5000.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

Tests use an in-memory SQLite database, so no PostgreSQL is needed.
