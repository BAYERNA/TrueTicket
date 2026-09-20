from prometheus_client import Counter, Histogram

score_histogram = Histogram(
    "trueticket_bot_score", "Distribution of acquisition-fraud scores",
    buckets=(0.1, 0.3, 0.5, 0.7, 0.9, 1.0),
)
flagged_counter = Counter("trueticket_bot_flagged_total", "Sessions flagged by model", ["model_version"])
feedback_counter = Counter("trueticket_bot_feedback_total", "Human review labels", ["model_version", "label"])
