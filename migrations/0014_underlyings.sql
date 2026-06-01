-- M-Underlyings: commodity/currency/rate dependency tracking per thesis.
--
-- underlyings       — catalog of trackable underlying instruments
-- underlying_prices — daily spot price snapshots (append-friendly; idempotent upsert)
-- thesis_underlyings— many-to-many: thesis ↔ underlying with exposure weighting
--
-- exposure CHECK: row-level [0,1] enforced in DB.
-- exposure sum per thesis: validated at application layer (service.py hard-fails >1.0).

CREATE TABLE underlyings (
    underlying_id  BIGSERIAL PRIMARY KEY,
    code           TEXT UNIQUE NOT NULL,   -- e.g. 'iron_ore_62fe', 'aud_usd'
    name           TEXT NOT NULL,
    category       TEXT NOT NULL CHECK (category IN (
                       'commodity_resources', 'commodity_energy',
                       'commodity_agriculture', 'currency', 'rate', 'index'
                   )),
    unit           TEXT,                   -- e.g. 'USD/t', 'AUD/USD', '%'
    data_source    TEXT,                   -- e.g. 'eodhd:IRON.COMM', 'fred:BAMLH0A0HYM2'
    is_active      BOOLEAN NOT NULL DEFAULT true,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE underlying_prices (
    underlying_id  BIGINT NOT NULL REFERENCES underlyings(underlying_id),
    as_of          DATE NOT NULL,
    spot           NUMERIC(18,6) NOT NULL,
    PRIMARY KEY (underlying_id, as_of)
);

CREATE TABLE thesis_underlyings (
    thesis_id      BIGINT NOT NULL REFERENCES theses(thesis_id),
    underlying_id  BIGINT NOT NULL REFERENCES underlyings(underlying_id),
    exposure       NUMERIC(18,6) NOT NULL CHECK (exposure >= 0 AND exposure <= 1),
    direction      TEXT NOT NULL CHECK (direction IN ('positive', 'negative')),
    last_validated_at DATE,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (thesis_id, underlying_id)
);

CREATE INDEX ON underlying_prices (as_of DESC);
CREATE INDEX ON thesis_underlyings (thesis_id);
