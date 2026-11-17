import os
import sqlite3
from pathlib import Path

from flask import Flask, flash, g, redirect, render_template, request, url_for


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("FLASK_SECRET_KEY", "local-library-development-key"),
        DATABASE=os.environ.get(
            "LIBRARY_DATABASE", str(Path(app.instance_path) / "library.sqlite")
        ),
    )
    if test_config:
        app.config.update(test_config)

    Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)

    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DATABASE"])
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys = ON")
        return g.db

    @app.teardown_appcontext
    def close_db(_error=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    with app.app_context():
        db = get_db()
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                isbn TEXT NOT NULL UNIQUE,
                total_copies INTEGER NOT NULL CHECK (total_copies > 0),
                available_copies INTEGER NOT NULL
                    CHECK (available_copies >= 0 AND available_copies <= total_copies)
            );
            CREATE TABLE IF NOT EXISTS loans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER NOT NULL REFERENCES books(id),
                borrower TEXT NOT NULL,
                checked_out_at TEXT NOT NULL DEFAULT (datetime('now')),
                returned_at TEXT
            );
            """
        )

    @app.get("/")
    def index():
        db = get_db()
        query = request.args.get("q", "").strip()
        books = db.execute(
            """
            SELECT * FROM books
            WHERE (? = '' OR title LIKE ? OR author LIKE ? OR isbn LIKE ?)
            ORDER BY title COLLATE NOCASE
            """,
            (query, f"%{query}%", f"%{query}%", f"%{query}%"),
        ).fetchall()
        loans = db.execute(
            """
            SELECT loans.id, loans.borrower, loans.checked_out_at,
                   books.title, books.author
            FROM loans JOIN books ON books.id = loans.book_id
            WHERE loans.returned_at IS NULL
            ORDER BY loans.checked_out_at DESC
            """
        ).fetchall()
        stats = db.execute(
            """
            SELECT COUNT(*) AS titles,
                   COALESCE(SUM(total_copies), 0) AS copies,
                   COALESCE(SUM(total_copies - available_copies), 0) AS checked_out
            FROM books
            """
        ).fetchone()
        return render_template(
            "index.html", books=books, loans=loans, stats=stats, query=query
        )

    @app.post("/books")
    def add_book():
        title = request.form.get("title", "").strip()
        author = request.form.get("author", "").strip()
        isbn = request.form.get("isbn", "").strip()
        try:
            copies = int(request.form.get("copies", ""))
        except ValueError:
            copies = 0

        if not title or not author or not isbn or copies < 1:
            flash("Enter a title, author, ISBN, and a copy count of at least one.", "error")
            return redirect(url_for("index"))
        try:
            db = get_db()
            db.execute(
                """
                INSERT INTO books (title, author, isbn, total_copies, available_copies)
                VALUES (?, ?, ?, ?, ?)
                """,
                (title, author, isbn, copies, copies),
            )
            db.commit()
        except sqlite3.IntegrityError:
            flash("That ISBN is already in the catalog.", "error")
            return redirect(url_for("index"))

        flash(f'"{title}" was added to the catalog.', "success")
        return redirect(url_for("index"))

    @app.post("/books/<int:book_id>/checkout")
    def checkout_book(book_id):
        borrower = request.form.get("borrower", "").strip()
        if not borrower:
            flash("Enter the borrower's name before checking out a book.", "error")
            return redirect(url_for("index"))

        db = get_db()
        try:
            db.execute("BEGIN")
            result = db.execute(
                """
                UPDATE books SET available_copies = available_copies - 1
                WHERE id = ? AND available_copies > 0
                """,
                (book_id,),
            )
            if result.rowcount == 0:
                db.rollback()
                flash("No available copies remain for that book.", "error")
                return redirect(url_for("index"))
            db.execute(
                "INSERT INTO loans (book_id, borrower) VALUES (?, ?)",
                (book_id, borrower),
            )
            db.commit()
        except sqlite3.Error:
            db.rollback()
            raise

        flash("Book checked out successfully.", "success")
        return redirect(url_for("index"))

    @app.post("/loans/<int:loan_id>/return")
    def return_book(loan_id):
        db = get_db()
        try:
            db.execute("BEGIN")
            loan = db.execute(
                "SELECT book_id FROM loans WHERE id = ? AND returned_at IS NULL",
                (loan_id,),
            ).fetchone()
            if loan is None:
                db.rollback()
                flash("That loan is already returned or does not exist.", "error")
                return redirect(url_for("index"))
            db.execute(
                "UPDATE loans SET returned_at = datetime('now') WHERE id = ?",
                (loan_id,),
            )
            db.execute(
                "UPDATE books SET available_copies = available_copies + 1 WHERE id = ?",
                (loan["book_id"],),
            )
            db.commit()
        except sqlite3.Error:
            db.rollback()
            raise

        flash("Book returned successfully.", "success")
        return redirect(url_for("index"))

    return app


if __name__ == "__main__":
    create_app().run(debug=os.environ.get("FLASK_DEBUG") == "1")
