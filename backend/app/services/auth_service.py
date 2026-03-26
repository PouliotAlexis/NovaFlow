import os
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.db.models import User

from app.core.config import settings

# Configuration
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 24 heures

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    with open("auth_debug.log", "a", encoding="utf-8") as f:
        f.write(f"--- {datetime.now()} ---\nAttempting to decode token\n")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            with open("auth_debug.log", "a", encoding="utf-8") as f: f.write("Email is None in payload\n")
            raise credentials_exception
    except Exception as e:
        with open("auth_debug.log", "a", encoding="utf-8") as f: f.write(f"JWT Decode error: {e}\n")
        raise credentials_exception
        
    with open("auth_debug.log", "a", encoding="utf-8") as f: f.write(f"Searching user for email: {email}\n")
    try:
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            with open("auth_debug.log", "a", encoding="utf-8") as f: f.write("User not found in DB\n")
            raise credentials_exception
        with open("auth_debug.log", "a", encoding="utf-8") as f: f.write(f"User found: {user.id}\n")
        return user
    except Exception as e:
        with open("auth_debug.log", "a", encoding="utf-8") as f: f.write(f"DB Query error: {e}\n")
        raise
