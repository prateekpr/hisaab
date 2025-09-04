# app/routers/settlements.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas
from app.auth import get_current_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settlements", tags=["settlements"])


@router.post("/", response_model=schemas.ExpenseOut)
def settle_up(
    request: schemas.SettleUpRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Record a settlement payment between two users inside a group.
    Example: User A pays User B ₹500 to settle balance.
    """
    logger.info(
        f"Settlement request: payer={request.payer_id}, "
        f"payee={request.payee_id}, amount={request.amount}, group={request.group_id}"
    )

    if request.amount <= 0:
        logger.warning("Attempted settlement with non-positive amount")
        raise HTTPException(status_code=400, detail="Amount must be positive")

    # Validate group
    group = db.query(models.Group).filter(models.Group.id == request.group_id).first()
    if not group:
        logger.error(f"Group not found: {request.group_id}")
        raise HTTPException(status_code=404, detail="Group not found")

    # Ensure both users are members of the group
    payer_member = (
        db.query(models.GroupMember)
        .filter(
            models.GroupMember.group_id == request.group_id,
            models.GroupMember.user_id == request.payer_id,
        )
        .first()
    )
    payee_member = (
        db.query(models.GroupMember)
        .filter(
            models.GroupMember.group_id == request.group_id,
            models.GroupMember.user_id == request.payee_id,
        )
        .first()
    )

    if not payer_member or not payee_member:
        logger.error("One or both users not in group")
        raise HTTPException(status_code=400, detail="Both users must be in the group")

    # Record settlement as an expense
    settlement_expense = models.Expense(
        description=f"Settlement: User {request.payer_id} paid User {request.payee_id}",
        amount=request.amount,
        paid_by_id=request.payer_id,
        group_id=request.group_id,
    )
    db.add(settlement_expense)
    db.commit()
    db.refresh(settlement_expense)

    # Create expense shares
    payer_share = models.ExpenseShare(
        expense_id=settlement_expense.id,
        user_id=request.payer_id,
        amount=0,
    )
    payee_share = models.ExpenseShare(
        expense_id=settlement_expense.id,
        user_id=request.payee_id,
        amount=-request.amount,  # Negative = reduces how much they’re owed
    )
    db.add_all([payer_share, payee_share])
    db.commit()
    db.refresh(settlement_expense)

    logger.info(f"Settlement recorded successfully (id={settlement_expense.id})")

    return settlement_expense
