import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DB_URL = os.getenv("AI_SERVICE_DB_URL", "sqlite:///./data/ai_service.db")

engine = create_engine(DB_URL, connect_args={"check_same_thread": False} if DB_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db() -> None:
    if DB_URL.startswith("sqlite"):
        os.makedirs("./data", exist_ok=True)
    Base.metadata.create_all(bind=engine)
