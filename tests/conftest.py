"""Integration fixtures: every test gets a real, isolated SQLite database."""

from importlib import import_module

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine


@pytest.fixture
def engine(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'test.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("SQL_ECHO", "0")
    database = import_module("app.database.db")
    import_module("app.database.models")
    test_engine = create_engine(database_url, connect_args={"check_same_thread": False})

    @event.listens_for(test_engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    monkeypatch.setattr(database, "engine", test_engine)
    SQLModel.metadata.create_all(test_engine)
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def client(engine):
    database = import_module("app.database.db")
    application = import_module("app.main").app

    def isolated_session():
        with Session(engine) as session:
            yield session

    application.dependency_overrides[database.get_session] = isolated_session
    with TestClient(application) as test_client:
        yield test_client
    application.dependency_overrides.clear()


@pytest.fixture
def category(client):
    response = client.post("/categories", json={"name": "Standard", "description": "Comfortable room"})
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
def guest(client):
    response = client.post(
        "/guests",
        json={"full_name": "Aruzhan Test", "phone": "+77010000001", "email": "aruzhan@example.test"},
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
def room(client, category):
    response = client.post(
        "/rooms",
        json={"category_id": category["id"], "room_number": "101", "price_per_night": "15000.00", "capacity": 2},
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
def booking_payload(guest, room):
    return {
        "guest_id": guest["id"],
        "room_id": room["id"],
        "check_in": "2026-12-10",
        "check_out": "2026-12-12",
        "status": "confirmed",
    }
