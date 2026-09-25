"""
FR-004/FR-005: 취득 부정성 스코어링.

MVP 1~2주차 로드맵("행동 로그 수집 → 규칙 기반 탐지 → 이후 ML 모델 고도화")에 맞춰
현재는 규칙 기반 휴리스틱으로 스코어를 산출한다. 클릭 간격의 표준편차가 비정상적으로
작을수록(=매크로처럼 균일할수록), 그리고 자동화 도구 흔적이 많을수록 점수가 올라간다.
scikit-learn 기반 모델로 교체할 때는 이 함수의 시그니처만 유지하면 된다.
"""
from __future__ import annotations

import statistics


def compute_rule_based_score(behavior_events: list[dict]) -> float:
    if not behavior_events:
        return 0.0

    click_intervals = [
        e["metadata"]["interval_ms"]
        for e in behavior_events
        if e.get("event_type") == "click" and "interval_ms" in e.get("metadata", {})
    ]
    automation_flags = sum(1 for e in behavior_events if e.get("event_type") == "automation_signature")

    uniformity_score = 0.0
    if len(click_intervals) >= 3:
        mean_interval = statistics.mean(click_intervals)
        stdev_interval = statistics.pstdev(click_intervals)
        if mean_interval > 0:
            coefficient_of_variation = stdev_interval / mean_interval
            # 변동계수가 작을수록(클릭 간격이 기계적으로 균일할수록) 이상 점수가 커진다.
            uniformity_score = max(0.0, 1.0 - min(coefficient_of_variation, 1.0))

    automation_score = min(automation_flags * 0.3, 1.0)

    return round(min(uniformity_score * 0.6 + automation_score * 0.4, 1.0), 4)
