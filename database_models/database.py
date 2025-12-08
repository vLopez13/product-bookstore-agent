import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from dotenv import load_dotenv
from database_models.db_models import Base

##this loads in the Database connection from file for security
load_dotenv()

DATABASE_URL = os.getenv("DB_CONN_STR")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in the .env file")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
#creates new engine here
engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
#pass Base
class Base(DeclarativeBase):
    pass
#checks if the tables have been created if not its okay do nothing
Base.metadata.create_all(bind=engine)
# gets database
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()