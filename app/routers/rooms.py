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


@router.get("", response_model=list[RoomRead], summary="Нөмірлерді іздеу және сүзгілеу")
def list_rooms(
    session: SessionDep,
    search: Annotated[str | None, Query(max_length=100)] = None,
    min_price: Annotated[Decimal | None, Query(ge=0)] = None,
    max_price: Annotated[Decimal | None, Query(ge=0)] = None,
    category_id: Annotated[int | None, Query(gt=0)] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
):
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(422, "Ең төмен баға ең жоғары бағадан аспауы керек.")
    statement = select(Room)
    if search:
        # contains SQL параметрлерін қолданады; % пен _ жай таңба ретінде ізделеді.
        statement = statement.where(Room.room_number.contains(search.strip(), autoescape=True))
    if min_price is not None:
        statement = statement.where(Room.price_per_night >= min_price)
    if max_price is not None:
        statement = statement.where(Room.price_per_night <= max_price)
    if category_id is not None:
        statement = statement.where(Room.category_id == category_id)
    return session.exec(statement.order_by(Room.id).offset(offset).limit(limit)).all()


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


@router.patch("/{room_id}", response_model=RoomRead, summary="Нөмірдің жеке өрістерін өзгерту")
def update_room(room_id: int, data: RoomUpdate, session: SessionDep):
    room = session.get(Room, room_id)
    if room is None:
        raise HTTPException(404, "Қонақүй нөмірі табылмады.")
    changes = data.model_dump(exclude_unset=True)
    if "category_id" in changes and session.get(RoomCategory, changes["category_id"]) is None:
        raise HTTPException(404, "Нөмір санаты табылмады.")
    room.sqlmodel_update(changes)
    session.add(room)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, "Мұндай нөмір бұрыннан бар немесе деректер қайшы.")
    session.refresh(room)
    return room


@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Брондауы жоқ нөмірді өшіру")
def delete_room(room_id: int, session: SessionDep):
    room = session.get(Room, room_id)
    if room is None:
        raise HTTPException(404, "Қонақүй нөмірі табылмады.")
    if session.exec(select(Booking.id).where(Booking.room_id == room_id).limit(1)).first() is not None:
        raise HTTPException(409, "Нөмірде брондаулар бар. Алдымен оларды өшіріңіз.")
    session.delete(room)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, "Бұл нөмір басқа жазбалармен байланысқан.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
