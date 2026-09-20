from prometheus_client import Counter, Histogram

score_histogram = Histogram(
    "trueticket_habitual_score", "Distribution of habitual-resale scores",
    buckets=(0.1, 0.3, 0.5, 0.7, 0.9, 1.0),
)
flagged_counter = Counter("trueticket_resale_flagged_total", "Listings flagged by model", ["model_version"])
