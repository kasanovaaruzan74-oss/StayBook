"""SQLite қосылымы және әр сұрауға арналған жеке деректер сессиясы."""

import os
from collections.abc import Generator

from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./database.db")
SQL_ECHO = os.getenv("SQL_ECHO", "false").lower() in {"1", "true", "yes"}
is_sqlite = DATABASE_URL.startswith("sqlite")

engine = create_engine(
    DATABASE_URL,
    echo=SQL_ECHO,
    connect_args={"check_same_thread": False, "timeout": 15} if is_sqlite else {},
)


if is_sqlite:
    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
        # SQLite сыртқы кілттерді әдепкіде тексермейді: оны нақты қосамыз.
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def init_db() -> None:
    """Модельдер тіркелгеннен кейін жоқ кестелерді құрады."""
    from app import models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """Сұрау аяқталғанда сессияны жауып, аяқталмаған транзакцияны қайтарады."""
    with Session(engine) as session:
        yield session
