ALTER TABLE reservations
    ADD COLUMN expires_at TIMESTAMPTZ,
    ADD COLUMN cancelled_at TIMESTAMPTZ;

UPDATE reservations
SET expires_at = COALESCE(confirmed_at, reserved_at + INTERVAL '5 minutes');

ALTER TABLE reservations ALTER COLUMN expires_at SET NOT NULL;
CREATE INDEX idx_reservations_status_expires ON reservations (reservation_status, expires_at);

ALTER TABLE payments
    ADD COLUMN idempotency_key UUID,
    ADD COLUMN provider_payment_id VARCHAR(100),
    ADD COLUMN webhook_event_id VARCHAR(100),
    ADD COLUMN failure_reason VARCHAR(255),
    ADD COLUMN created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    ADD COLUMN updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

UPDATE payments
SET idempotency_key = gen_random_uuid(),
    provider_payment_id = 'legacy_' || payment_id::text;

ALTER TABLE payments ALTER COLUMN idempotency_key SET NOT NULL;
ALTER TABLE payments ALTER COLUMN provider_payment_id SET NOT NULL;
CREATE UNIQUE INDEX idx_payments_idempotency_key ON payments (idempotency_key);
CREATE UNIQUE INDEX idx_payments_provider_payment_id ON payments (provider_payment_id);
CREATE UNIQUE INDEX idx_payments_webhook_event_id ON payments (webhook_event_id) WHERE webhook_event_id IS NOT NULL;
