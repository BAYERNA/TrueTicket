CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    venue TEXT NOT NULL,
    date TEXT NOT NULL,
    session_id TEXT NOT NULL,
    session_label TEXT NOT NULL,
    seat_grades TEXT NOT NULL CHECK(json_valid(seat_grades)),
    booking_fee INTEGER NOT NULL CHECK(booking_fee >= 0),
    UNIQUE(id, session_id)
);

CREATE TABLE IF NOT EXISTS accounts (
    account_id TEXT PRIMARY KEY,
    nickname TEXT NOT NULL,
    created_at TEXT NOT NULL,
    group_tag TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS bookings (
    booking_id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    account_id TEXT NOT NULL REFERENCES accounts(account_id),
    seat TEXT NOT NULL,
    grade TEXT NOT NULL,
    price_paid INTEGER NOT NULL CHECK(price_paid >= 0),
    booked_at TEXT NOT NULL,
    behavior_events TEXT NOT NULL CHECK(json_valid(behavior_events)),
    status TEXT NOT NULL,
    UNIQUE(event_id, session_id, seat),
    FOREIGN KEY(event_id, session_id) REFERENCES events(id, session_id)
);

CREATE TABLE IF NOT EXISTS resale_posts (
    post_id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL REFERENCES events(id),
    channel TEXT NOT NULL CHECK(channel IN ('가상 중고거래', '가상 SNS')),
    author_handle TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    price INTEGER CHECK(price >= 0),
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS resale_posts_by_event
    ON resale_posts(event_id, created_at DESC, post_id);

CREATE TABLE IF NOT EXISTS analyses (
    post_id TEXT PRIMARY KEY REFERENCES resale_posts(post_id),
    extracted TEXT CHECK(extracted IS NULL OR json_valid(extracted)),
    confidence REAL,
    matched_booking_id TEXT REFERENCES bookings(booking_id),
    matched_booking_ids TEXT NOT NULL DEFAULT '[]' CHECK(json_valid(matched_booking_ids)),
    bot_score REAL,
    cluster_id TEXT,
    rule_hits TEXT NOT NULL DEFAULT '[]' CHECK(json_valid(rule_hits)),
    risk_level TEXT,
    explanation TEXT,
    details TEXT CHECK(details IS NULL OR json_valid(details)),
    gemini_cache TEXT CHECK(gemini_cache IS NULL OR json_valid(gemini_cache))
);

CREATE TABLE IF NOT EXISTS cases (
    case_id TEXT PRIMARY KEY,
    post_id TEXT NOT NULL UNIQUE REFERENCES resale_posts(post_id),
    status TEXT NOT NULL,
    actions TEXT NOT NULL DEFAULT '[]' CHECK(json_valid(actions))
);

CREATE TABLE IF NOT EXISTS waitlist (
    fan_id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL REFERENCES events(id),
    grade TEXT NOT NULL,
    joined_at TEXT NOT NULL,
    status TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS waitlist_order
    ON waitlist(event_id, grade, status, joined_at, fan_id);

CREATE TABLE IF NOT EXISTS agent_logs (
    id INTEGER PRIMARY KEY,
    run_id TEXT NOT NULL,
    event_id TEXT,
    step TEXT NOT NULL,
    tool TEXT NOT NULL,
    input_summary TEXT NOT NULL CHECK(json_valid(input_summary)),
    output_summary TEXT NOT NULL CHECK(json_valid(output_summary)),
    latency INTEGER NOT NULL CHECK(latency >= 0),
    tokens INTEGER NOT NULL DEFAULT 0 CHECK(tokens >= 0)
);

CREATE INDEX IF NOT EXISTS agent_logs_by_run ON agent_logs(run_id, id);

CREATE TABLE IF NOT EXISTS api_usage (
    day TEXT PRIMARY KEY,
    requests INTEGER NOT NULL DEFAULT 0
);
