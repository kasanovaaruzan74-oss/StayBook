"""Нөмір санаттарының анықтамалығы."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.db import get_session
from app.models import Room, RoomCategory
from app.schemas import CategoryCreate, CategoryRead, CategoryUpdate

router = APIRouter(prefix="/categories", tags=["Нөмір санаттары"])
SessionDep = Annotated[Session, Depends(get_session)]


@router.get("", response_model=list[CategoryRead], summary="Санаттар тізімі")
def list_categories(
    session: SessionDep,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
):
    return session.exec(select(RoomCategory).order_by(RoomCategory.id).offset(offset).limit(limit)).all()


@router.get("/{category_id}", response_model=CategoryRead, summary="Санатты ID арқылы табу")
def get_category(category_id: int, session: SessionDep):
    category = session.get(RoomCategory, category_id)
    if category is None:
        raise HTTPException(404, "Нөмір санаты табылмады.")
    return category


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED,
             summary="Жаңа санат қосу")
def create_category(data: CategoryCreate, session: SessionDep):
    category = RoomCategory.model_validate(data)
    session.add(category)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, "Мұндай санат атауы бұрыннан бар.")
    session.refresh(category)
    return category




