CREATE TABLE users (
    user_id       UUID PRIMARY KEY,
    email         VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    name          VARCHAR(100) NOT NULL,
    phone         VARCHAR(30),
    role          VARCHAR(20)  NOT NULL DEFAULT 'USER',
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE events (
    event_id       UUID PRIMARY KEY,
    title          VARCHAR(255) NOT NULL,
    category       VARCHAR(20)  NOT NULL,
    venue          VARCHAR(255) NOT NULL,
    event_datetime TIMESTAMPTZ  NOT NULL,
    base_price     NUMERIC(12, 2) NOT NULL,
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE seats (
    seat_id      UUID PRIMARY KEY,
    event_id     UUID NOT NULL REFERENCES events (event_id),
    seat_section VARCHAR(50) NOT NULL,
    seat_row     VARCHAR(10) NOT NULL,
    seat_number  INT NOT NULL,
    price        NUMERIC(12, 2) NOT NULL,
    status       VARCHAR(20) NOT NULL DEFAULT 'AVAILABLE',
    version      BIGINT NOT NULL DEFAULT 0
);

CREATE INDEX idx_seats_event_status ON seats (event_id, status);

CREATE TABLE reservations (
    reservation_id      UUID PRIMARY KEY,
    user_id              UUID NOT NULL REFERENCES users (user_id),
    event_id             UUID NOT NULL REFERENCES events (event_id),
    seat_id              UUID NOT NULL REFERENCES seats (seat_id),
    reservation_status   VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    qr_code              VARCHAR(64) UNIQUE,
    reserved_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    confirmed_at         TIMESTAMPTZ
);

CREATE UNIQUE INDEX idx_reservations_qr_code ON reservations (qr_code);
CREATE INDEX idx_reservations_user_event ON reservations (user_id, event_id);

CREATE TABLE payments (
    payment_id      UUID PRIMARY KEY,
    reservation_id  UUID NOT NULL UNIQUE REFERENCES reservations (reservation_id),
    amount          NUMERIC(12, 2) NOT NULL,
    payment_method  VARCHAR(50),
    payment_status  VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    paid_at         TIMESTAMPTZ
);
