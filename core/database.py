from sqlmodel import SQLModel, create_engine, Session
# Import all models so SQLModel knows about them before create_all()
from models.database import User, Video, Favorite, SearchHistory, RadarKeyword

sqlite_url = "sqlite:///./nocta_trends.db"
# Use check_same_thread=False for FastAPI + SQLite
engine = create_engine(sqlite_url, echo=False, connect_args={"check_same_thread": False})

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
