import unittest

from app.scoring import compute_rule_based_score


class RuleBasedScoringTest(unittest.TestCase):
    def test_uniform_clicks_and_automation_signature_are_high_risk(self) -> None:
        events = [
            {"event_type": "click", "metadata": {"interval_ms": interval}}
            for interval in (100, 100, 100, 100)
        ]
        events.append({"event_type": "automation_signature", "metadata": {}})

        self.assertGreaterEqual(compute_rule_based_score(events), 0.7)

    def test_variable_human_clicks_remain_below_threshold(self) -> None:
        events = [
            {"event_type": "click", "metadata": {"interval_ms": interval}}
            for interval in (80, 240, 510, 920)
        ]

        self.assertLess(compute_rule_based_score(events), 0.7)


if __name__ == "__main__":
    unittest.main()
