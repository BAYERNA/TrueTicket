import statistics

from .bot_rules import compute_rule_based_score


def bot_score(behavior_events: list[dict]) -> dict:
    score = compute_rule_based_score(behavior_events)
    intervals = [
        event["metadata"]["interval_ms"]
        for event in behavior_events
        if event.get("event_type") == "click" and "interval_ms" in event.get("metadata", {})
    ]
    coefficient_of_variation = None
    if len(intervals) >= 3:
        mean_interval = statistics.mean(intervals)
        if mean_interval > 0:
            coefficient_of_variation = statistics.pstdev(intervals) / mean_interval
    return {
        "score": score,
        "evidence": {
            "click_interval_count": len(intervals),
            "click_interval_cv": coefficient_of_variation,
            "automation_signature_count": sum(
                event.get("event_type") == "automation_signature" for event in behavior_events
            ),
        },
    }
