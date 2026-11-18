"""
LabelIntel — SQLite Database Configuration via SQLAlchemy
"""

from pathlib import Path
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

DB_PATH = Path("data/labelintel.db").resolve()
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency to provide a thread-safe database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initializes tables and applies small, non-destructive SQLite upgrades."""
    Base.metadata.create_all(bind=engine)

    # ``create_all`` does not add columns to an existing SQLite table. Keep
    # the local demo database backward-compatible without requiring a reset or
    # introducing a migration dependency for this small application.
    inspector = inspect(engine)
    if "inspections" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("inspections")}
        if "file_hash" not in columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE inspections ADD COLUMN file_hash VARCHAR(64)"))
