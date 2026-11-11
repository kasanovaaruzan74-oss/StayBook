"""FastAPI қосымшасының кіру нүктесі: uvicorn app.main:app --reload."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database.db import init_db
from app.routers import bookings, categories, guests, rooms


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="StayBook — Қонақүй нөмірлерін брондау",
    description=(
        "1–4 зертханалық жұмыс: SQLModel, SQLite, REST API, валидация және толық CRUD. "
        "Бағалар теңгемен (KZT) беріледі. Кіру және шығу күндері [check_in, check_out) "
        "аралығын білдіреді: бір брондау аяқталған күні келесісі бастала алады."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(categories.router)
app.include_router(guests.router)
app.include_router(rooms.router)
app.include_router(bookings.router)


@app.get("/", tags=["Жүйе"], summary="Сервердің күйін тексеру")
def health():
    return {"status": "ok", "project": "StayBook", "docs": "/docs"}
