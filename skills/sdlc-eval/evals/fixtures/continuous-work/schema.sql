CREATE TABLE observations(
    id INTEGER PRIMARY KEY,
    source TEXT NOT NULL,
    external_id TEXT NOT NULL,
    observed_day TEXT NOT NULL,
    amount_cents INTEGER NOT NULL
);
