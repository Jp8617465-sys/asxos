---
title: M-Thesis-1 Implementation Plan v2
status: amended — system-architect review 2026-05-28
supersedes: (inline plan generated in session, not saved separately)
author: james + claude code
last_updated: 2026-05-28
---

# M-Thesis-1 Implementation Plan — v2

> **v2 changes from v1:** Eleven system-architect review items processed.
> Four CRITICAL schema gaps fixed (last_revisited_at, event-model revisions,
> enter command, SQL injection / type-loss). Six IMPORTANT items accepted or
> escalated. Themes table aligned to Part 6.2 spec (twelfth issue). One
> design fork (theme_holdings linkage) blocked pending James's decision.

---

## 1. Feature Overview

**Problem:** The V2 product's emotional centre is a structured investment
thesis per position. Without the `theses` + `themes` tables and CLI, the
discipline layer — the pre-commitment device in Part 1.3 Layer 2 — does not
exist. There is no way to record *why* you own something, what the plan is,
or when that plan is breaking down.

**Who:** James only. Single-user. `ASXOS_PERSONAL_USE=1` not required for
thesis commands (theses are not portfolio construction outputs), but the
portfolio firewall remains in place for `asx portfolio` commands.

**Key functionality:**
- Open a thesis at `research` or `watching` status with entry band, stop,
  target, timeline, thesis text, and invalidation conditions
- Enter a position (`watching → active`) capturing actual entry price
- Revise any field with a typed audit trail in `thesis_revisions`
- Record deliberate "reviewed, no change" decisions (the discipline event)
- Exit a position with actual exit price
- Attach theses to named themes; maintain theme adjacency
- `asx thesis list` / `asx thesis show` for the morning CLI ritual

**Not in scope:** Brief integration (M-Brief-V2-Sections), opportunity cost
(M-Opportunity-Cost-v1), automated revisit triggers (M-Thesis-Revisit-Engine),
LLM-assisted structuring (M-LLM-Thesis-Structuring), theme stage detection
(M-Theme-Stage-Detection).

---

## 2. Architecture

```
CLI (asx thesis / asx theme)
         │
         ▼
asxos/domain/theses/service.py   asxos/domain/themes/service.py
         │                                   │
         └──────────────┬────────────────────┘
                        ▼
              asyncpg conn.transaction()
                        │
                        ▼
  Supabase Postgres 16 — migration 0012_theses_and_themes.sql
  tables: themes, theses, theme_holdings, thesis_revisions
```

No API routes in M-Thesis-1. The brief reads direct from DB. No REST layer
until a web UI exists.

---

## 3. Database Schema — `migrations/0012_theses_and_themes.sql`

### Design decisions embedded in schema

| Decision | Choice | Ref |
|---|---|---|
| BIGSERIAL not SERIAL | Matches spec Part 6 throughout | Item 11c |
| No FK on `theses.symbol` → `universe` | Watchlist names may not be in universe | Item 7 |
| `theme_holdings.symbol` linkage | **BLOCKED — see §3.4** | Item 8 |
| `timeline_days` not `horizon_months` + `expires_at` | Single source of truth per spec 6.1 | Item 9 |
| `thesis_text` nullable in DB | Research status has no thesis yet | Item 10 |
| `thesis_text` hard-fail in `enter_thesis()` | Cannot enter capital on unarticulated thesis | Item 10 |
| Event model for thesis_revisions | `reviewed_no_change` requires event not field-change | Items 2, 4 |
| `entry_band_lower <= entry_band_upper` CHECK | Domain integrity | Item 5 |
| `exposure_strength NUMERIC(8,6) in [0,1]` | Per spec 6.3; fraction not percent | Items 5, 6 |

### 3.1 — `themes`

Aligned to Part 6.2 + D6 (`adjacent_codes`) + D8 (`stage_suggested`).

```sql
-- ─────────────────────────────────────────────────────────────────────────────
-- themes  (no FK dependencies; create first)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE themes (
    theme_id         BIGSERIAL    PRIMARY KEY,
    theme_code       TEXT         NOT NULL UNIQUE,
    -- slug identifier: 'ai-infrastructure', 'lithium-oversupply-unwinding'
    name             TEXT         NOT NULL,
    description      TEXT         NOT NULL,
    conviction_band  TEXT         NOT NULL DEFAULT 'medium'
                         CHECK (conviction_band IN ('low', 'medium', 'high')),
    stage            TEXT         NOT NULL DEFAULT 'early'
                         CHECK (stage IN ('early', 'early-institutional',
                                          'broad-institutional', 'mainstream',
                                          'late-retail', 'mature')),
    stage_suggested  TEXT                              -- D8: auto-classifier output (M-Theme-Stage-Detection)
                         CHECK (stage_suggested IN ('early', 'early-institutional',
                                                    'broad-institutional', 'mainstream',
                                                    'late-retail', 'mature')),
    adjacent_codes   TEXT[]       NOT NULL DEFAULT '{}',  -- D6: user-maintained adjacency
    started_at       DATE         NOT NULL DEFAULT CURRENT_DATE,
    retired_at       DATE,                            -- NULL = active theme
    last_reviewed_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_themes_code ON themes (theme_code);
```

**Note on stage enum:** Part 6.2 uses 6 stages vs the v1 plan's 4. The spec's
stages are richer ('early-institutional', 'broad-institutional', 'late-retail')
and match the worked-example brief ("late mid-cycle, broad institutional
ownership" for NVDA). Theme retirement is indicated by `retired_at DATE` not a
'retired' status value.

### 3.2 — `theses`

Aligned to Part 6.1 + D2 (watchlist = status='watching') + D3 (add 'research').

```sql
-- ─────────────────────────────────────────────────────────────────────────────
-- theses  (no FK dependency on universe — watchlist names may not be in universe)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE theses (
    thesis_id           BIGSERIAL    PRIMARY KEY,
    symbol              TEXT         NOT NULL,
    -- Validated at service layer: must end with .AU or .US (Item 7)
    -- Intentionally NOT a FK to universe — watchlist may contain unregistered symbols

    status              TEXT         NOT NULL DEFAULT 'watching'
                            CHECK (status IN ('research', 'watching', 'active',
                                              'exited', 'expired')),
    -- D3: 'research' added to spec's original enum

    thesis_text         TEXT,
    -- NULL is valid for research/watching status.
    -- enter_thesis() hard-fails if thesis_text IS NULL OR thesis_text = '' (Item 10)

    entry_band_lower    NUMERIC(18,6),
    entry_band_upper    NUMERIC(18,6),
    CONSTRAINT theses_entry_band_order
        CHECK (entry_band_lower IS NULL OR entry_band_upper IS NULL
               OR entry_band_lower <= entry_band_upper),
    -- Both NULL for research status (no entry plan yet)

    stop_price          NUMERIC(18,6),
    target_price        NUMERIC(18,6),
    -- Nullable: research status may have no price levels yet
    -- enter_thesis() hard-fails if either is NULL

    timeline_days       INTEGER,
    -- Days from opened_at to expected exit. CLI --timeline 18m → 540.
    -- Compute 'day N of M' as: CURRENT_DATE - opened_at::date vs timeline_days
    -- Compute deadline as: opened_at::date + timeline_days
    -- NULL for research status

    -- ⚠️ ESCALATED: stop/target sanity CHECK (stop < entry, target > entry)
    -- Requires knowing whether v1 is long-only (enforce) or allows shorts (defer).
    -- Do not add this constraint until James decides. See §7.

    invalidation_conditions JSONB   NOT NULL DEFAULT '[]'::jsonb,
    -- Array of: {condition: TEXT, status: 'active'|'triggered'|'resolved', note: TEXT|null}
    -- D9: status is manual in v1; M-Thesis-Revisit-Engine automates later

    themes              TEXT[]       NOT NULL DEFAULT '{}',
    -- Denormalised fast-lookup: theme codes attached to this thesis
    -- Kept in sync with theme_holdings at write time

    actual_entry_price  NUMERIC(18,6),   -- set by enter_thesis()
    actual_entry_at     TIMESTAMPTZ,     -- set by enter_thesis()
    actual_exit_price   NUMERIC(18,6),   -- set by exit_thesis()
    actual_exit_at      TIMESTAMPTZ,     -- set by exit_thesis()

    last_revisited_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    -- Updated by: open_thesis, enter_thesis, revise_thesis, exit_thesis,
    --             review_thesis (reviewed_no_change)
    revisit_due_at      TIMESTAMPTZ  NOT NULL DEFAULT (NOW() + INTERVAL '30 days'),
    -- Reset to NOW() + 30 days on every revisit action
    -- M-Thesis-Revisit-Engine makes this dynamic (Part 8.3)

    opened_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    closed_at           TIMESTAMPTZ
    -- Set when status moves to exited or expired
);

CREATE INDEX idx_theses_status_revisit
    ON theses (status, revisit_due_at)
    WHERE status IN ('watching', 'active');
CREATE INDEX idx_theses_symbol ON theses (symbol, opened_at DESC);
```

### 3.3 — `thesis_revisions` (event model)

Aligned to Part 6.4 + Item 2 (event model, `reviewed_no_change`) + Item 4
(diff JSONB, reasoning required).

```sql
-- ─────────────────────────────────────────────────────────────────────────────
-- thesis_revisions  (append-only; every discipline event recorded here)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE thesis_revisions (
    revision_id     BIGSERIAL    PRIMARY KEY,
    thesis_id       BIGINT       NOT NULL REFERENCES theses(thesis_id) ON DELETE CASCADE,
    revised_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    revision_type   TEXT         NOT NULL
                        CHECK (revision_type IN (
                            'opened',
                            'assumption_change',
                            'target_adjusted',
                            'stop_adjusted',
                            'timeline_extended',
                            'reviewed_no_change',  -- Item 2: the discipline event
                            'status_change',
                            'entered',
                            'exited',
                            'exited_by_stop',
                            'exited_by_target',
                            'expired'
                        )),
    diff            JSONB        NOT NULL DEFAULT '{}'::jsonb,
    -- Format: {"field": {"old": "serialised_value", "new": "serialised_value"}, ...}
    -- Decimal values serialised as full-precision strings: Decimal("55.00") → "55.00"
    -- Parse back with Decimal() on read. Never float.
    -- Empty ({}) for reviewed_no_change — no fields changed, only reasoning recorded.
    reasoning       TEXT         NOT NULL,
    -- Required for every revision. reviewed_no_change must state why holding.
    -- 'opened': "Initial thesis" or user's summary of conviction.

    CONSTRAINT thesis_revisions_no_empty_reasoning
        CHECK (reasoning <> '')
);

CREATE INDEX idx_thesis_revisions_thesis
    ON thesis_revisions (thesis_id, revised_at DESC);
```

**Serialisation contract (Item 4):**
All monetary Decimal values in `diff` are serialised as `str(Decimal_value)`
(e.g. `"55.000000"`) and deserialised via `Decimal(str_value)`. Never via
`float()`. Document this in `asxos/domain/theses/service.py` module docstring.

### 3.4 — `theme_holdings` — ⚠️ BLOCKED PENDING JAMES DECISION

**Item 8 ESCALATE:** The plan links `theme_holdings` to `thesis_id`. The V2
spec (Part 6.3) links it to `symbol`. This is a genuine design fork.

**Option A — link to `thesis_id` (plan's choice):**
```sql
CREATE TABLE theme_holdings (
    theme_id        BIGINT    NOT NULL REFERENCES themes(theme_id) ON DELETE CASCADE,
    thesis_id       BIGINT    NOT NULL REFERENCES theses(thesis_id) ON DELETE CASCADE,
    exposure_strength NUMERIC(8,6) NOT NULL
                        CHECK (exposure_strength >= 0 AND exposure_strength <= 1),
    -- fraction in [0,1]; 0.65 means 65% of this thesis attributed to theme
    direction       TEXT      NOT NULL DEFAULT 'positive'
                        CHECK (direction IN ('positive', 'negative')),
    mechanism_text  TEXT      NOT NULL DEFAULT '',
    source          TEXT      NOT NULL DEFAULT 'user'
                        CHECK (source IN ('user', 'llm_inferred', 'system_default')),
    last_validated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    note            TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (theme_id, thesis_id)
);
```
Pros: clean lifecycle coupling, easy active-exposure query.
Cons: loses cross-thesis theme history. "Every thesis I ever held on
ai-infrastructure" requires querying exited theses by theme.

**Option B — link to `symbol` (spec's choice):**
```sql
CREATE TABLE theme_holdings (
    theme_id        BIGINT    NOT NULL REFERENCES themes(theme_id) ON DELETE CASCADE,
    symbol          TEXT      NOT NULL,  -- no FK; watchlist names may not be in universe
    exposure_strength NUMERIC(8,6) NOT NULL
                        CHECK (exposure_strength >= 0 AND exposure_strength <= 1),
    direction       TEXT      NOT NULL DEFAULT 'positive'
                        CHECK (direction IN ('positive', 'negative')),
    mechanism_text  TEXT      NOT NULL DEFAULT '',
    source          TEXT      NOT NULL DEFAULT 'user'
                        CHECK (source IN ('user', 'llm_inferred', 'system_default')),
    last_validated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    note            TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (theme_id, symbol)
);

CREATE INDEX idx_theme_holdings_symbol ON theme_holdings (symbol);
```
Pros: matches spec; theme membership outlives any single thesis; enables
"all theses I ever had on ai-infrastructure" via join through theses.symbol.
Cons: join to compute current exposure needs `WHERE symbol IN (SELECT symbol
FROM theses WHERE status='active')`.

**Reviewer recommendation:** Option B. Matches spec. The cross-thesis history
("every thesis I ever held on ai-infrastructure") becomes useful from the
first portfolio review. The exposure join is a single WHERE clause.

**⚠️ Phase 3 (services + CLI) cannot finalise the `attach_thesis()` function
until this decision is made. Everything else can proceed.**

---

## 4. Implementation Plan

### Phase 1: Database (Day 1 morning — ~3h)

- [ ] Write `migrations/0012_theses_and_themes.sql` (all four tables; use
      Option B for theme_holdings unless James decides Option A)
- [ ] Apply via `mcp__supabase__apply_migration` (project `gxjqezqndltaelmyctnl`)
- [ ] Bump `REQUIRED_MIGRATIONS` in `asxos/api/main.py` from 11 → 12
- [ ] Verify: `SELECT table_name FROM information_schema.tables WHERE
      table_name IN ('theses','themes','theme_holdings','thesis_revisions')`
- [ ] Verify `stage` enum by inserting + rolling back a test row in psql

### Phase 2: Domain types (Day 1 afternoon — ~2h)

Replace M-Thesis-0 stubs entirely.

**`asxos/domain/theses/types.py`:**
```python
from __future__ import annotations
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass(frozen=True)
class InvalidationCondition:
    condition: str
    status: str   # 'active' | 'triggered' | 'resolved'
    note: str | None


@dataclass(frozen=True)
class Thesis:
    thesis_id: int
    symbol: str
    status: str   # 'research' | 'watching' | 'active' | 'exited' | 'expired'
    thesis_text: str | None
    entry_band_lower: Decimal | None
    entry_band_upper: Decimal | None
    stop_price: Decimal | None
    target_price: Decimal | None
    timeline_days: int | None
    invalidation_conditions: tuple[InvalidationCondition, ...]
    themes: tuple[str, ...]           # theme codes (denormalised)
    actual_entry_price: Decimal | None
    actual_entry_at: datetime | None
    actual_exit_price: Decimal | None
    actual_exit_at: datetime | None
    last_revisited_at: datetime
    revisit_due_at: datetime
    opened_at: datetime
    closed_at: datetime | None


@dataclass(frozen=True)
class ThesisRevision:
    revision_id: int
    thesis_id: int
    revised_at: datetime
    revision_type: str
    diff: dict                        # {field: {old: str, new: str}}
    reasoning: str


# Allowlist for revise_thesis() — Item 4
# Maps Python attribute name → SQL column name
REVISABLE_FIELDS: dict[str, str] = {
    "thesis_text":       "thesis_text",
    "entry_band_lower":  "entry_band_lower",
    "entry_band_upper":  "entry_band_upper",
    "stop_price":        "stop_price",
    "target_price":      "target_price",
    "timeline_days":     "timeline_days",
    "status":            "status",
    "invalidation_conditions": "invalidation_conditions",
    "expires_at":        "expires_at",
}

_REVISION_TYPE_FOR_FIELD: dict[str, str] = {
    "thesis_text":       "assumption_change",
    "entry_band_lower":  "assumption_change",
    "entry_band_upper":  "assumption_change",
    "stop_price":        "stop_adjusted",
    "target_price":      "target_adjusted",
    "timeline_days":     "timeline_extended",
    "status":            "status_change",
    "invalidation_conditions": "assumption_change",
}
```

**`asxos/domain/themes/types.py`:**
```python
from __future__ import annotations
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass(frozen=True)
class Theme:
    theme_id: int
    theme_code: str
    name: str
    description: str
    conviction_band: str  # 'low' | 'medium' | 'high'
    stage: str            # 'early'|'early-institutional'|'broad-institutional'|
                          # 'mainstream'|'late-retail'|'mature'
    stage_suggested: str | None   # D8: written by M-Theme-Stage-Detection
    adjacent_codes: tuple[str, ...]  # D6: user-maintained
    started_at: date
    retired_at: date | None
    last_reviewed_at: datetime


@dataclass(frozen=True)
class ThemeHolding:
    theme_id: int
    # thesis_id (Option A) or symbol (Option B) — BLOCKED pending decision
    exposure_strength: Decimal   # fraction in [0,1]
    direction: str               # 'positive' | 'negative'
    mechanism_text: str
    source: str                  # 'user' | 'llm_inferred' | 'system_default'
    last_validated_at: datetime
    note: str | None
```

### Phase 3: Domain services (Day 2 — ~5h)

**`asxos/domain/theses/service.py`**

Module docstring must state:
- Decimal serialisation contract for `diff` JSONB: `str(Decimal_value)`, parse
  back with `Decimal(str_value)`. Never `float()`.
- All multi-statement functions use `async with conn.transaction():`.
- `revise_thesis` uses `REVISABLE_FIELDS` allowlist; never interpolates raw field names.

| Function | Signature | Notes |
|---|---|---|
| `open_thesis` | `(conn, symbol, *, status, thesis_text, entry_band_lower, entry_band_upper, stop_price, target_price, timeline_days, themes, invalidation_conditions) → Thesis` | Validates symbol suffix; inserts thesis + `opened` revision; inserts theme_holdings rows; single transaction |
| `get_thesis` | `(conn, thesis_id: int) → Thesis \| None` | |
| `get_thesis_by_symbol` | `(conn, symbol: str) → Thesis \| None` | Most recent by `opened_at DESC` |
| `list_theses` | `(conn, *, status: str \| None = None) → list[Thesis]` | All if status=None |
| `revise_thesis` | `(conn, thesis_id: int, field: str, value: Any, reasoning: str) → Thesis` | Field must be in `REVISABLE_FIELDS`; hard-fail otherwise; reads old value; writes UPDATE + revision; updates `last_revisited_at`, `revisit_due_at`; transaction |
| `review_thesis` | `(conn, thesis_id: int, reasoning: str) → Thesis` | Writes `reviewed_no_change` revision; updates `last_revisited_at`, `revisit_due_at`; no field change |
| `enter_thesis` | `(conn, thesis_id: int, entry_price: Decimal, qty: int \| None) → Thesis` | Hard-fails if status not in ('watching','research'); hard-fails if thesis_text is None or ''; sets status='active', actual_entry_price, actual_entry_at; writes `entered` revision; transaction |
| `exit_thesis` | `(conn, thesis_id: int, exit_price: Decimal, revision_type: str = 'exited') → Thesis` | Hard-fails if already exited/expired; sets status='exited', actual_exit_price, actual_exit_at, closed_at; writes revision; transaction |

**`asxos/domain/themes/service.py`**

| Function | Notes |
|---|---|
| `create_theme(conn, theme_code, name, description, *, conviction_band, started_at) → Theme` | |
| `get_theme(conn, theme_code: str) → Theme \| None` | |
| `list_themes(conn) → list[Theme]` | Ordered by theme_code |
| `add_adjacency(conn, code_a: str, code_b: str) → None` | Bidirectional: appends code_b to A's array AND code_a to B's array; uses `array_append` with `WHERE NOT (code = ANY(adjacent_codes))` guard; transaction |
| `set_stage(conn, theme_code: str, stage: str, note: str) → Theme` | Writes `themes.stage` (user-confirmed per D8); does NOT touch `stage_suggested` |
| `attach_thesis(conn, theme_code, thesis_id_or_symbol, *, exposure_strength, direction, mechanism_text) → ThemeHolding` | **Signature pending Item 8 decision** |

### Phase 4: CLI commands (Day 2–3 — ~5h)

**`asxos/cli/thesis.py`**

```python
thesis_app = typer.Typer(
    help="Trade thesis management.",
    no_args_is_help=True,
    add_completion=False,
)
```

Commands:

| Command | Signature | Notes |
|---|---|---|
| `asx thesis open SYMBOL` | `--entry "60-65"` `--stop 52` `--target 95` `--timeline 18m` `--themes "code1,code2"` `--thesis TEXT` `--status watching\|research` | Parses `--entry` as `"lo-hi"` or single price; parses `--timeline` as `Nm` or `Nd`; calls `open_thesis()` |
| `asx thesis show [SYMBOL]` | positional optional | Rich table: all fields + invalidation conditions + linked themes |
| `asx thesis list` | `--status` optional | Rich table summary |
| `asx thesis enter SYMBOL` | `--at PRICE` (required) `--qty N` | Calls `enter_thesis()`; hard-fail if already active |
| `asx thesis revise SYMBOL` | `--stop X` `--target X` `--entry "lo-hi"` `--timeline Nm` `--thesis TEXT` `--status S` `--reason TEXT` (required) | One field per invocation; `--reason` required |
| `asx thesis review SYMBOL` | `--reason TEXT` (required) | Alias: `asx thesis hold`; calls `review_thesis()`; writes `reviewed_no_change` |
| `asx thesis exit SYMBOL` | `--at PRICE` (required) `--stop` flag (sets `exited_by_stop`) `--target` flag | Calls `exit_thesis()` |

**`asxos/cli/theme.py`**

```python
theme_app = typer.Typer(
    help="Theme stewardship.",
    no_args_is_help=True,
    add_completion=False,
)
```

| Command | Notes |
|---|---|
| `asx theme create CODE` | `--name` `--description` `--conviction low\|medium\|high` `--started YYYY-MM-DD` |
| `asx theme review CODE` | Rich output: theme metadata + all linked theses (active, watching, research) + adjacencies |
| `asx theme adjacency add CODE_A CODE_B` | Calls `add_adjacency()` |
| `asx theme stage CODE STAGE` | `--note TEXT` (required); calls `set_stage()`; shows diff if `stage_suggested != new stage` |
| `asx theme list` | Summary table: code, stage, stage_suggested (if different), linked thesis count |

**`asxos/cli/main.py` — add 4 lines:**
```python
from asxos.cli.thesis import thesis_app
from asxos.cli.theme import theme_app
app.add_typer(thesis_app, name="thesis")
app.add_typer(theme_app, name="theme")
```

### Phase 5: Tests (Day 3 — ~5h)

**`tests/test_thesis_service.py`** (mock conn, same pattern as
`test_snapshot_portfolio_job.py`):
- `test_open_thesis_happy_path` — row inserted, `opened` revision created
- `test_open_thesis_invalid_symbol_raises` — 'MIN' (no suffix) → ValueError
- `test_open_thesis_invalid_suffix_raises` — 'MIN.ASX' → ValueError
- `test_enter_thesis_sets_active` — status→active, actual_entry_price set
- `test_enter_thesis_no_thesis_text_raises` — hard-fail if thesis_text blank
- `test_enter_thesis_already_active_raises` — hard-fail on double-enter
- `test_revise_thesis_stop` — stop updated, `stop_adjusted` revision written
- `test_revise_thesis_invalid_field_raises` — 'arbitrary_field' → ValueError
- `test_revise_thesis_writes_revision_with_decimal_diff` — old/new are strings parseable as Decimal
- `test_review_thesis_no_field_change` — `reviewed_no_change` revision, last_revisited_at updated
- `test_exit_thesis_sets_exited` — status→exited, actual_exit_price, closed_at set
- `test_exit_thesis_already_exited_raises` — hard-fail

**`tests/test_theme_service.py`:**
- `test_create_theme_inserts_row`
- `test_add_adjacency_bidirectional` — both arrays updated
- `test_set_stage_does_not_touch_stage_suggested`
- `test_add_adjacency_idempotent` — second call does not duplicate

**`tests/test_cli_thesis.py`** (CliRunner):
- `test_thesis_open_watching` — happy path
- `test_thesis_open_research_no_price_levels` — research status, no entry required
- `test_thesis_enter_requires_at_option`
- `test_thesis_review_requires_reason`
- `test_thesis_show_empty` — no theses → graceful message, exit 0

### Phase 6: Docs + deploy (Day 4 — ~2h)

- [ ] Update `CLAUDE.md`: schema ref 11 → 15 tables (theses, themes,
      theme_holdings, thesis_revisions); add backup note for irreplaceable tables
- [ ] Update `scripts/backup_irreplaceable.sh`: add theses, themes,
      theme_holdings, thesis_revisions (per spec Part 6.9)
- [ ] Update `V2_PRODUCT_THESIS_AND_BRIEF_SPEC.md` changelog
- [ ] Commit: `feat(M-Thesis-1): thesis + theme data model and CLI`
- [ ] PR → merge → `make check-drift`

---

## 5. File Changes

**New files:**
```
migrations/0012_theses_and_themes.sql
asxos/domain/theses/service.py
asxos/domain/themes/service.py
asxos/cli/thesis.py
asxos/cli/theme.py
tests/test_thesis_service.py
tests/test_theme_service.py
tests/test_cli_thesis.py
```

**Modified files:**
```
asxos/domain/theses/types.py       (expand stub → full dataclass + REVISABLE_FIELDS)
asxos/domain/themes/types.py       (expand stub → full dataclass + ThemeHolding)
asxos/cli/main.py                  (add thesis_app, theme_app)
asxos/api/main.py                  (REQUIRED_MIGRATIONS 11 → 12)
CLAUDE.md                          (schema ref: 11 → 15 tables)
scripts/backup_irreplaceable.sh    (add 4 new irreplaceable tables)
docs/strategy/V2_PRODUCT_THESIS_AND_BRIEF_SPEC.md  (changelog)
```

---

## 6. Constraints checklist

- [ ] `NUMERIC(18,6)` on every monetary column (`entry_band_lower/upper`,
      `stop_price`, `target_price`, `actual_entry_price`, `actual_exit_price`,
      `exposure_strength` uses `NUMERIC(8,6)`)
- [ ] No `user_id` column anywhere
- [ ] No `float` in domain arithmetic — Decimal only
- [ ] `diff` JSONB serialises Decimal as `str(v)`, parses back with `Decimal(s)`
- [ ] All multi-statement service functions use `async with conn.transaction():`
- [ ] `revise_thesis` uses `REVISABLE_FIELDS` allowlist, never raw interpolation
- [ ] `enter_thesis` hard-fails on: wrong status, NULL/empty thesis_text,
      NULL stop_price, NULL target_price
- [ ] `review_thesis` bumps `last_revisited_at` and `revisit_due_at` without
      changing any thesis field

---

## 7. Escalated decisions (block until resolved)

### ESCALATE A — Stop/target sanity CHECK (Item 5)

**Question:** Is v1 long-only? Should we enforce `stop_price < entry_band_lower`
and `target_price > entry_band_upper`?

**Option 1 — Long-only CHECK (enforce now):**
```sql
CONSTRAINT theses_long_only_sanity
    CHECK (
        (stop_price IS NULL OR entry_band_lower IS NULL OR stop_price < entry_band_lower)
        AND
        (target_price IS NULL OR entry_band_upper IS NULL OR target_price > entry_band_upper)
    )
```
Pros: catches typos at insert time. Cons: cannot represent short thesis later.

**Option 2 — Defer (document, don't enforce):**
Service validates at `open_thesis()` for long-only with a logged WARNING.
CHECK constraint added in a future migration when direction is formalised.

**Reviewer recommendation:** Option 2. V1 is implicitly long-only but the
schema should not bake in that assumption yet. A `direction TEXT` column and
direction-aware CHECK belongs together.

### ESCALATE B — theme_holdings linkage (Item 8)

Already presented in §3.4. Options A (thesis_id) and B (symbol).
**Recommendation: Option B (symbol) — matches spec, preserves history.**

*These two decisions must be made before Phase 3 (services) begins.*

---

## 8. Revised estimate

| Phase | v1 estimate | v2 estimate | Delta |
|---|---|---|---|
| Phase 1 — Migration | 2-3h | 3-4h | +1h (themes table alignment, event model) |
| Phase 2 — Domain types | 1-2h | 2-3h | +1h (REVISABLE_FIELDS, revision type map) |
| Phase 3 — Services | 3-4h | 4-6h | +2h (enter, review, allowlist, transactions) |
| Phase 4 — CLI | 4-5h | 5-6h | +1h (enter, review/hold commands) |
| Phase 5 — Tests | 3-4h | 4-5h | +1h (enter, review, allowlist tests) |
| Phase 6 — Docs | 1-2h | 2-3h | +1h (backup_irreplaceable, portfolio-conventions note) |
| **Total** | **~3 days** | **~4-4.5 days** | **+1-1.5 days** |

---

## 9. Success criteria (amended — Item 11a)

M-Thesis-1 creates and populates the tables. Brief integration is a later
milestone (M-Brief-V2-Sections). CLI is the only reader in this milestone.

- [ ] `asx thesis open MIN.AU --entry 48-53 --stop 42 --target 74 --timeline 18m --thesis "Lithium oversupply unwinds..."` — row in `theses`, `opened` revision in `thesis_revisions`, `last_revisited_at` set
- [ ] `asx thesis enter MIN.AU --at 51.20 --qty 800` — status='active', `actual_entry_price=51.20`, `entered` revision
- [ ] `asx thesis review CSL.AU --reason "Held conviction despite miss; watching Behring margin next Q"` — `reviewed_no_change` revision, `last_revisited_at` bumped, no field change
- [ ] `asx thesis revise MIN.AU --stop 45 --reason "Raised stop after Q3"` — `stop_adjusted` revision, `diff={"stop_price": {"old": "42.000000", "new": "45.000000"}}`
- [ ] `asx thesis exit MIN.AU --at 67.40` — status='exited', `actual_exit_price`, `closed_at` set
- [ ] `asx theme create ai-infrastructure --name "AI Infrastructure" --description "..."` — row in `themes`
- [ ] `asx theme adjacency add ai-infrastructure data-centre-reits` — both arrays updated
- [ ] `revise_thesis(conn, 1, "not_a_field", 99, "test")` → `ValueError`
- [ ] `enter_thesis(conn, 1, ...)` with `thesis_text=None` → `RuntimeError`
- [ ] `pytest tests/test_thesis_service.py tests/test_theme_service.py tests/test_cli_thesis.py` — all green
- [ ] `make check` (ruff + mypy + full suite) — clean
- [ ] `REQUIRED_MIGRATIONS == 12` in `asxos/api/main.py`
- [ ] `theses`, `themes`, `theme_holdings`, `thesis_revisions` in `backup_irreplaceable.sh`

---

## Changelog

| Date | Change |
|---|---|
| 2026-05-28 | v1 — initial plan generated in feature-plan session |
| 2026-05-28 | v2 — system-architect review: 11 items processed. 9 ACCEPTED (Items 1, 2, 3, 4, 6, 7, 9, 10, 11). 2 ESCALATED (Item 5 stop/target sanity, Item 8 theme_holdings linkage). Twelfth issue (themes table schema) folded in. Estimate revised 3d → 4-4.5d. |
