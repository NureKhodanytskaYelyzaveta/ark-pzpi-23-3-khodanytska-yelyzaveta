from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base
from enum import Enum

class UserRole(str, Enum):
    READER = "reader"
    LIBRARIAN = "librarian"
    ADMIN = "admin"

class BookStatus(str, Enum):
    AVAILABLE = "available"
    ISSUED = "issued"
    RESERVED = "reserved"
    WITHDRAWN = "withdrawn"

class BookCondition(str, Enum):
    NEW = "new"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"

class ReservationStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"

class User(Base):
    __tablename__ = "users"
    user_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    phone = Column(String(20))
    role = Column(SQLEnum(UserRole), default=UserRole.READER, nullable=False)
    loans = relationship("Loan", back_populates="user", cascade="all, delete-orphan")
    reservations = relationship("Reservation", back_populates="user", cascade="all, delete-orphan")

class Book(Base):
    __tablename__ = "books"
    book_id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    author = Column(String(100), nullable=False)
    category = Column(String(50))
    isbn = Column(String(20), unique=True)
    condition = Column(SQLEnum(BookCondition), default=BookCondition.GOOD)
    status = Column(SQLEnum(BookStatus), default=BookStatus.AVAILABLE, nullable=False)
    location = Column(String(100))
    tags = Column(String(200))
    loans = relationship("Loan", back_populates="book", cascade="all, delete-orphan")
    reservations = relationship("Reservation", back_populates="book", cascade="all, delete-orphan")

class Loan(Base):
    __tablename__ = "loans"
    loan_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    book_id = Column(Integer, ForeignKey("books.book_id"), nullable=False)
    issue_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    due_date = Column(DateTime, nullable=False)
    return_date = Column(DateTime)
    user = relationship("User", back_populates="loans")
    book = relationship("Book", back_populates="loans")

class Reservation(Base):
    __tablename__ = "reservations"
    reservation_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    book_id = Column(Integer, ForeignKey("books.book_id"), nullable=False)
    reservation_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    expiry_date = Column(DateTime, nullable=False)
    status = Column(SQLEnum(ReservationStatus), default=ReservationStatus.ACTIVE, nullable=False)
    user = relationship("User", back_populates="reservations")
    book = relationship("Book", back_populates="reservations")
