"""Әр кестеге бес синтетикалық жазба қосады: python seed.py.

Қайта іске қосқанда табиғи кілттермен бұрынғы жазбаларды тауып, қайталамайды.
Қолмен өзгертілген деректерді бастапқы мәнге қайтармайды.
"""

import json
from datetime import date
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, select

from app.database.db import engine, init_db
from app.database.models import Booking, BookingStatus, Guest, Room, RoomCategory


def seed_data(db_engine: Engine | None = None) -> dict[str, int]:
    """Деректерді қосып, кестелердегі жалпы жазбалар санын қайтарады."""
    target_engine = db_engine if db_engine is not None else engine
    if db_engine is None:
        init_db()
    else:
        SQLModel.metadata.create_all(target_engine)

    categories_data = [
        ("Стандарт", "Бір немесе екі адамға арналған қолжетімді нөмір."),
        ("Комфорт", "Жұмыс орны мен кең демалыс аймағы бар нөмір."),
        ("Делюкс", "Қала көрінісі және кең жатын бөлмесі бар нөмір."),
        ("Отбасылық", "Балалы отбасыға арналған төрт орындық нөмір."),
        ("Люкс", "Жеке қонақ бөлмесі бар жоғары санатты нөмір."),
    ]
    guests_data = [
        ("Айдана Сынақова", "+77000000001", "aidana@example.com"),
        ("Ерлан Үлгібаев", "+77000000002", "erlan@example.com"),
        ("Дана Мысалқызы", "+77000000003", "dana@example.com"),
        ("Арман Тестов", "+77000000004", "arman@example.com"),
        ("Әсел Демоқызы", "+77000000005", "asel@example.com"),
    ]
    room_numbers = ["101", "201", "301", "401", "501"]
    prices = ["18000.00", "25000.00", "35000.00", "42000.00", "65000.00"]
    capacities = [2, 2, 2, 4, 3]

    with Session(target_engine) as session:
        categories = []
        for name, description in categories_data:
            category = session.exec(select(RoomCategory).where(RoomCategory.name == name)).first()
            if category is None:
                category = RoomCategory(name=name, description=description)
                session.add(category)
                session.flush()
            categories.append(category)

        guests = []
        for full_name, phone, email in guests_data:
            guest = session.exec(select(Guest).where(Guest.email == email)).first()
            if guest is None:
                guest = Guest(full_name=full_name, phone=phone, email=email)
                session.add(guest)
                session.flush()
            guests.append(guest)

        rooms = []
        for index, room_number in enumerate(room_numbers):
            room = session.exec(select(Room).where(Room.room_number == room_number)).first()
            if room is None:
                room = Room(
                    category_id=categories[index].id,
                    room_number=room_number,
                    price_per_night=Decimal(prices[index]),
                    capacity=capacities[index],
                )
                session.add(room)
                session.flush()
            rooms.append(room)

        for index in range(5):
            check_in = date(2027, 1, 10 + index * 3)
            check_out = date(2027, 1, 12 + index * 3)
            booking = session.exec(
                select(Booking).where(
                    Booking.guest_id == guests[index].id,
                    Booking.room_id == rooms[index].id,
                    Booking.check_in == check_in,
                    Booking.check_out == check_out,
                )
            ).first()
            if booking is None:
                booking = Booking(
                    guest_id=guests[index].id,
                    room_id=rooms[index].id,
                    check_in=check_in,
                    check_out=check_out,
                    status=BookingStatus.confirmed,
                )
                session.add(booking)

        session.commit()
        return {
            "guests": session.exec(select(func.count()).select_from(Guest)).one(),
            "room_categories": session.exec(select(func.count()).select_from(RoomCategory)).one(),
            "rooms": session.exec(select(func.count()).select_from(Room)).one(),
            "bookings": session.exec(select(func.count()).select_from(Booking)).one(),
        }


if __name__ == "__main__":
    print(json.dumps(seed_data(), ensure_ascii=False, indent=2))
