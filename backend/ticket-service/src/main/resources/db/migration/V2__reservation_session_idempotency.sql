-- FR-004에서 프론트가 좌석 선택 세션마다 발급하는 reservationSessionId를 영속화한다.
-- 네트워크 타임아웃 등으로 클라이언트가 동일 요청을 재시도할 때, 이미 처리된 예매를
-- "이미 선점된 좌석"(409)으로 오인하지 않고 원래 예매 건을 그대로 반환하기 위한 멱등성 키.
ALTER TABLE reservations ADD COLUMN reservation_session_id UUID;

CREATE UNIQUE INDEX idx_reservations_session_id ON reservations (reservation_session_id);
