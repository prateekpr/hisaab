# app/routers/users.py
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import crud, schemas, database, models
from app.auth import get_current_user

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter()

# Dependency: get DB session
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/", response_model=schemas.UserOut)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    try:
        logger.info(f"Attempting to create user with username={user.username}, email={user.email}")

        db_user_by_username = crud.get_user_by_username(db, user.username)
        if db_user_by_username:
            logger.warning(f"Username already registered: {user.username}")
            raise HTTPException(status_code=400, detail="Username already registered")
        
        db_user_by_email = crud.get_user_by_email(db, user.email)
        if db_user_by_email:
            logger.warning(f"Email already registered: {user.email}")
            raise HTTPException(status_code=400, detail="User email already registered")
        
        new_user = crud.create_user(db, user)
        logger.info(f"User created successfully with ID {new_user.id}")
        return new_user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user {user.username}: {e}")
        raise HTTPException(status_code=500, detail="Failed to create user")


@router.get("/me", response_model=schemas.UserOut)
def read_users_me(current_user: schemas.UserOut = Depends(get_current_user)):
    logger.info(f"Fetching profile for user {current_user.id}")
    return current_user


@router.get("/me/balance")
def get_my_balance(
    db: Session = Depends(get_db),
    current_user: schemas.UserOut = Depends(get_current_user),
):
    logger.info(f"Calculating balances for user {current_user.id}")
    balances = {}
    total_balance = 0.0

    try:
        # Query all groups the user is a member of
        groups = (
            db.query(models.Group)
            .join(models.GroupMember)
            .filter(models.GroupMember.user_id == current_user.id)
            .all()
        )
        logger.info(f"User {current_user.id} is part of {len(groups)} groups")

        for group in groups:
            group_balance = 0.0
            for expense in group.expenses:
                split_amount = expense.amount / len(group.members)
                if expense.payer_id == current_user.id:
                    group_balance += expense.amount - split_amount
                else:
                    group_balance -= split_amount
            balances[group.name] = group_balance
            total_balance += group_balance

        logger.info(f"Balance calculation complete for user {current_user.id}")
        return {
            "user": current_user.username,
            "balances_per_group": balances,
            "total_balance": total_balance,
        }
    except Exception as e:
        logger.error(f"Error calculating balances for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to calculate balances")
