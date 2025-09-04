# app/routers/groups.py
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas
from app.auth import get_current_user

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter(prefix="/groups", tags=["groups"])


@router.post("/", response_model=schemas.GroupOut)
def create_group(
    group: schemas.GroupCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    try:
        logger.info(f"User {current_user.id} is creating a group with name '{group.name}'")

        db_group = models.Group(name=group.name, created_by_id=current_user.id)
        db.add(db_group)
        db.commit()
        db.refresh(db_group)

        # Add creator as member
        group_member = models.GroupMember(group_id=db_group.id, user_id=current_user.id)
        db.add(group_member)
        db.commit()

        logger.info(f"Group created successfully with ID {db_group.id}")
        return db_group
    except Exception as e:
        logger.error(f"Error creating group '{group.name}' by user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to create group")


@router.get("/", response_model=list[schemas.GroupOut])
def list_groups(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    try:
        logger.info(f"Fetching groups for user {current_user.id}")
        groups = (
            db.query(models.Group)
            .join(models.GroupMember)
            .filter(models.GroupMember.user_id == current_user.id)
            .all()
        )
        logger.info(f"User {current_user.id} is part of {len(groups)} groups")
        return groups
    except Exception as e:
        logger.error(f"Error fetching groups for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch groups")


@router.get("/{group_id}/expenses", response_model=list[schemas.ExpenseOut])
def get_group_expenses(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    logger.info(f"User {current_user.id} is requesting expenses for group {group_id}")
    group = db.query(models.Group).filter(models.Group.id == group_id).first()
    if not group:
        logger.warning(f"Group {group_id} not found for user {current_user.id}")
        raise HTTPException(status_code=404, detail="Group not found")

    if current_user not in group.members:
        logger.warning(f"Unauthorized access: User {current_user.id} tried accessing group {group_id}")
        raise HTTPException(status_code=403, detail="Not a member of this group")

    logger.info(f"Returning {len(group.expenses)} expenses for group {group_id}")
    return group.expenses


@router.get("/{group_id}/balances")
def get_group_balances(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    logger.info(f"User {current_user.id} is requesting balances for group {group_id}")
    group = db.query(models.Group).filter(models.Group.id == group_id).first()
    if not group:
        logger.warning(f"Group {group_id} not found for user {current_user.id}")
        raise HTTPException(status_code=404, detail="Group not found")

    if current_user not in group.members:
        logger.warning(f"Unauthorized access: User {current_user.id} tried accessing group {group_id}")
        raise HTTPException(status_code=403, detail="Not a member of this group")

    try:
        balances = (
            db.query(models.Balance)
            .join(models.User, models.User.id == models.Balance.user_id)
            .filter(models.Balance.user_id.in_([m.id for m in group.members]))
            .all()
        )
        logger.info(f"Found {len(balances)} balances for group {group_id}")
        return [
            {"user": b.user_id, "owes_to": b.owes_to_id, "amount": b.amount}
            for b in balances
        ]
    except Exception as e:
        logger.error(f"Error fetching balances for group {group_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch balances")
