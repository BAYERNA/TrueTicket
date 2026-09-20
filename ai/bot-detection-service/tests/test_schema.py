import unittest

from sqlalchemy import inspect

from app.db import engine


class SchemaTest(unittest.TestCase):
    def test_required_tables_and_indexes_exist(self) -> None:
        inspector = inspect(engine)
        self.assertTrue(inspector.has_table("behavior_logs"))
        self.assertTrue(inspector.has_table("bot_scores"))
        self.assertIn(
            "ix_behavior_logs_reservation_session_id",
            {index["name"] for index in inspector.get_indexes("behavior_logs")},
        )
        self.assertIn(
            "ix_bot_scores_reservation_session_id",
            {index["name"] for index in inspector.get_indexes("bot_scores")},
        )


if __name__ == "__main__":
    unittest.main()
