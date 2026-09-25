-- Kafka는 at-least-once 전달이므로 동일 스코어 이벤트가 재전송될 수 있다.
-- 기존 중복 행이 있다면 가장 최근 판정만 남긴 뒤, 예매 세션과 리셀 게시물 조합을
-- 최종 판정의 멱등성 키로 승격한다.
DELETE FROM scam_judgments older
USING scam_judgments newer
WHERE older.reservation_session_id = newer.reservation_session_id
  AND older.listing_id = newer.listing_id
  AND (
      older.judged_at < newer.judged_at
      OR (older.judged_at = newer.judged_at AND older.judgment_id < newer.judgment_id)
  );

DROP INDEX IF EXISTS idx_scam_judgments_session_listing;

CREATE UNIQUE INDEX idx_scam_judgments_session_listing
    ON scam_judgments (reservation_session_id, listing_id);
