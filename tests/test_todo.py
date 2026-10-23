import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest
from sqlalchemy import inspect, text

from todo import app, db, ToDo, User, init_db


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.app_context():
        db.drop_all()
        db.create_all()
    with app.test_client() as client:
        yield client


def register(client, username="alice", password="secret1", confirm=None):
    return client.post("/register", data={
        "username": username,
        "password": password,
        "confirm": password if confirm is None else confirm,
    })


def login(client, username="alice", password="secret1"):
    return client.post("/login", data={"username": username, "password": password})


def logout(client):
    return client.post("/logout")


@pytest.fixture
def auth_client(client):
    register(client)
    return client


def titles():
    with app.app_context():
        return [t.title for t in ToDo.query.order_by(ToDo.id).all()]


# --- auth ---

def test_index_requires_login(client):
    response = client.get("/")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_mutations_require_login(client):
    assert client.post("/add", data={"title": "x"}).status_code == 302
    assert client.get("/dashboard").status_code == 302
    assert titles() == []


def test_register_logs_in_and_hashes_password(client):
    response = register(client)
    assert response.status_code == 302
    assert client.get("/").status_code == 200
    with app.app_context():
        user = db.session.execute(db.select(User)).scalar_one()
        assert user.username == "alice"
        assert user.password_hash != "secret1"


def test_register_validation(client):
    register(client, password="123")
    register(client, password="secret1", confirm="other12")
    register(client, username="   ")
    with app.app_context():
        assert db.session.execute(db.select(User)).scalars().all() == []


def test_register_duplicate_username(client):
    register(client)
    logout(client)
    register(client, password="another1")
    with app.app_context():
        assert len(db.session.execute(db.select(User)).scalars().all()) == 1


def test_login_and_logout(client):
    register(client)
    logout(client)
    assert client.get("/").status_code == 302
    login(client, password="wrong-pw")
    assert client.get("/").status_code == 302
    login(client)
    assert client.get("/").status_code == 200


def test_logout_requires_post(auth_client):
    assert auth_client.get("/logout").status_code == 405


def test_users_only_see_and_change_their_own_todos(client):
    register(client, "alice")
    client.post("/add", data={"title": "Alice task"})
    logout(client)

    register(client, "bob")
    assert b"Alice task" not in client.get("/").data
    assert client.post("/complete/1").status_code == 404
    assert client.post("/delete/1").status_code == 404
    assert titles() == ["Alice task"]


# --- todos ---

def test_empty_list(auth_client):
    response = auth_client.get("/")
    assert response.status_code == 200
    assert b"ToDo list empty" in response.data


def test_add_todo(auth_client):
    response = auth_client.post("/add", data={"title": "  Buy milk  "})
    assert response.status_code == 302
    assert titles() == ["Buy milk"]
    assert b"Buy milk" in auth_client.get("/").data


def test_add_empty_title_rejected(auth_client):
    auth_client.post("/add", data={"title": "   "})
    auth_client.post("/add", data={})
    assert titles() == []


def test_add_too_long_title_rejected(auth_client):
    auth_client.post("/add", data={"title": "x" * 81})
    assert titles() == []


def test_toggle_complete(auth_client):
    auth_client.post("/add", data={"title": "Task"})
    auth_client.post("/complete/1")
    with app.app_context():
        assert db.session.get(ToDo, 1).complete is True
    auth_client.post("/complete/1")
    with app.app_context():
        assert db.session.get(ToDo, 1).complete is False


def test_delete(auth_client):
    auth_client.post("/add", data={"title": "Task"})
    auth_client.post("/delete/1")
    assert titles() == []


def test_missing_todo_returns_404(auth_client):
    assert auth_client.post("/complete/999").status_code == 404
    assert auth_client.post("/delete/999").status_code == 404


def test_get_not_allowed_for_mutations(auth_client):
    auth_client.post("/add", data={"title": "Task"})
    assert auth_client.get("/complete/1").status_code == 405
    assert auth_client.get("/delete/1").status_code == 405
    assert titles() == ["Task"]


def test_dashboard_counts(auth_client):
    for title in ["a", "b", "c", "d"]:
        auth_client.post("/add", data={"title": title})
    auth_client.post("/complete/1")
    html = auth_client.get("/dashboard").get_data(as_text=True)
    assert "25% completed" in html


def test_init_db_adds_user_id_to_old_schema(client):
    with app.app_context():
        with db.engine.begin() as conn:
            conn.execute(text("DROP TABLE to_do"))
            conn.execute(text("CREATE TABLE to_do (id INTEGER PRIMARY KEY, title VARCHAR(80), complete BOOLEAN)"))
        init_db()
        assert "user_id" in [c["name"] for c in inspect(db.engine).get_columns("to_do")]
