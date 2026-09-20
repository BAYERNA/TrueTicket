import unittest

from app.scoring import (
    compute_habitual_score,
    compute_price_anomaly_score,
    compute_seller_repetition_score,
)


class ResaleScoringTest(unittest.TestCase):
    def test_price_at_threshold_is_not_anomaly(self) -> None:
        self.assertEqual(compute_price_anomaly_score(130_000, 100_000), 0.0)

    def test_repeated_high_markup_sales_raise_habitual_score(self) -> None:
        price_score = compute_price_anomaly_score(390_000, 100_000)
        repetition_score = compute_seller_repetition_score(10)

        self.assertEqual(price_score, 1.0)
        self.assertEqual(repetition_score, 1.0)
        self.assertEqual(compute_habitual_score(price_score, repetition_score), 1.0)


if __name__ == "__main__":
    unittest.main()
