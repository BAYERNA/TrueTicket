import unittest

from sqlalchemy import inspect

from app.db import engine


class SchemaTest(unittest.TestCase):
    def test_required_tables_and_query_indexes_exist(self) -> None:
        inspector = inspect(engine)
        self.assertTrue(inspector.has_table("sellers"))
        self.assertTrue(inspector.has_table("resale_listings"))
        self.assertIn(
            "idx_sellers_habitual_score",
            {index["name"] for index in inspector.get_indexes("sellers")},
        )
        self.assertIn(
            "idx_resale_listings_event_price",
            {index["name"] for index in inspector.get_indexes("resale_listings")},
        )


if __name__ == "__main__":
    unittest.main()
