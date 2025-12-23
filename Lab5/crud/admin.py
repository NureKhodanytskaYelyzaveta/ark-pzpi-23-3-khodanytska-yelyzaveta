from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from models import User, Book, Loan, UserRole
from crud.reader import hash_password

# Створення користувача
def create_user(
    db: Session,
    name: str,
    email: str,
    password: str,
    phone: str = None,
    role: UserRole = UserRole.READER
):
    if db.query(User).filter(User.email == email).first():
        raise ValueError("Користувач з таким email уже існує")

    user = User(
        name=name,
        email=email,
        password_hash=hash_password(password),
        phone=phone,
        role=role
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

# Отримання списку користувачів
def get_users(db: Session, role: UserRole = None):
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    return query.all()

# Оновлення користувача
def update_user(db: Session, user_id: int, **kwargs):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        return None

    # Обробка зміни пароля
    if "password" in kwargs:
        kwargs["password_hash"] = hash_password(kwargs.pop("password"))

    # Обробка зміни ролі
    if "role" in kwargs:
        role = kwargs["role"]
        if isinstance(role, str):
            try:
                role = UserRole(role)
            except ValueError:
                raise ValueError("Недійсна роль користувача")
        kwargs["role"] = role

    for key, value in kwargs.items():
        setattr(user, key, value)

    db.commit()
    db.refresh(user)
    return user

# Видалення користувача
def delete_user(db, user_id):
    user = db.query(User).filter(User.user_id == user_id).first()
    if user:
        db.delete(user)
        db.commit()
        return True
    return False

# Зміна ролі користувача
def change_user_role(db: Session, user_id: int, new_role: str):
    try:
        new_role_enum = UserRole(new_role)
    except ValueError:
        raise ValueError("Недійсна роль користувача")

    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        return None

    user.role = new_role_enum
    db.commit()
    db.refresh(user)
    return user

# Топ популярних книг
def get_popular_books(db: Session, limit: int = 10):
    return (
        db.query(
            Book.book_id,
            Book.title,
            Book.author,
            func.count(Loan.loan_id).label("loan_count")
        )
        .join(Loan, Book.book_id == Loan.book_id)
        .group_by(Book.book_id)
        .order_by(func.count(Loan.loan_id).desc())
        .limit(limit)
        .all()
    )

# Прострочені позики
def get_overdue_loans(db: Session):
    return (
        db.query(Loan)
        .filter(
            Loan.return_date.is_(None),
            Loan.due_date < datetime.utcnow()
        )
        .all()
    )

# Активність читачів
def get_reader_activity(db: Session, limit: int = 10):
    return (
        db.query(
            User.user_id,
            User.name,
            User.email,
            func.count(Loan.loan_id).label("loan_count")
        )
        .join(Loan, User.user_id == Loan.user_id)
        .filter(User.role == UserRole.READER)
        .group_by(User.user_id)
        .order_by(func.count(Loan.loan_id).desc())
        .limit(limit)
        .all()
    )