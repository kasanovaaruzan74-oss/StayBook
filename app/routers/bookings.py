"""Брондауларды басқару және бір нөмірдің күндерін қабаттастырмау."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi import status as http_status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.db import get_session
from app.models import Booking, BookingStatus, Guest, Room
from app.schemas import BookingCreate, BookingRead, BookingUpdate


router = APIRouter(prefix="/bookings", tags=["Брондаулар"])
SessionDep = Annotated[Session, Depends(get_session)]


def _get_booking(session: Session, booking_id: int) -> Booking:
    booking = session.get(Booking, booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="Брондау табылмады.")
    return booking


def _reserve_writer(session: Session) -> None:
    # SQLite-де тексеру мен жазу бір транзакцияда өтеді: екі параллель
    # сұрау бір нөмірдің бірдей бос күндерін қатар брондай алмайды.
    if session.get_bind().dialect.name == "sqlite":
        session.execute(text("BEGIN IMMEDIATE"))


def _validate_booking(
    session: Session,
    *,
    guest_id: int,
    room_id: int,
    check_in: date,
    check_out: date,
    booking_status: BookingStatus,
    exclude_id: int | None = None,
) -> None:
    if check_out <= check_in:
        raise HTTPException(
            status_code=422,
            detail="Шығу күні кіру күнінен кейін болуы керек.",
        )
    if session.get(Guest, guest_id) is None:
        raise HTTPException(status_code=404, detail="Қонақ табылмады.")
    if session.get(Room, room_id) is None:
        raise HTTPException(status_code=404, detail="Нөмір табылмады.")

    # Cancelled брондау күндерді босатады. Шығу күніне басқа қонақ кіре алады:
    # [кіру, шығу) интервалдары тек екі қатаң теңсіздік орындалса қабаттасады.
    if booking_status == BookingStatus.cancelled:
        return
    statement = select(Booking).where(
        Booking.room_id == room_id,
        Booking.status != BookingStatus.cancelled,
        Booking.check_in < check_out,
        Booking.check_out > check_in,
    )
    if exclude_id is not None:
        statement = statement.where(Booking.id != exclude_id)
    if session.exec(statement).first() is not None:
        raise HTTPException(
            status_code=409,
            detail="Бұл нөмір көрсетілген күндерге брондалған.",
        )


def _save_booking(session: Session, booking: Booking) -> Booking:
    session.add(booking)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail="Брондауды сақтау мүмкін болмады: деректер байланысын тексеріңіз.",
        ) from None
    session.refresh(booking)
    return booking


@router.get("", response_model=list[BookingRead], summary="Брондаулар тізімі")
def list_bookings(
    session: SessionDep,
    guest_id: int | None = Query(default=None, ge=1),
    room_id: int | None = Query(default=None, ge=1),
    booking_status: BookingStatus | None = Query(default=None, alias="status"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[Booking]:
    statement = select(Booking)
    if guest_id is not None:
        statement = statement.where(Booking.guest_id == guest_id)
    if room_id is not None:
        statement = statement.where(Booking.room_id == room_id)
    if booking_status is not None:
        statement = statement.where(Booking.status == booking_status)
    statement = statement.order_by(Booking.id).offset(offset).limit(limit)
    return list(session.exec(statement).all())


@router.get(
    "/{booking_id}", response_model=BookingRead, summary="Брондауды ID бойынша табу"
)
def read_booking(booking_id: int, session: SessionDep) -> Booking:
    return _get_booking(session, booking_id)


@router.post(
    "",
    response_model=BookingRead,
    status_code=http_status.HTTP_201_CREATED,
    summary="Жаңа брондау жасау",
)
def create_booking(payload: BookingCreate, session: SessionDep) -> Booking:
    _reserve_writer(session)
    _validate_booking(
        session,
        guest_id=payload.guest_id,
        room_id=payload.room_id,
        check_in=payload.check_in,
        check_out=payload.check_out,
        booking_status=payload.status,
    )
    booking = Booking.model_validate(payload)
    return _save_booking(session, booking)




