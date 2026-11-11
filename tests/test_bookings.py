"""Booking date rules and relational integrity across public endpoints."""

import pytest


def create_booking(client, payload):
    response = client.post("/bookings", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_booking_round_trip_and_referenced_room_is_protected(client, booking_payload):
    booking = create_booking(client, booking_payload)
    assert client.get(f"/bookings/{booking['id']}").json() == booking
    assert client.get("/bookings").json() == [booking]
    response = client.delete(f"/rooms/{booking_payload['room_id']}")
    assert response.status_code == 409, response.text
    assert client.get(f"/rooms/{booking_payload['room_id']}").status_code == 200


@pytest.mark.parametrize("checkout", ["2026-12-09", "2026-12-10"])
def test_booking_must_end_after_check_in(client, booking_payload, checkout):
    booking_payload["check_out"] = checkout
    response = client.post("/bookings", json=booking_payload)
    assert response.status_code == 422, response.text
    assert client.get("/bookings").json() == []


@pytest.mark.parametrize("field", ["room_id", "guest_id"])
def test_booking_references_must_exist(client, booking_payload, field):
    booking_payload[field] = 99999
    response = client.post("/bookings", json=booking_payload)
    assert response.status_code == 404, response.text


@pytest.mark.parametrize(
    "start,end",
    [
        ("2026-12-10", "2026-12-12"),
        ("2026-12-09", "2026-12-11"),
        ("2026-12-11", "2026-12-13"),
        ("2026-12-09", "2026-12-13"),
    ],
)
def test_overlapping_booking_is_conflict(client, booking_payload, start, end):
    create_booking(client, booking_payload)
    replacement = {**booking_payload, "check_in": start, "check_out": end}
    response = client.post("/bookings", json=replacement)
    assert response.status_code == 409, response.text
    assert len(client.get("/bookings").json()) == 1


@pytest.mark.parametrize(
    "start,end", [("2026-12-08", "2026-12-10"), ("2026-12-12", "2026-12-14")]
)
def test_adjacent_bookings_are_allowed(client, booking_payload, start, end):
    create_booking(client, booking_payload)
    adjacent = {**booking_payload, "check_in": start, "check_out": end}
    create_booking(client, adjacent)
    assert len(client.get("/bookings").json()) == 2


def test_cancellation_releases_dates(client, booking_payload):
    booking = create_booking(client, booking_payload)
    response = client.patch(f"/bookings/{booking['id']}", json={"status": "cancelled"})
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "cancelled"
    replacement = create_booking(client, booking_payload)
    assert replacement["id"] != booking["id"]
    # Re-activating the first reservation must not create a collision either.
    response = client.patch(f"/bookings/{booking['id']}", json={"status": "confirmed"})
    assert response.status_code == 409, response.text
    assert client.get(f"/bookings/{booking['id']}").json()["status"] == "cancelled"


def test_booking_partial_update_validates_combined_dates(client, booking_payload):
    booking = create_booking(client, booking_payload)
    response = client.patch(f"/bookings/{booking['id']}", json={"check_out": "2026-12-09"})
    assert response.status_code == 422, response.text
    assert client.get(f"/bookings/{booking['id']}").json() == booking


def test_deleted_booking_is_not_found(client, booking_payload):
    booking = create_booking(client, booking_payload)
    response = client.delete(f"/bookings/{booking['id']}")
    assert response.status_code == 204
    assert response.content == b""
    assert client.get(f"/bookings/{booking['id']}").status_code == 404
