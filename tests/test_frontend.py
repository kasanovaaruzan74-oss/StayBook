"""Exercise real Streamlit widgets while the HTTP boundary uses a fake API."""

from copy import deepcopy
import json
from pathlib import Path
from urllib.parse import urlsplit

import pytest
import requests
from streamlit.testing.v1 import AppTest


UI_PATH = Path(__file__).resolve().parents[1] / "app" / "frontend" / "ui.py"


@pytest.fixture
def fake_api(monkeypatch):
    """Small HTTP fixture: no Streamlit internals or database access is mocked."""
    resources = {
        "/categories": [
            {"id": 1, "name": "Standard", "description": "Comfortable"},
            {"id": 2, "name": "Suite", "description": "Spacious"},
        ],
        "/rooms": [
            {"id": 1, "category_id": 1, "room_number": "101", "price_per_night": "15000.00", "capacity": 2},
            {"id": 2, "category_id": 2, "room_number": "201", "price_per_night": "30000.00", "capacity": 3},
        ],
        "/guests": [{"id": 1, "full_name": "Aruzhan Test", "phone": "+77010000001", "email": "aruzhan@example.test"}],
        "/bookings": [{"id": 1, "guest_id": 1, "room_id": 1, "check_in": "2026-12-10", "check_out": "2026-12-12", "status": "confirmed"}],
    }
    calls = []

    def handle(method, url, **kwargs):
        path = urlsplit(url).path
        calls.append({"method": method.upper(), "path": path, **deepcopy(kwargs)})
        if method.upper() == "GET":
            payload = deepcopy(resources[path])
            if path == "/rooms":
                params = kwargs.get("params") or {}
                if params.get("search"):
                    payload = [room for room in payload if params["search"] in room["room_number"]]
                if params.get("category_id") is not None:
                    payload = [room for room in payload if room["category_id"] == int(params["category_id"])]
                if params.get("min_price") is not None:
                    payload = [room for room in payload if float(room["price_per_night"]) >= float(params["min_price"])]
                if params.get("max_price") is not None:
                    payload = [room for room in payload if float(room["price_per_night"]) <= float(params["max_price"])]
            status_code = 200
        elif method.upper() == "POST" and path == "/rooms":
            payload = {"id": 3, **kwargs["json"]}
            resources[path].append(payload)
            status_code = 201
        else:
            raise AssertionError(f"Unexpected API request: {method} {path}")
        response = requests.Response()
        response.status_code = status_code
        response._content = json.dumps(payload).encode("utf-8")
        response.encoding = "utf-8"
        response.headers["Content-Type"] = "application/json"
        return response

    monkeypatch.setenv("BACKEND_URL", "http://staybook.test:8000")
    monkeypatch.setattr(requests, "request", handle)
    return calls


def by_label(elements, label):
    return next(element for element in elements if element.label == label)


def test_room_search_reruns_without_submit_and_sends_query_parameters(fake_api):
    app = AppTest.from_file(str(UI_PATH), default_timeout=10).run()
    assert not app.exception
    fake_api.clear()

    by_label(app.text_input, "Нөмірді іздеу").set_value("201").run()

    assert not app.exception
    searches = [call for call in fake_api if call["method"] == "GET" and call["path"] == "/rooms" and call.get("params")]
    assert searches[-1]["params"]["search"] == "201"
    assert app.dataframe[0].value["Нөмір"].astype(str).tolist() == ["201"]


def test_room_creation_form_posts_to_api_and_refreshes_table(fake_api):
    app = AppTest.from_file(str(UI_PATH), default_timeout=10).run()
    assert not app.exception
    by_label(app.text_input, "Нөмір атауы").set_value("401")
    by_label(app.number_input, "Бір тәулік бағасы, ₸").set_value(25000.0)
    by_label(app.number_input, "Сыйымдылығы").set_value(4)
    by_label(app.button, "Нөмірді қосу").click().run()

    assert not app.exception
    posts = [call for call in fake_api if call["method"] == "POST" and call["path"] == "/rooms"]
    assert len(posts) == 1
    assert posts[0]["json"] == {
        "room_number": "401", "category_id": 1, "price_per_night": "25000.0", "capacity": 4,
    }
    assert "401" in app.dataframe[0].value["Нөмір"].astype(str).tolist()
    assert any("қосылды" in notice.value for notice in app.success)


def test_api_offline_shows_recovery_instructions_without_traceback(monkeypatch):
    def unavailable(*_args, **_kwargs):
        raise requests.ConnectionError("Test API is offline")

    monkeypatch.setattr(requests, "request", unavailable)
    app = AppTest.from_file(str(UI_PATH), default_timeout=10).run()

    assert not app.exception
    assert any("Серверге қосылу мүмкін болмады" in message.value for message in app.error)
    assert any("uvicorn app.main:app --reload" in snippet.value for snippet in app.code)
