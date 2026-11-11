"""Room CRUD, filtering, and input validation through the public HTTP API."""

from decimal import Decimal

import pytest


def test_room_crud_preserves_unpatched_fields(client, room):
    room_id = room["id"]
    assert client.get(f"/rooms/{room_id}").json() == room

    response = client.patch(f"/rooms/{room_id}", json={"price_per_night": "17500.50"})
    assert response.status_code == 200, response.text
    changed = response.json()
    assert Decimal(str(changed["price_per_night"])) == Decimal("17500.50")
    for field in ("id", "room_number", "category_id", "capacity"):
        assert changed[field] == room[field]
    assert client.get(f"/rooms/{room_id}").json() == changed

    deleted = client.delete(f"/rooms/{room_id}")
    assert deleted.status_code == 204
    assert deleted.content == b""
    assert client.get(f"/rooms/{room_id}").status_code == 404
    assert client.patch(f"/rooms/{room_id}", json={"capacity": 3}).status_code == 404
    assert client.delete(f"/rooms/{room_id}").status_code == 404


def test_room_list_returns_created_room(client, room):
    response = client.get("/rooms")
    assert response.status_code == 200
    assert response.json() == [room]


@pytest.mark.parametrize(
    "changes",
    [
        {"price_per_night": -1},
        {"room_number": "   "},
        {"capacity": 0},
        {"id": 99},
    ],
)
def test_room_creation_rejects_invalid_input(client, category, changes):
    payload = {"category_id": category["id"], "room_number": "102", "price_per_night": 10000, "capacity": 2}
    payload.update(changes)
    response = client.post("/rooms", json=payload)
    assert response.status_code == 422, response.text
    assert client.get("/rooms").json() == []


@pytest.mark.parametrize("field", ["room_number", "price_per_night", "capacity", "category_id"])
def test_patch_rejects_explicit_null_without_changing_room(client, room, field):
    response = client.patch(f"/rooms/{room['id']}", json={field: None})
    assert response.status_code == 422, response.text
    assert client.get(f"/rooms/{room['id']}").json() == room


def test_duplicate_room_number_is_conflict_and_session_remains_usable(client, room):
    payload = {key: value for key, value in room.items() if key != "id"}
    response = client.post("/rooms", json=payload)
    assert response.status_code == 409, response.text
    payload["room_number"] = "102"
    assert client.post("/rooms", json=payload).status_code == 201
    assert len(client.get("/rooms").json()) == 2


def test_room_references_must_exist(client):
    response = client.post(
        "/rooms",
        json={"category_id": 99999, "room_number": "101", "price_per_night": 100, "capacity": 1},
    )
    assert response.status_code == 404, response.text
    assert client.get("/rooms/99999").status_code == 404


def test_room_search_price_and_category_filters_compose(client, category):
    other = client.post("/categories", json={"name": "Suite", "description": "Large room"}).json()
    examples = [
        {"room_number": "101", "category_id": category["id"], "price_per_night": "10000", "capacity": 1},
        {"room_number": "102", "category_id": category["id"], "price_per_night": "20000", "capacity": 2},
        {"room_number": "201", "category_id": other["id"], "price_per_night": "30000", "capacity": 3},
    ]
    for item in examples:
        response = client.post("/rooms", json=item)
        assert response.status_code == 201, response.text

    def numbers(**params):
        response = client.get("/rooms", params=params)
        assert response.status_code == 200, response.text
        return {item["room_number"] for item in response.json()}

    assert numbers(search="10") == {"101", "102"}
    assert numbers(min_price=20000, max_price=30000) == {"102", "201"}
    assert numbers(category_id=other["id"]) == {"201"}
    assert numbers(search="10", min_price=15000, max_price=25000, category_id=category["id"]) == {"102"}
    assert numbers(search="' OR 1=1 --") == set()
    assert len(client.get("/rooms").json()) == 3


@pytest.mark.parametrize(
    "params",
    [{"min_price": -1}, {"max_price": -1}, {"min_price": 30000, "max_price": 10000}],
)
def test_invalid_price_filters_return_validation_error(client, params):
    response = client.get("/rooms", params=params)
    assert response.status_code == 422, response.text
