from flask import Flask, request, jsonify
from database import engine, SessionLocal
from models import Base
from crud import *

app = Flask(__name__)
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.route("/users/", methods=["POST"])
def create_user_route():
    db = next(get_db())
    data = request.get_json()
    try:
        user = create_user(db, **data)
        return jsonify({
            "user_id": user.user_id,
            "name": user.name,
            "email": user.email,
            "role": user.role
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/users/<int:user_id>", methods=["GET"])
def get_user_route(user_id):
    db = next(get_db())
    user = get_user(db, user_id)
    if not user:
        return jsonify({"error": "Not found"}), 404
    return jsonify({
        "user_id": user.user_id,
        "name": user.name,
        "email": user.email,
        "role": user.role
    })

@app.route("/books/", methods=["POST"])
def create_book_route():
    db = next(get_db())
    data = request.get_json()
    book = create_book(db, **data)
    return jsonify({
        "book_id": book.book_id,
        "title": book.title,
        "author": book.author,
        "status": book.status
    }), 201

@app.route("/books/search")
def search_books_route():
    db = next(get_db())
    q = request.args.get("q", "")
    books = search_books(db, q)
    return jsonify([{
        "book_id": b.book_id,
        "title": b.title,
        "author": b.author,
        "status": b.status
    } for b in books])

@app.route("/loans/", methods=["POST"])
def create_loan_route():
    db = next(get_db())
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

@app.route("/loans/<int:loan_id>/return", methods=["POST"])
def return_loan_route(loan_id):
    db = next(get_db())
    try:
        loan = return_book(db, loan_id)
        return jsonify({
            "message": "Книга була успішно повернута.",
            "return_date": loan.return_date.isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == "__main__":
    app.run(debug=True)
