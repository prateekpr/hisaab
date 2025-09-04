# app/routers/expenses.py
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app import models, schemas, database

router = APIRouter(prefix="/expenses", tags=["expenses"])

# Configure logger for this module
logger = logging.getLogger(__name__)

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/", response_model=schemas.ExpenseOut)
def create_expense(expense: schemas.ExpenseCreate, db: Session = Depends(get_db)):
    try:
        logger.info(f"Creating expense: {expense.dict()}")

        # 1. Validate group
        group = db.query(models.Group).filter(models.Group.id == expense.group_id).first()
        if not group:
            logger.warning(f"Group {expense.group_id} not found")
            raise HTTPException(status_code=404, detail="Group not found")

        # 2. Validate payer
        payer = db.query(models.GroupMember).filter(
            models.GroupMember.group_id == expense.group_id,
            models.GroupMember.user_id == expense.paid_by_id
        ).first()
        if not payer:
            logger.warning(f"Payer {expense.paid_by_id} not in group {expense.group_id}")
            raise HTTPException(status_code=400, detail="Payer is not part of the group")

        # 3. Validate all split_between users
        members = db.query(models.GroupMember.user_id).filter(
            models.GroupMember.group_id == expense.group_id
        ).all()
        member_ids = {m[0] for m in members}
        for user_id in expense.split_between:
            if user_id not in member_ids:
                logger.warning(f"User {user_id} not in group {expense.group_id}")
                raise HTTPException(status_code=400, detail=f"User {user_id} not in group")

        # 4. Create expense
        db_expense = models.Expense(
            description=expense.description,
            amount=expense.amount,
            paid_by_id=expense.paid_by_id,
            group_id=expense.group_id
        )
        db.add(db_expense)
        db.commit()
        db.refresh(db_expense)
        logger.info(f"Expense {db_expense.id} created successfully")

        # 5. Split equally & update balances
        split_amount = expense.amount / len(expense.split_between)
        logger.debug(f"Split amount per user: {split_amount}")

        for user_id in expense.split_between:
            share = models.ExpenseShare(
                expense_id=db_expense.id,
                user_id=user_id,
                amount=split_amount
            )
            db.add(share)

            if user_id != expense.paid_by_id:
                balance = db.query(models.Balance).filter_by(
                    user_id=user_id,
                    owes_to_id=expense.paid_by_id
                ).first()

                if balance:
                    balance.amount += split_amount
                    logger.debug(f"Updated balance: {user_id} owes {expense.paid_by_id} → {balance.amount}")
                else:
                    balance = models.Balance(
                        user_id=user_id,
                        owes_to_id=expense.paid_by_id,
                        amount=split_amount
                    )
                    db.add(balance)
                    logger.debug(f"New balance created: {user_id} owes {expense.paid_by_id} → {split_amount}")

        db.commit()
        db.refresh(db_expense)
        return db_expense

    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error while creating expense: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        logger.error(f"Unexpected error while creating expense: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unexpected error")


@router.get("/", response_model=list[schemas.ExpenseOut])
def get_expenses(db: Session = Depends(get_db)):
    try:
        expenses = db.query(models.Expense).all()
        logger.info(f"Retrieved {len(expenses)} expenses")
        return expenses
    except Exception as e:
        logger.error(f"Error fetching expenses: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not fetch expenses")


@router.get("/group/{group_id}", response_model=list[schemas.ExpenseOut])
def get_group_expenses(group_id: int, db: Session = Depends(get_db)):
    try:
        expenses = db.query(models.Expense).filter(models.Expense.group_id == group_id).all()
        logger.info(f"Retrieved {len(expenses)} expenses for group {group_id}")
        return expenses
    except Exception as e:
        logger.error(f"Error fetching group {group_id} expenses: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not fetch group expenses")


@router.get("/balances/{user_id}")
def get_user_balances(user_id: int, db: Session = Depends(get_db)):
    try:
        balances = db.query(models.Balance).filter(models.Balance.user_id == user_id).all()
        logger.info(f"Retrieved balances for user {user_id}")
        return [{"owes_to": b.owes_to_id, "amount": b.amount} for b in balances]
    except Exception as e:
        logger.error(f"Error fetching balances for user {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not fetch balances")
