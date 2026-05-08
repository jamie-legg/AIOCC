#!/usr/bin/env python3
"""Initialize the Upload Studio backend database."""

from backend.src.database import Base, engine
import backend.src.models  # noqa: F401 - registers SQLAlchemy models with Base

def init_database():
    """Create all backend tables."""
    print("[INIT] Initializing Upload Studio database...")
    Base.metadata.create_all(bind=engine)
    print("[INIT] Database tables created/verified")

if __name__ == "__main__":
    init_database()

