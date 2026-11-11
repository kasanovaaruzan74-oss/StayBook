"""Real schema constraints and reproducible seed data, using temporary files."""

import os
from pathlib import Path
import sqlite3
import subprocess
import sys

from sqlalchemy import inspect


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_schema_contains_foreign_keys_and_orm_relationships(engine):
    from app.models import Booking, Guest, Room, RoomCategory

    schema = inspect(engine)
    assert {"guests", "room_categories", "rooms", "bookings"}.issubset(schema.get_table_names())
    room_keys = schema.get_foreign_keys("rooms")
    assert any(key["constrained_columns"] == ["category_id"] and key["referred_table"] == "room_categories" for key in room_keys)
    booking_keys = schema.get_foreign_keys("bookings")
    assert {tuple(key["constrained_columns"]) for key in booking_keys} == {("guest_id",), ("room_id",)}
    assert inspect(Guest).relationships
    assert inspect(RoomCategory).relationships
    assert inspect(Room).relationships
    assert inspect(Booking).relationships


def test_seed_is_reproducible_and_idempotent(tmp_path):
    database_path = tmp_path / "seed.db"
    environment = {**os.environ, "DATABASE_URL": f"sqlite:///{database_path}", "SQL_ECHO": "0"}

    def snapshot_after_seed():
        process = subprocess.run(
            [sys.executable, "seed.py"], cwd=PROJECT_ROOT, env=environment,
            capture_output=True, text=True, timeout=30,
        )
        assert process.returncode == 0, process.stdout + process.stderr
        with sqlite3.connect(database_path) as database:
            return {
                table: database.execute(f"SELECT * FROM {table} ORDER BY id").fetchall()
                for table in ("guests", "room_categories", "rooms", "bookings")
            }

    first = snapshot_after_seed()
    assert all(3 <= len(rows) <= 5 for rows in first.values())
    assert snapshot_after_seed() == first
