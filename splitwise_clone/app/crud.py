# app/crud.py
import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from passlib.hash import bcrypt
from . import models, schemas

# Logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def create_user(db: Session, user: schemas.UserCreate):
    try:
        logger.info(f"Creating new user: username={user.username}, email={user.email}")
        hashed_pw = bcrypt.hash(user.password)
        db_user = models.User(
            username=user.username,
            email=user.email,
            password_hash=hashed_pw
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        logger.info(f"User created successfully: id={db_user.id}, username={db_user.username}")
        return db_user
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error while creating user {user.username}: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in create_user for {user.username}: {e}")
        raise


def get_user_by_username(db: Session, username: str):
    try:
        logger.debug(f"Fetching user by username={username}")
        return db.query(models.User).filter(models.User.username == username).first()
    except SQLAlchemyError as e:
        logger.error(f"DB error in get_user_by_username for {username}: {e}")
        raise


def get_user_by_email(db: Session, email: str):
    try:
        logger.debug(f"Fetching user by email={email}")
        return db.query(models.User).filter(models.User.email == email).first()
    except SQLAlchemyError as e:
        logger.error(f"DB error in get_user_by_email for {email}: {e}")
        raise
