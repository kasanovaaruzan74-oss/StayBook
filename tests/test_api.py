"""ЛР №7: API-дің оқу нұсқаулығында талап етілген екі негізгі тексеруі."""


def test_get_rooms_returns_200(client):
    response = client.get("/rooms")
    assert response.status_code == 200
    assert response.json() == []


def test_post_room_returns_201_and_persists_record(client, category):
    payload = {
        "room_number": "401",
        "category_id": category["id"],
        "price_per_night": "25000.00",
        "capacity": 2,
    }
    response = client.post("/rooms", json=payload)
    assert response.status_code == 201, response.text
    saved = response.json()
    assert isinstance(saved["id"], int)
    assert saved["room_number"] == payload["room_number"]
    assert client.get(f"/rooms/{saved['id']}").json() == saved
