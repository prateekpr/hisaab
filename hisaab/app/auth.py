# app/auth.py
import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status, APIRouter
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from passlib.hash import bcrypt

from app import models, database, crud

# -------------------------
# JWT settings
# -------------------------
SECRET_KEY = "supersecretkey"   # 🔴 replace with env var in production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Router & Logger
router = APIRouter(tags=["auth"])
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


# -------------------------
# Password & Token Helpers
# -------------------------
def verify_password(plain_password, hashed_password):
    return bcrypt.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    logger.debug(f"JWT token created for user={data.get('sub')} exp={expire}")
    return token


# -------------------------
# DB Dependency
# -------------------------
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -------------------------
# Auth Endpoints
# -------------------------
@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    logger.info(f"Login attempt for username={form_data.username}")
    try:
        user = crud.get_user_by_username(db, form_data.username)
        if not user:
            logger.warning(f"Login failed: user not found ({form_data.username})")
            raise HTTPException(status_code=400, detail="Incorrect username or password")

        if not verify_password(form_data.password, user.password_hash):
            logger.warning(f"Login failed: invalid password for {form_data.username}")
            raise HTTPException(status_code=400, detail="Incorrect username or password")

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )
        logger.info(f"Login successful for user={user.username}")
        return {"access_token": access_token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during login for {form_data.username}: {e}")
        raise HTTPException(status_code=500, detail="Login failed due to server error")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            logger.warning("JWT decode failed: 'sub' missing in payload")
            raise credentials_exception
    except JWTError as e:
        logger.warning(f"JWT validation error: {e}")
        raise credentials_exception

    user = crud.get_user_by_username(db, username=username)
    if user is None:
        logger.warning(f"JWT validation failed: user not found ({username})")
        raise credentials_exception

    logger.debug(f"Authenticated user={username}")
    return user
