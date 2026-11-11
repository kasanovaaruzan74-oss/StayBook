"""Клиенттен келетін деректер мен API жауаптарының жеке схемалары."""

from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models import BookingStatus

Name = Annotated[str, Field(min_length=1, max_length=100)]
Phone = Annotated[str, Field(min_length=7, max_length=30)]
Email = Annotated[
    str,
    Field(min_length=3, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$"),
]
RoomNumber = Annotated[str, Field(min_length=1, max_length=20)]
Money = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]
PositiveId = Annotated[int, Field(gt=0)]
Capacity = Annotated[int, Field(ge=1, le=20)]


class Schema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
        str_strip_whitespace=True,
    )


class UpdateSchema(Schema):
    @model_validator(mode="before")
    @classmethod
    def reject_explicit_null(cls, data):
        # Жіберілмеген өріс өзгермейді; әдейі жіберілген null қабылданбайды.
        if isinstance(data, dict) and any(value is None for value in data.values()):
            raise ValueError("Өрісті null етуге болмайды; өзгертпесеңіз, оны жібермеңіз.")
        return data


class GuestCreate(Schema):
    full_name: Name
    phone: Phone
    email: Email


class GuestRead(GuestCreate):
    id: int


class GuestUpdate(UpdateSchema):
    full_name: Name | None = None
    phone: Phone | None = None
    email: Email | None = None


class CategoryCreate(Schema):
    name: Annotated[str, Field(min_length=1, max_length=80)]
    description: Annotated[str, Field(max_length=1000)] = ""


class CategoryRead(CategoryCreate):
    id: int


class CategoryUpdate(UpdateSchema):
    name: Annotated[str, Field(min_length=1, max_length=80)] | None = None
    description: Annotated[str, Field(max_length=1000)] | None = None


class RoomCreate(Schema):
    category_id: PositiveId
    room_number: RoomNumber
    price_per_night: Money
    capacity: Capacity


class RoomRead(RoomCreate):
    id: int


class RoomUpdate(UpdateSchema):
    category_id: PositiveId | None = None
    room_number: RoomNumber | None = None
    price_per_night: Money | None = None
    capacity: Capacity | None = None


class BookingCreate(Schema):
    guest_id: PositiveId
    room_id: PositiveId
    check_in: date
    check_out: date
    status: BookingStatus = BookingStatus.confirmed

    @model_validator(mode="after")
    def validate_dates(self):
        if self.check_out <= self.check_in:
            raise ValueError("Шығу күні келу күнінен кейін болуы керек.")
        return self


class BookingRead(BookingCreate):
    id: int


class BookingUpdate(UpdateSchema):
    guest_id: PositiveId | None = None
    room_id: PositiveId | None = None
    check_in: date | None = None
    check_out: date | None = None
    status: BookingStatus | None = None

    @model_validator(mode="after")
    def validate_dates(self):
        if self.check_in is not None and self.check_out is not None:
            if self.check_out <= self.check_in:
                raise ValueError("Шығу күні келу күнінен кейін болуы керек.")
        return self
