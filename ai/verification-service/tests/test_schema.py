import unittest

from sqlalchemy import inspect

from app.db import engine


class SchemaTest(unittest.TestCase):
    def test_duplicate_success_guard_exists(self) -> None:
        inspector = inspect(engine)
        self.assertTrue(inspector.has_table("verification_logs"))
        indexes = {
            index["name"]: index
            for index in inspector.get_indexes("verification_logs")
        }
        self.assertIn("ix_verification_logs_reservation_id", indexes)
        self.assertTrue(
            indexes["idx_verification_logs_one_success_per_reservation"]["unique"]
        )


if __name__ == "__main__":
    unittest.main()
