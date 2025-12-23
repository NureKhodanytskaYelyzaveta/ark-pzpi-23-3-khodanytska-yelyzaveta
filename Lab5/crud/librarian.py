from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from models import User, Book, Loan, Reservation, BookStatus, ReservationStatus, UserRole

# Створення видачі
def create_loan(db: Session, user_id: int, book_id: int, days: int = 14):
    book = db.query(Book).filter(Book.book_id == book_id).first()
    if not book:
        raise ValueError("Книга не знайдена")
    if book.status == BookStatus.WITHDRAWN:
        raise ValueError("Книга списана і недоступна")
    if book.status == BookStatus.ISSUED:
        raise ValueError("Книга вже видана")

    # Перевірка активного бронювання
    active_res = db.query(Reservation).filter(
        Reservation.book_id == book_id,
        Reservation.expiry_date > datetime.utcnow(),
        Reservation.status == ReservationStatus.ACTIVE
    ).first()

    if active_res and active_res.user_id != user_id:
        raise ValueError("Книга зарезервована іншим користувачем")

    if active_res and active_res.user_id == user_id:
        active_res.status = ReservationStatus.COMPLETED

    loan = Loan(
        user_id=user_id,
        book_id=book_id,
        due_date=datetime.utcnow() + timedelta(days=days)
    )
    db.add(loan)
    book.status = BookStatus.ISSUED
    db.commit()
    db.refresh(loan)
    return loan

# Повернення книги
def return_book(db: Session, loan_id: int):
    loan = db.query(Loan).filter(Loan.loan_id == loan_id).first()
    if not loan:
        raise ValueError("Позика не знайдена")
    if loan.return_date:
        raise ValueError("Книга вже повернута")

    loan.return_date = datetime.utcnow()
    book = loan.book

    # Перевірка наявності наступного бронювання
    next_res = db.query(Reservation).filter(
        Reservation.book_id == book.book_id,
        Reservation.expiry_date > datetime.utcnow(),
        Reservation.status == ReservationStatus.ACTIVE
    ).order_by(Reservation.reservation_date.asc()).first()

    if next_res:
        book.status = BookStatus.RESERVED
    else:
        book.status = BookStatus.AVAILABLE

    db.commit()
    db.refresh(loan)
    return loan

# Створення книги
def create_book(db: Session, title: str, author: str, **kwargs):
    book = Book(title=title, author=author, **kwargs)
    db.add(book)
    db.commit()
    db.refresh(book)
    return book

# Оновлення інформації по книзі
def update_book(db: Session, book_id: int, **kwargs):
    from models import BookStatus, BookCondition
    book = db.query(Book).filter(Book.book_id == book_id).first()
    if not book:
        return None

    # Обробка енамів
    if "status" in kwargs:
        try:
            kwargs["status"] = BookStatus(kwargs["status"])
        except ValueError:
            raise ValueError(f"Недійсний статус. Дозволені значення: {[s.value for s in BookStatus]}")

    if "condition" in kwargs:
        try:
            kwargs["condition"] = BookCondition(kwargs["condition"])
        except ValueError:
            raise ValueError(f"Недійсний стан книги. Дозволені значення: {[c.value for c in BookCondition]}")

    # Оновлення інших полів
    for key, value in kwargs.items():
        if hasattr(book, key):
            setattr(book, key, value)
        else:
            raise ValueError(f"Поле '{key}' не існує в моделі Book")

    db.commit()
    db.refresh(book)
    return book

# Видалення книги
def delete_book(db: Session, book_id: int) -> bool:
    book = db.query(Book).filter(Book.book_id == book_id).first()
    if not book:
        return False
    if book.status != BookStatus.WITHDRAWN:
        raise ValueError("Можна видаляти лише списані книги (статус 'withdrawn')")
    db.delete(book)
    db.commit()
    return True

# Отримати інформацію по всіх користувачах
def get_all_readers(db: Session):
    return db.query(User).filter(User.role == UserRole.READER).all()

# Отримати інформацію про видачі
def get_reader_loans(db: Session, user_id: int):
    return db.query(Loan).filter(Loan.user_id == user_id).all()