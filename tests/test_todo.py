import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest

from todo import app, db, ToDo


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.app_context():
        db.drop_all()
        db.create_all()
    with app.test_client() as client:
        yield client


def titles():
    with app.app_context():
        return [t.title for t in ToDo.query.order_by(ToDo.id).all()]


def test_empty_list(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"ToDo list empty" in response.data


def test_add_todo(client):
    response = client.post("/add", data={"title": "  Buy milk  "})
    assert response.status_code == 302
    assert titles() == ["Buy milk"]
    assert b"Buy milk" in client.get("/").data


def test_add_empty_title_rejected(client):
    client.post("/add", data={"title": "   "})
    client.post("/add", data={})
    assert titles() == []


def test_add_too_long_title_rejected(client):
    client.post("/add", data={"title": "x" * 81})
    assert titles() == []


def test_toggle_complete(client):
    client.post("/add", data={"title": "Task"})
    client.post("/complete/1")
    with app.app_context():
        assert db.session.get(ToDo, 1).complete is True
    client.post("/complete/1")
    with app.app_context():
        assert db.session.get(ToDo, 1).complete is False


def test_delete(client):
    client.post("/add", data={"title": "Task"})
    client.post("/delete/1")
    assert titles() == []


def test_missing_todo_returns_404(client):
    assert client.post("/complete/999").status_code == 404
    assert client.post("/delete/999").status_code == 404


def test_get_not_allowed_for_mutations(client):
    client.post("/add", data={"title": "Task"})
    assert client.get("/complete/1").status_code == 405
    assert client.get("/delete/1").status_code == 405
    assert titles() == ["Task"]
