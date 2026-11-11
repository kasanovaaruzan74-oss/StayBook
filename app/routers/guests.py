"""Қонақтарды тіркеу және басқару."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.db import get_session
from app.models import Booking, Guest
from app.schemas import GuestCreate, GuestRead, GuestUpdate

router = APIRouter(prefix="/guests", tags=["Қонақтар"])
SessionDep = Annotated[Session, Depends(get_session)]


@router.get("", response_model=list[GuestRead], summary="Қонақтар тізімі")
def list_guests(
    session: SessionDep,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
):
    return session.exec(select(Guest).order_by(Guest.id).offset(offset).limit(limit)).all()


@router.get("/{guest_id}", response_model=GuestRead, summary="Қонақты ID арқылы табу")
def get_guest(guest_id: int, session: SessionDep):
    guest = session.get(Guest, guest_id)
    if guest is None:
        raise HTTPException(404, "Қонақ табылмады.")
    return guest


@router.post("", response_model=GuestRead, status_code=status.HTTP_201_CREATED,
             summary="Жаңа қонақ тіркеу")
def create_guest(data: GuestCreate, session: SessionDep):
    guest = Guest.model_validate(data)
    session.add(guest)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, "Мұндай телефон немесе email бұрыннан тіркелген.")
    session.refresh(guest)
    return guest


@router.patch("/{guest_id}", response_model=GuestRead, summary="Қонақ деректерін өзгерту")
def update_guest(guest_id: int, data: GuestUpdate, session: SessionDep):
    guest = session.get(Guest, guest_id)
    if guest is None:
        raise HTTPException(404, "Қонақ табылмады.")
    guest.sqlmodel_update(data.model_dump(exclude_unset=True))
    session.add(guest)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, "Мұндай телефон немесе email бұрыннан тіркелген.")
    session.refresh(guest)
    return guest


@router.delete("/{guest_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Брондауы жоқ қонақты өшіру")
def delete_guest(guest_id: int, session: SessionDep):
    guest = session.get(Guest, guest_id)
    if guest is None:
        raise HTTPException(404, "Қонақ табылмады.")
    if session.exec(select(Booking.id).where(Booking.guest_id == guest_id).limit(1)).first() is not None:
        raise HTTPException(409, "Қонақта брондаулар бар. Алдымен оларды өшіріңіз.")
    session.delete(guest)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, "Бұл қонақ басқа жазбалармен байланысқан.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
