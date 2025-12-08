from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os
import logging

# import the declarative Base and models so metadata is populated
from database_models.db_models import Base  # ensures your models are registered on this Base

load_dotenv()

DATABASE_URL = os.getenv('DB_CONN_STR')

# create engine and session factory
engine = create_engine(DATABASE_URL, echo=True, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    logging.info("create_tables: using DATABASE_URL=%s", DATABASE_URL)
    # show what metadata knows about before creating
    logging.info("Base.metadata.tables keys before create_all: %s", list(Base.metadata.tables.keys()))
    Base.metadata.create_all(bind=engine)
    # inspect DB to confirm
    inspector = inspect(engine)
    logging.info("Tables in DB after create_all: %s", inspector.get_table_names())
