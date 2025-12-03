from sqlalchemy.orm import Session
from models import User, Book, Loan, Reservation
import hashlib
from datetime import datetime

def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def create_user(db: Session, name: str, email: str, password: str, phone: str = None, role: str = "reader"):
    db_user = User(
        name=name,
        email=email,
        password_hash=hash_password(password),
        phone=phone,
        role=role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_user(db: Session, user_id: int):
    return db.query(User).filter(User.user_id == user_id).first()

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def get_users(db: Session, role: str = None):
    q = db.query(User)
    if role:
        q = q.filter(User.role == role)
    return q.all()

def update_user(db: Session, user_id: int, **kwargs):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        return None
    if "password" in kwargs:
        kwargs["password_hash"] = hash_password(kwargs.pop("password"))
    for k, v in kwargs.items():
        setattr(user, k, v)
    db.commit()
    db.refresh(user)
    return user

def delete_user(db: Session, user_id: int) -> bool:
    user = db.query(User).filter(User.user_id == user_id).first()
    if user:
        db.delete(user)
        db.commit()
        return True
    return False

def create_book(db: Session, title: str, author: str, **kwargs):
    book = Book(title=title, author=author, **kwargs)
    db.add(book)
    db.commit()
    db.refresh(book)
    return book

def get_book(db: Session, book_id: int):
    return db.query(Book).filter(Book.book_id == book_id).first()

def search_books(db: Session, q: str):
    pattern = f"%{q}%"
    return db.query(Book).filter(
        Book.title.like(pattern) |
        Book.author.like(pattern) |
        Book.tags.like(pattern)
    ).all()

def update_book(db: Session, book_id: int, **kwargs):
    book = db.query(Book).filter(Book.book_id == book_id).first()
    if book:
        for k, v in kwargs.items():
            setattr(book, k, v)
        db.commit()
        db.refresh(book)
    return book

def delete_book(db: Session, book_id: int) -> bool:
    book = db.query(Book).filter(Book.book_id == book_id).first()
    if book:
        db.delete(book)
        db.commit()
        return True
    return False

def create_loan(db: Session, user_id: int, book_id: int, days: int = 14):
    from models import BookStatus
    book = db.query(Book).filter(Book.book_id == book_id).first()
    if not book or book.status != BookStatus.AVAILABLE:
        raise ValueError("Книга недоступна")
    from datetime import timedelta
    loan = Loan(
        user_id=user_id,
        book_id=book_id,
        due_date=datetime.utcnow() + timedelta(days=days)
    )
    book.status = BookStatus.ISSUED
    db.add(loan)
    db.commit()
    db.refresh(loan)
    return loan

def return_book(db: Session, loan_id: int):
    from models import BookStatus
    loan = db.query(Loan).filter(Loan.loan_id == loan_id).first()
    if not loan or loan.return_date:
        raise ValueError("Книга вже повернута")
    loan.return_date = datetime.utcnow()
    book = db.query(Book).filter(Book.book_id == loan.book_id).first()
    book.status = BookStatus.AVAILABLE
    db.commit()
    db.refresh(loan)
    return loan

def create_reservation(db: Session, user_id: int, book_id: int, days: int = 7):
    from models import BookStatus, ReservationStatus
    book = db.query(Book).filter(Book.book_id == book_id).first()
    if not book:
        raise ValueError("Книга не знайдена")
    from datetime import timedelta
    res = Reservation(
        user_id=user_id,
        book_id=book_id,
        expiry_date=datetime.utcnow() + timedelta(days=days)
    )
    if book.status == BookStatus.AVAILABLE:
        book.status = BookStatus.RESERVED
    db.add(res)
    db.commit()
    db.refresh(res)
    return res
