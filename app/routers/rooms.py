"""Нөмірлер: іздеу, баға бойынша сүзгілеу және толық CRUD."""

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.db import get_session
from app.models import Booking, Room, RoomCategory
from app.schemas import RoomCreate, RoomRead, RoomUpdate

router = APIRouter(prefix="/rooms", tags=["Қонақүй нөмірлері"])
SessionDep = Annotated[Session, Depends(get_session)]


@router.get("", response_model=list[RoomRead], summary="Нөмірлер тізімі")
def list_rooms(session: SessionDep):
    return session.exec(select(Room).order_by(Room.id)).all()


@router.get("/{room_id}", response_model=RoomRead, summary="Нөмірді ID арқылы табу")
def get_room(room_id: int, session: SessionDep):
    room = session.get(Room, room_id)
    if room is None:
        raise HTTPException(404, "Қонақүй нөмірі табылмады.")
    return room


@router.post("", response_model=RoomRead, status_code=status.HTTP_201_CREATED,
             summary="Жаңа нөмір қосу")
def create_room(data: RoomCreate, session: SessionDep):
    if session.get(RoomCategory, data.category_id) is None:
        raise HTTPException(404, "Нөмір санаты табылмады.")
    room = Room.model_validate(data)
    session.add(room)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, "Мұндай нөмір бұрыннан бар немесе деректер қайшы.")
    session.refresh(room)
    return room




