"""ER-диаграммадағы төрт кестеге сәйкес SQLModel ORM модельдері."""

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from sqlalchemy import CheckConstraint
from sqlmodel import Field, Relationship, SQLModel


class BookingStatus(str, Enum):
    confirmed = "confirmed"
    cancelled = "cancelled"
    completed = "completed"


class Guest(SQLModel, table=True):
    __tablename__ = "guests"

    id: Optional[int] = Field(default=None, primary_key=True)
    full_name: str = Field(max_length=100)
    phone: str = Field(unique=True, index=True, max_length=30)
    email: str = Field(unique=True, index=True, max_length=254)

    bookings: List["Booking"] = Relationship(back_populates="guest")


class RoomCategory(SQLModel, table=True):
    __tablename__ = "room_categories"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True, max_length=80)
    description: str = Field(default="", max_length=1000)

    rooms: List["Room"] = Relationship(back_populates="category")


class Room(SQLModel, table=True):
    __tablename__ = "rooms"
    __table_args__ = (
        CheckConstraint("price_per_night >= 0", name="ck_room_price_nonnegative"),
        CheckConstraint("capacity >= 1", name="ck_room_capacity_positive"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    category_id: int = Field(foreign_key="room_categories.id", index=True)
    room_number: str = Field(unique=True, index=True, max_length=20)
    price_per_night: Decimal = Field(max_digits=12, decimal_places=2, ge=0)
    capacity: int = Field(ge=1)

    category: Optional[RoomCategory] = Relationship(back_populates="rooms")
    bookings: List["Booking"] = Relationship(back_populates="room")


class Booking(SQLModel, table=True):
    __tablename__ = "bookings"
    __table_args__ = (
        CheckConstraint("check_out > check_in", name="ck_booking_dates"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    guest_id: int = Field(foreign_key="guests.id", index=True)
    room_id: int = Field(foreign_key="rooms.id", index=True)
    check_in: date
    check_out: date
    status: BookingStatus = Field(default=BookingStatus.confirmed, index=True)

    guest: Optional[Guest] = Relationship(back_populates="bookings")
    room: Optional[Room] = Relationship(back_populates="bookings")
