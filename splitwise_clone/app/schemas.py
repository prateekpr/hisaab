import logging
from typing import List, Optional
from pydantic import BaseModel, EmailStr, ValidationError
from pydantic import ConfigDict

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# -------------------------
# Base class with logging on validation errors
# -------------------------
class LoggedModel(BaseModel):
    """Base Pydantic model with error logging."""

    def __init__(self, **data):
        try:
            super().__init__(**data)
        except ValidationError as e:
            logger.error(f"Schema validation error in {self.__class__.__name__}: {e.errors()}")
            raise

    def __repr__(self):
        return f"<{self.__class__.__name__}({self.dict(exclude_none=True)})>"


# -------------------------
# User Schemas
# -------------------------
class UserCreate(LoggedModel):
    username: str
    email: EmailStr
    password: str


class UserOut(LoggedModel):
    id: int
    username: str
    email: EmailStr

    model_config = ConfigDict(from_attributes=True)


# -------------------------
# Expense Schemas
# -------------------------
class ExpenseShareBase(LoggedModel):
    user_id: int
    amount: float


class ExpenseShareCreate(ExpenseShareBase):
    pass


class ExpenseShareOut(ExpenseShareBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class ExpenseBase(LoggedModel):
    description: str
    amount: float
    paid_by_id: int
    group_id: Optional[int] = None


class ExpenseCreate(ExpenseBase):
    split_between: List[int]  # user IDs who share expense


class ExpenseOut(ExpenseBase):
    id: int
    shares: List[ExpenseShareOut]

    model_config = ConfigDict(from_attributes=True)


# -------------------------
# Group Schemas
# -------------------------
class GroupBase(LoggedModel):
    name: str


class GroupCreate(GroupBase):
    member_ids: List[int]


class GroupOut(GroupBase):
    id: int
    created_by_id: int
    members: List[UserOut]

    model_config = ConfigDict(from_attributes=True)


# -------------------------
# Balance & SettleUp
# -------------------------
class BalanceOut(LoggedModel):
    user_id: int
    username: str
    balance: float   # positive = owed to them, negative = they owe others

    model_config = ConfigDict(from_attributes=True)


class SettleUpRequest(LoggedModel):
    group_id: int
    payer_id: int
    payee_id: int
    amount: float
