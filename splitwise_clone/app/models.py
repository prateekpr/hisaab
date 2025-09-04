# app/models.py
import logging
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Table
from .database import Base
from sqlalchemy.orm import relationship
from datetime import datetime

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Association table for many-to-many relation between users and groups
group_members = Table(
    "group_members",
    Base.metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("group_id", Integer, ForeignKey("groups.id")),
    Column("user_id", Integer, ForeignKey("users.id")),
)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(32), unique=True, index=True, nullable=False)
    email = Column(String(64), unique=True, index=True, nullable=False)
    password_hash = Column(String(128), nullable=False)

    expenses_paid = relationship("Expense", back_populates="paid_by")
    expense_shares = relationship("ExpenseShare", back_populates="user")
    groups = relationship("Group", secondary=group_members, back_populates="members")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    description = Column(String(255), nullable=False)
    amount = Column(Float, nullable=False)
    paid_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    paid_by = relationship("User", back_populates="expenses_paid")
    shares = relationship("ExpenseShare", back_populates="expense")
    group = relationship("Group", back_populates="expenses")

    def __repr__(self):
        return f"<Expense(id={self.id}, description='{self.description}', amount={self.amount})>"


class ExpenseShare(Base):
    __tablename__ = "expense_shares"

    id = Column(Integer, primary_key=True, index=True)
    expense_id = Column(Integer, ForeignKey("expenses.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Float, nullable=False)

    expense = relationship("Expense", back_populates="shares")
    user = relationship("User", back_populates="expense_shares")

    def __repr__(self):
        return f"<ExpenseShare(id={self.id}, expense_id={self.expense_id}, user_id={self.user_id}, amount={self.amount})>"


class Group(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    members = relationship("User", secondary=group_members, back_populates="groups")
    expenses = relationship("Expense", back_populates="group")

    def __repr__(self):
        return f"<Group(id={self.id}, name='{self.name}')>"
