from contextlib import closing
import tempfile
import sqlite3
import unittest
from pathlib import Path

from app import create_app


class LibraryAppTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test-key",
                "DATABASE": str(Path(self.temp_dir.name) / "library.sqlite"),
            }
        )
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def add_book(self, title="The Left Hand of Darkness", copies="1"):
        return self.client.post(
            "/books",
            data={
                "title": title,
                "author": "Ursula K. Le Guin",
                "isbn": "9780441478125" if title == "The Left Hand of Darkness" else "9780000000001",
                "copies": copies,
            },
            follow_redirects=True,
        )

    def database_value(self, query):
        with closing(sqlite3.connect(self.app.config["DATABASE"])) as db:
            return db.execute(query).fetchone()[0]

    def test_add_and_search_catalog(self):
        self.add_book()
        response = self.client.get("/?q=darkness")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"The Left Hand of Darkness", response.data)
        self.assertIn(b"1 / 1", response.data)

    def test_rejects_duplicate_isbn_and_invalid_copy_count(self):
        self.add_book()
        response = self.client.post(
            "/books",
            data={
                "title": "Another Book",
                "author": "A. Writer",
                "isbn": "9780441478125",
                "copies": "2",
            },
            follow_redirects=True,
        )
        self.assertIn(b"That ISBN is already in the catalog.", response.data)
        response = self.client.post(
            "/books",
            data={"title": "No Copies", "author": "A. Writer", "isbn": "unique", "copies": "0"},
            follow_redirects=True,
        )
        self.assertIn(b"copy count of at least one", response.data)

    def test_checkout_and_return_restore_availability(self):
        self.add_book()
        book_id = self.database_value("SELECT id FROM books")

        response = self.client.post(
            f"/books/{book_id}/checkout", data={"borrower": "Alex"}, follow_redirects=True
        )
        self.assertIn(b"0 / 1", response.data)
        self.assertIn(b"Alex", response.data)
        exhausted = self.client.post(
            f"/books/{book_id}/checkout",
            data={"borrower": "Sam"},
            follow_redirects=True,
        )
        self.assertIn(b"No available copies remain", exhausted.data)

        loan_id = self.database_value("SELECT id FROM loans")
        response = self.client.post(f"/loans/{loan_id}/return", follow_redirects=True)
        self.assertIn(b"1 / 1", response.data)
        self.assertIn(b"No books are currently checked out.", response.data)


if __name__ == "__main__":
    unittest.main()
