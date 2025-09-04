# app/create_tables.py
from .database import engine, Base
from . import models  # ensure models are imported before create_all

def create_all_tables():
    print("🔄 Creating all database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created successfully.")
