"""
FR-007/FR-008: 상습 판매 스코어 = 가격 이상치 + 판매자 반복 게시 패턴을 종합한다.
정식 통계적 이상치 모델(예: IQR, z-score 기반)은 MVP 4주차 크롤링 데이터가 쌓인 뒤
고도화하고, 현재는 정가 대비 배율 기반 규칙으로 시작한다.
"""
from app.config import settings


def compute_price_anomaly_score(listed_price: float, base_price: float) -> float:
    if base_price <= 0:
        return 0.0

    ratio = listed_price / base_price
    if ratio <= settings.price_anomaly_ratio_threshold:
        return 0.0

    # 임계 배율을 넘는 만큼 선형적으로 점수를 올리되 1.0에서 saturate 시킨다.
    excess = ratio - settings.price_anomaly_ratio_threshold
    return round(min(excess / settings.price_anomaly_ratio_threshold, 1.0), 4)


def compute_seller_repetition_score(listing_count: int) -> float:
    # 10회 이상 반복 게시하면 상습성 만점으로 간주한다.
    return round(min(listing_count / 10.0, 1.0), 4)


def compute_habitual_score(price_anomaly_score: float, seller_repetition_score: float) -> float:
    return round(min(price_anomaly_score * 0.5 + seller_repetition_score * 0.5, 1.0), 4)
