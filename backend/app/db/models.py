from sqlalchemy import Column, String, Boolean, DateTime, JSON, ForeignKey, Table, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
import uuid

def generate_uuid():
    return str(uuid.uuid4())

# Table d'association pour Event <-> Task (Many-to-Many ou One-to-Many avec relation flexible)
# Dans NovaFlow, une tâche peut être liée à un seul événement parent (One-to-Many).
# Mais on garde la structure flexible.

class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, index=True) # UUID
    title = Column(String, nullable=False)
    priority = Column(String, default="medium")
    meta = Column(String, default="NovaFlow")
    done = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    due_date = Column(String, nullable=True) # ISO Date string format
    description = Column(String, default="")
    
    # Association avec les cours Moodle
    course_id = Column(String, nullable=True)
    
    # Association avec l'utilisateur
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    
    # Association avec les événements (Google, Outlook, Moodle, local)
    parent_event_id = Column(String, ForeignKey("events.id"), nullable=True)
    
    # Métadonnées Cloud Migration
    sync_status = Column(String, default="local") # "local", "pending", "synced"
    external_id = Column(String, nullable=True)
    source = Column(String, default="local")
    
    # Relations
    parent_event = relationship("Event", back_populates="tasks")
    user = relationship("User", back_populates="tasks")

class Event(Base):
    __tablename__ = "events"

    id = Column(String, primary_key=True, index=True) # UUID Interne
    external_id = Column(String, nullable=True) # ID Google, Outlook, Moodle
    source = Column(String, nullable=False) # "google_calendar", "outlook_calendar", "moodle", "local"
    title = Column(String, nullable=False)
    start = Column(String, nullable=False) # ISO Start
    updated = Column(String, nullable=True) # ISO Updated
    desc_hash = Column(String, nullable=True) # Pour détection de changement
    category = Column(String, nullable=True) # Pour le frontend
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Association avec l'utilisateur
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    
    # Relations
    tasks = relationship("Task", back_populates="parent_event")
    user = relationship("User", back_populates="events")

class ChatMessage(Base):
    __tablename__ = "chat_history"

    id = Column(String, primary_key=True, index=True) # YYYYMMDDHHMMSSf
    role = Column(String, nullable=False) # "user" ou "ai"
    content = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Optionnel: lier à une session de chat future
    session_id = Column(String, nullable=True)
    
    # Association avec l'utilisateur
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    user = relationship("User", back_populates="chat_history")

class MoodleConfig(Base):
    """Stockage des URLs et réglages Moodle autrefois dans data/moodle_settings.json."""
    __tablename__ = "moodle_config"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String, nullable=False, unique=True)
    token = Column(String, nullable=True)
    sesskey = Column(String, nullable=True)
    last_sync = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)

class MoodleExtCourse(Base):
    """Cache des cours extraits via l'extension."""
    __tablename__ = "moodle_ext_courses"
    
    id = Column(String, primary_key=True) # ID Moodle (ex: 1234)
    fullname = Column(String, nullable=False)
    shortname = Column(String, nullable=True)
    last_processed = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class MoodleSyncedFile(Base):
    """Suivi des clés de fichiers Moodle déjà téléchargés/traités."""
    __tablename__ = "moodle_synced_files"
    
    file_key = Column(String, primary_key=True) # Clé unique du fichier Moodle
    synced_at = Column(DateTime(timezone=True), server_default=func.now())

class CloudFile(Base):
    """Suivi universel de la synchronisation des documents sur Google Drive."""
    __tablename__ = "cloud_files"
    
    id = Column(String, primary_key=True, index=True) # Nom du fichier ou UUID
    file_name = Column(String, nullable=False)
    drive_id = Column(String, nullable=True) # ID du fichier sur Google Drive
    local_path = Column(String, nullable=False)
    status = Column(String, default="local") # "local", "synced", "cloud_only"
    file_hash = Column(String, nullable=True) # Pour détection de changement
    last_sync = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Association avec l'utilisateur
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    user = relationship("User", back_populates="documents")

class User(Base):
    """Modèle utilisateur pour NovaFlow."""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    privacy_mode = Column(Boolean, default=True)
    ai_mode = Column(String, default="local") # "local", "openai", "groq"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relations
    tasks = relationship("Task", back_populates="user")
    events = relationship("Event", back_populates="user")
    chat_history = relationship("ChatMessage", back_populates="user")
    documents = relationship("CloudFile", back_populates="user")
