from flask import Flask, request, jsonify, g
from database import engine, SessionLocal
from models import (
    Base, User, Book, Loan, Reservation,
    UserRole, BookStatus, ReservationStatus
)
import hashlib
from datetime import datetime, timedelta

# Імпорти CRUD
from crud.reader import (
    authenticate_user,
    search_books,
    create_reservation,
    get_user_loans,
    get_active_loans,
    get_user_active_reservations,
    extend_loan,
    get_user,
    get_book,
    cancel_reservation
)
from crud.librarian import (
    create_loan,
    return_book,
    create_book,
    update_book,
    delete_book,
    get_all_readers,
    get_reader_loans
)
from crud.admin import (
    create_user,
    get_users,
    update_user,
    delete_user,
    change_user_role,
    get_popular_books,
    get_overdue_loans,
    get_reader_activity
)

app = Flask(__name__)
Base.metadata.create_all(bind=engine)


# Управління сесією бази даних
@app.before_request
def create_db_session():
    g.db = SessionLocal()

@app.teardown_appcontext
def close_db_session(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()


# Допоміжна функція для генерації OTP
def generate_reservation_otp(reservation: Reservation) -> str:
    """
    Генерує 6-значний OTP на основі reservation_id, user_id, book_id та години.
    OTP дійсний протягом 1 години.
    """
    hour_key = int(datetime.utcnow().timestamp() // 3600)
    seed = f"{reservation.reservation_id}{reservation.user_id}{reservation.book_id}{hour_key}"
    hash_val = hashlib.sha256(seed.encode()).hexdigest()
    return str(int(hash_val[:12], 16) % 1000000).zfill(6)


# ===== АВТЕНТИФІКАЦІЯ =====
@app.route("/auth/login", methods=["POST"])
def login():
    db = g.db
    data = request.get_json()
    user = authenticate_user(db, data.get("email"), data.get("password"))
    if not user:
        return jsonify({"error": "Невірний email або пароль"}), 401
    return jsonify({
        "user_id": user.user_id,
        "name": user.name,
        "email": user.email,
        "role": user.role.value
    })


# ===== ЧИТАЧ =====
@app.route("/books/search")
def search_books_route():
    db = g.db
    q = request.args.get("q", "")
    books = search_books(db, q)
    return jsonify([{
        "book_id": b.book_id,
        "title": b.title,
        "author": b.author,
        "status": b.status.value
    } for b in books])


@app.route("/reservations/", methods=["POST"])
def create_reservation_route():
    db = g.db
    data = request.get_json()
    try:
        res = create_reservation(db, data["user_id"], data["book_id"])
        return jsonify({
            "reservation_id": res.reservation_id,
            "book_id": res.book_id,
            "expiry_date": res.expiry_date.isoformat()
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/users/<int:user_id>/loans", methods=["GET"])
def get_user_loans_route(user_id):
    db = g.db
    loans = get_user_loans(db, user_id)
    result = []
    for loan in loans:
        book = get_book(db, loan.book_id)
        result.append({
            "loan_id": loan.loan_id,
            "book_title": book.title,
            "due_date": loan.due_date.isoformat(),
            "return_date": loan.return_date.isoformat() if loan.return_date else None
        })
    return jsonify(result)


@app.route("/users/<int:user_id>/loans/active", methods=["GET"])
def get_user_active_loans_route(user_id):
    db = g.db
    loans = get_active_loans(db, user_id)
    result = []
    for loan in loans:
        book = get_book(db, loan.book_id)
        result.append({
            "loan_id": loan.loan_id,
            "book_title": book.title,
            "due_date": loan.due_date.isoformat()
        })
    return jsonify(result)


@app.route("/users/<int:user_id>/reservations/active", methods=["GET"])
def get_user_active_reservations_route(user_id):
    db = g.db
    reservations = get_user_active_reservations(db, user_id)
    return jsonify([{
        "reservation_id": r.reservation_id,
        "book_id": r.book_id,
        "expiry_date": r.expiry_date.isoformat()
    } for r in reservations])


@app.route("/loans/<int:loan_id>/extend", methods=["POST"])
def extend_loan_route(loan_id):
    db = g.db
    data = request.get_json()
    days = data.get("days", 7)
    try:
        loan = extend_loan(db, loan_id, days)
        return jsonify({
            "loan_id": loan.loan_id,
            "new_due_date": loan.due_date.isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/reservations/<int:reservation_id>/cancel", methods=["POST"])
def cancel_reservation_route(reservation_id):
    db = g.db
    try:
        res = cancel_reservation(db, reservation_id)
        if not res:
            return jsonify({"error": "Бронювання не знайдено"}), 404
        return jsonify({
            "reservation_id": res.reservation_id,
            "status": res.status.value,
            "message": "Бронювання успішно скасовано"
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Внутрішня помилка сервера"}), 500


# ===== БІБЛІОТЕКАР =====
@app.route("/librarian/users", methods=["GET"])
def librarian_get_readers():
    db = g.db
    readers = get_all_readers(db)
    return jsonify([{
        "user_id": u.user_id,
        "name": u.name,
        "email": u.email
    } for u in readers])


@app.route("/librarian/users/<int:user_id>/loans", methods=["GET"])
def librarian_get_reader_loans(user_id):
    db = g.db
    loans = get_reader_loans(db, user_id)
    result = []
    for loan in loans:
        book = get_book(db, loan.book_id)
        result.append({
            "loan_id": loan.loan_id,
            "book_title": book.title,
            "due_date": loan.due_date.isoformat(),
            "return_date": loan.return_date.isoformat() if loan.return_date else None
        })
    return jsonify(result)


@app.route("/librarian/loans/", methods=["POST"])
def librarian_create_loan():
    db = g.db
    data = request.get_json()
    try:
        loan = create_loan(db, data["user_id"], data["book_id"])
        return jsonify({
            "loan_id": loan.loan_id,
            "book_id": loan.book_id,
            "due_date": loan.due_date.isoformat()
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/librarian/loans/<int:loan_id>/return", methods=["POST"])
def librarian_return_loan(loan_id):
    db = g.db
    try:
        loan = return_book(db, loan_id)
        return jsonify({
            "message": "Книга була успішно повернута.",
            "return_date": loan.return_date.isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/librarian/books/", methods=["POST"])
def librarian_create_book():
    db = g.db
    data = request.get_json()
    try:
        book = create_book(db, **data)
        return jsonify({
            "book_id": book.book_id,
            "title": book.title,
            "author": book.author,
            "status": book.status.value
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/librarian/books/<int:book_id>", methods=["PUT"])
def librarian_update_book(book_id):
    db = g.db
    data = request.get_json() or {}
    try:
        book = update_book(db, book_id, **data)
        if not book:
            return jsonify({"error": "Книгу не знайдено"}), 404
        return jsonify({
            "book_id": book.book_id,
            "title": book.title,
            "author": book.author,
            "status": book.status.value
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Внутрішня помилка сервера"}), 500


@app.route("/librarian/books/<int:book_id>", methods=["DELETE"])
def librarian_delete_book(book_id):
    db = g.db
    try:
        success = delete_book(db, book_id)
        if not success:
            return jsonify({"error": "Книгу не знайдено"}), 404
        return jsonify({"message": "Книга видалена"}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Внутрішня помилка сервера"}), 500


# ===== АДМІНІСТРАТОР =====
@app.route("/admin/users/", methods=["POST"])
def admin_create_user():
    db = g.db
    data = request.get_json()
    try:
        user = create_user(db, **data)
        return jsonify({
            "user_id": user.user_id,
            "name": user.name,
            "role": user.role.value
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/admin/users/", methods=["GET"])
def admin_get_all_users():
    db = g.db
    role = request.args.get("role")
    users = get_users(db, role=role)
    return jsonify([{
        "user_id": u.user_id,
        "name": u.name,
        "email": u.email,
        "role": u.role.value
    } for u in users])


@app.route("/admin/users/<int:user_id>", methods=["PUT"])
def admin_update_user(user_id):
    db = g.db
    data = request.get_json() or {}
    try:
        user = update_user(db, user_id, **data)
        if not user:
            return jsonify({"error": "Користувача не знайдено"}), 404
        return jsonify({
            "user_id": user.user_id,
            "name": user.name,
            "email": user.email,
            "phone": user.phone,
            "role": user.role.value
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Внутрішня помилка сервера"}), 500


@app.route("/admin/users/<int:user_id>/role", methods=["PUT"])
def admin_change_role(user_id):
    db = g.db
    data = request.get_json()
    if not data or "role" not in data:
        return jsonify({"error": "Поле 'role' обов'язкове"}), 400

    try:
        user = change_user_role(db, user_id, data["role"])
        if not user:
            return jsonify({"error": "Користувача не знайдено або недійсна роль"}), 400
        return jsonify({
            "user_id": user.user_id,
            "role": user.role.value
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@app.route("/admin/users/<int:user_id>", methods=["DELETE"])
def admin_delete_user(user_id):
    db = g.db
    try:
        success = delete_user(db, user_id)
        if not success:
            return jsonify({"error": "Користувача не знайдено"}), 404
        return jsonify({"message": "Користувач успішно видалений"}), 200
    except Exception as e:
        return jsonify({"error": "Помилка при видаленні користувача: " + str(e)}), 500


@app.route("/admin/reports/popular-books", methods=["GET"])
def admin_popular_books():
    db = g.db
    books = get_popular_books(db)
    return jsonify([{
        "book_id": b.book_id,
        "title": b.title,
        "author": b.author,
        "loan_count": b.loan_count
    } for b in books])


@app.route("/admin/reports/overdue", methods=["GET"])
def admin_overdue_loans():
    db = g.db
    loans = get_overdue_loans(db)
    result = []
    for loan in loans:
        user = get_user(db, loan.user_id)
        book = get_book(db, loan.book_id)
        result.append({
            "user": user.name,
            "email": user.email,
            "book": book.title,
            "due_date": loan.due_date.isoformat()
        })
    return jsonify(result)


@app.route("/admin/reports/reader-activity", methods=["GET"])
def admin_reader_activity():
    db = g.db
    limit = request.args.get("limit", 10, type=int)
    readers = get_reader_activity(db, limit=limit)
    return jsonify([{
        "user_id": r.user_id,
        "name": r.name,
        "email": r.email,
        "loan_count": r.loan_count
    } for r in readers])


@app.route("/users/<int:user_id>", methods=["GET"])
def get_user_route(user_id):
    db = g.db
    user = get_user(db, user_id)
    if not user:
        return jsonify({"error": "Not found"}), 404
    return jsonify({
        "user_id": user.user_id,
        "name": user.name,
        "email": user.email,
        "role": user.role.value
    })


# ===== IoT =====
@app.route("/iot/reservations/<int:reservation_id>/otp", methods=["GET"])
def get_reservation_otp(reservation_id):
    db = g.db
    res = db.query(Reservation).filter(
        Reservation.reservation_id == reservation_id,
        Reservation.status == ReservationStatus.ACTIVE,
        Reservation.expiry_date > datetime.utcnow()
    ).first()

    if not res:
        return jsonify({"error": "Активне бронювання не знайдено"}), 404

    otp = generate_reservation_otp(res)
    return jsonify({
        "reservation_id": res.reservation_id,
        "otp": otp,
        "valid_until": (datetime.utcnow() + timedelta(hours=1)).isoformat()
    })


@app.route("/iot/lockers/unlock", methods=["POST"])
def iot_unlock_locker():
    db = g.db
    data = request.get_json()
    otp_input = data.get("otp")

    if not otp_input or len(otp_input) != 6 or not otp_input.isdigit():
        return jsonify({"error": "OTP має містити 6 цифр"}), 400

    active_reservations = db.query(Reservation).filter(
        Reservation.status == ReservationStatus.ACTIVE,
        Reservation.expiry_date > datetime.utcnow()
    ).all()

    matched_reservation = None
    for res in active_reservations:
        expected_otp = generate_reservation_otp(res)
        if otp_input == expected_otp:
            matched_reservation = res
            break

    if not matched_reservation:
        return jsonify({"error": "Неправильний або прострочений OTP"}), 400

    locker_id = f"A{(matched_reservation.book_id % 5) + 1}"

    return jsonify({
        "locker_id": locker_id,
        "book_id": matched_reservation.book_id,
        "user_id": matched_reservation.user_id
    })


@app.route("/iot/lockers/confirm_pickup", methods=["POST"])
def iot_confirm_pickup():
    db = g.db
    data = request.get_json()
    user_id = data.get("user_id")
    book_id = data.get("book_id")

    if not user_id or not book_id:
        return jsonify({"error": "user_id та book_id обов'язкові"}), 400

    res = db.query(Reservation).filter(
        Reservation.user_id == user_id,
        Reservation.book_id == book_id,
        Reservation.status == ReservationStatus.ACTIVE,
        Reservation.expiry_date > datetime.utcnow()
    ).first()

    if not res:
        return jsonify({"error": "Немає активного бронювання для цієї книги"}), 400

    try:
        loan = create_loan(db, user_id, book_id)
        res.status = ReservationStatus.COMPLETED
        db.commit()
        return jsonify({
            "message": "Книга видана через IoT-поштомат",
            "loan_id": loan.loan_id,
            "due_date": loan.due_date.isoformat()
        })
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 400


@app.route("/iot/loans/return_by_book", methods=["POST"])
def iot_return_by_book():
    db = g.db
    data = request.get_json()
    book_id = data.get("book_id")

    if not book_id:
        return jsonify({"error": "book_id обов'язковий"}), 400

    loan = db.query(Loan).filter(
        Loan.book_id == book_id,
        Loan.return_date.is_(None)
    ).first()

    if not loan:
        return jsonify({"error": "Активна позика для цієї книги не знайдена"}), 404

    try:
        updated_loan = return_book(db, loan.loan_id)
        return jsonify({
            "message": "Книга повернута через поштомат",
            "return_date": updated_loan.return_date.isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ===== ЗАПУСК =====
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)