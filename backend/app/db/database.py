from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# On utilise l'URL de base configurée (sqlite par défaut localement)
# Pour PostgreSQL (Supabase), on passera par une variable d'environnement DATABASE_URL
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

# Correction pour SQLite (connect_args requis pour le multi-threading)
connect_args = {"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args=connect_args
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
