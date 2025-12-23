from sqlalchemy.orm import Session
from models import User, Book, Loan, Reservation
import hashlib
from datetime import datetime, timedelta

# Авторизація
def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()

def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    if user and user.password_hash == hash_password(password):
        return user
    return None

def get_user(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.user_id == user_id).first()


# Книги
def get_book(db: Session, book_id: int) -> Book | None:
    return db.query(Book).filter(Book.book_id == book_id).first()

# Пошук
def search_books(db: Session, q: str):
    pattern = f"%{q}%"
    return db.query(Book).filter(
        Book.title.like(pattern) |
        Book.author.like(pattern) |
        Book.tags.like(pattern)
    ).all()

# Бронювання
def create_reservation(db: Session, user_id: int, book_id: int, days: int = 7):
    from models import BookStatus

    book = get_book(db, book_id)
    if not book:
        raise ValueError("Книга не знайдена")

    # Перевірка активного бронювання
    active_res = db.query(Reservation).filter(
        Reservation.book_id == book_id,
        Reservation.expiry_date > datetime.utcnow()
    ).first()

    if active_res:
        raise ValueError("Книга вже зарезервована іншим користувачем")

    reservation = Reservation(
        user_id=user_id,
        book_id=book_id,
        expiry_date=datetime.utcnow() + timedelta(days=days)
    )

    if book.status == BookStatus.AVAILABLE:
        book.status = BookStatus.RESERVED

    db.add(reservation)
    db.commit()
    db.refresh(reservation)
    return reservation

# Активні бронювання
def get_user_active_reservations(db: Session, user_id: int):
    return db.query(Reservation).filter(
        Reservation.user_id == user_id,
        Reservation.expiry_date > datetime.utcnow()
    ).all()


# Видача
def get_user_loans(db: Session, user_id: int):
    return db.query(Loan).filter(Loan.user_id == user_id).all()

# Активні видачі
def get_active_loans(db: Session, user_id: int):
    return db.query(Loan).filter(
        Loan.user_id == user_id,
        Loan.return_date.is_(None)
    ).all()

# Подовжити видачу
def extend_loan(db: Session, loan_id: int, days: int = 7):
    loan = db.query(Loan).filter(
        Loan.loan_id == loan_id,
        Loan.return_date.is_(None)
    ).first()

    if not loan:
        raise ValueError("Активна позика не знайдена або вже повернута")

    loan.due_date += timedelta(days=days)
    db.commit()
    db.refresh(loan)
    return loan

# Відмінити бронювання
def cancel_reservation(db: Session, reservation_id: int) -> Reservation | None:
    from models import Reservation, ReservationStatus, Book, BookStatus
    res = db.query(Reservation).filter(Reservation.reservation_id == reservation_id).first()
    if not res:
        return None
    if res.status != ReservationStatus.ACTIVE:
        raise ValueError("Бронювання вже скасовано або завершене")

    # Скасовує бронювання
    res.status = ReservationStatus.CANCELLED

    # Оновлює статус книги. Тобто, якщо вона була reserved, то тепер available
    book = db.query(Book).filter(Book.book_id == res.book_id).first()
    if book and book.status == BookStatus.RESERVED:
        # Перевіряє, чи немає інших активних бронювань на цю книгу
        other_active = db.query(Reservation).filter(
            Reservation.book_id == book.book_id,
            Reservation.reservation_id != reservation_id,
            Reservation.status == ReservationStatus.ACTIVE,
            Reservation.expiry_date > datetime.utcnow()
        ).first()

        if not other_active:
            book.status = BookStatus.AVAILABLE

    db.commit()
    db.refresh(res)
    return res