CREATE TABLE reports (
    report_id         UUID PRIMARY KEY,
    reporter_user_id  UUID NOT NULL,
    target_listing_id UUID,
    report_reason     TEXT NOT NULL,
    report_status     VARCHAR(20) NOT NULL DEFAULT 'RECEIVED',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE notifications (
    notification_id   UUID PRIMARY KEY,
    user_id            UUID NOT NULL,
    notification_type  VARCHAR(30) NOT NULL,
    message             TEXT NOT NULL,
    is_read             BOOLEAN NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- AND 엔진이 두 이벤트를 모두 받을 때까지 부분 상태를 보관하는 조인 버퍼
CREATE TABLE pending_score_joins (
    reservation_session_id UUID PRIMARY KEY,
    listing_id              UUID,
    acquisition_score       DOUBLE PRECISION,
    habitual_score          DOUBLE PRECISION,
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE scam_judgments (
    judgment_id             UUID PRIMARY KEY,
    reservation_session_id  UUID NOT NULL,
    listing_id               UUID,
    acquisition_score        DOUBLE PRECISION NOT NULL,
    habitual_score            DOUBLE PRECISION NOT NULL,
    verdict                    VARCHAR(20) NOT NULL,
    judged_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    reviewed_by                VARCHAR(100)
);

CREATE INDEX idx_scam_judgments_session_listing ON scam_judgments (reservation_session_id, listing_id);
