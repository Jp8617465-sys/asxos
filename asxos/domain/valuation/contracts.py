"""Persisted valuation artifacts — `ScenarioPreregistration` and `ValuationRun`.

Both subclass `ContentAddressedContract` (`decision_engine/types.py`): frozen,
`extra="forbid"`, float input refused, `content_hash` sealed on construction
and verified when supplied. The whole model is the `payload JSONB` of migration
0054; every other column on `valuation_runs` / `valuation_scenario_preregistrations`
is a NON-AUTHORITATIVE shadow for indexing (same rule as `decision_engine/repository.py`).

Why one row per symbol carries BOTH conventions (decision, F-E2E r2 S1, 2026-09-16)
----------------------------------------------------------------------------------
Migration 0054's `terminal_convention` CHECK admits only `zero_excess`, and the
scenario pre-registration's standing pre-commitment says the fading-excess
convention is a COMPARISON, never a declared basis for a value. A row declared
under `fading_excess` would therefore claim a provenance nothing has registered.
So the registered convention is the row's discriminator and the fading-excess
value (w = 0.5), the 3-period-average-ROE value and the Ke-band values travel
INSIDE the row as labelled `sensitivities` — present from row one, so hash
continuity holds if a later ADR registers a second convention and widens the
CHECK (the payload field simply stays). `residual_income.py`'s "both are ALWAYS
run" holds: every valued row computes both.

Blocked rows are rows (0054 header): `outcome="blocked"`, no value, at least one
named gap, so a symbol the model could not value is a record, not an absence.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Self

from pydantic import Field, model_validator

from asxos.domain.decision_engine.types import ContentAddressedContract, Contract, DataMode

ValuationMethod = Literal["residual_income"]
#: The conventions the store admits. Widening this Literal is an ADR plus a
#: migration that widens 0054's CHECK — never a code-only change.
RegisteredTerminalConvention = Literal["zero_excess"]
FrankingConvention = Literal["pre_tax_no_franking_adjustment", "grossed_up_resident"]
ReturnBase = Literal["tangible_common_equity", "reported_book_equity"]
ValuationOutcome = Literal["valued", "blocked"]
ScenarioLabel = Literal["bear", "base", "bull"]

_ONE_HUNDRED = Decimal("100")


# --- pre-registration --------------------------------------------------------


class ScenarioLever(Contract):
    """A multiplicative lever on each name's own measured ROE — symbol-agnostic."""

    label: ScenarioLabel
    probability_pct: Decimal = Field(ge=0, le=100)
    roe_factor: Decimal = Field(gt=0)
    rationale: str = Field(min_length=1, max_length=2_000)


class Sensitivity(Contract):
    """A figure computed ALONGSIDE the registered value, never in place of it."""

    label: str = Field(min_length=1, max_length=80)
    parameter: str = Field(min_length=1, max_length=200)
    registered: Literal[False] = False
    rationale: str = Field(min_length=1, max_length=2_000)


class KeTreatment(Contract):
    erp: Decimal = Field(gt=0)
    beta_low: Decimal = Field(ge=0)
    beta_mid: Decimal = Field(ge=0)
    beta_high: Decimal = Field(ge=0)
    beta_provenance: str = Field(min_length=1, max_length=1_000)
    risk_free_series: str = Field(min_length=1, max_length=200)
    sensitivity_note: str = Field(min_length=1, max_length=2_000)

    @model_validator(mode="after")
    def validate_band_is_ordered(self) -> Self:
        if not self.beta_low <= self.beta_mid <= self.beta_high:
            raise ValueError("beta band must be ordered low <= mid <= high")
        return self


class InputRules(Contract):
    """How the sweep reads its inputs, written down before the first run."""

    universe: str = Field(min_length=1, max_length=500)
    pit_selection: str = Field(min_length=1, max_length=1_000)
    price_window_days: int = Field(ge=1, le=365)
    usd_conversion: str = Field(min_length=1, max_length=1_000)
    currency_unverified_policy: str = Field(min_length=1, max_length=1_000)
    payout_rule: str = Field(min_length=1, max_length=1_000)
    franking_rule: str = Field(min_length=1, max_length=1_000)
    roe_average_periods: int = Field(ge=1, le=10)


class ScenarioPreregistration(ContentAddressedContract):
    preregistration_id: str = Field(min_length=1, max_length=200)
    registered_by: str = Field(min_length=1, max_length=200)
    registered_at: datetime
    applies_to: str = Field(min_length=1, max_length=1_000)
    method: ValuationMethod
    return_base: ReturnBase
    terminal_convention: RegisteredTerminalConvention
    franking_convention: FrankingConvention
    horizon_years: int = Field(ge=1, le=30)
    symbol_agnostic: Literal[True]
    committed_before_any_model_run: Literal[True]
    levers: tuple[ScenarioLever, ...] = Field(min_length=1, max_length=10)
    sensitivities: tuple[Sensitivity, ...] = Field(max_length=10)
    ke_treatment: KeTreatment
    input_rules: InputRules
    evidence_basis: str = Field(min_length=1, max_length=4_000)
    pre_commitment: str = Field(min_length=1, max_length=4_000)

    @model_validator(mode="after")
    def validate_levers(self) -> Self:
        labels = [lever.label for lever in self.levers]
        if len(set(labels)) != len(labels):
            raise ValueError("scenario lever labels must be unique")
        total = sum((lever.probability_pct for lever in self.levers), Decimal(0))
        if total != _ONE_HUNDRED:
            raise ValueError(f"scenario probabilities must sum to exactly 100, got {total}")
        sensitivity_labels = [s.label for s in self.sensitivities]
        if len(set(sensitivity_labels)) != len(sensitivity_labels):
            raise ValueError("sensitivity labels must be unique")
        return self


# --- a run -------------------------------------------------------------------


class KeBand(Contract):
    """Ke as a stated band over the cited beta band — never a measured point."""

    risk_free: Decimal = Field(ge=0)
    risk_free_as_of: date
    risk_free_series: str = Field(min_length=1, max_length=200)
    erp: Decimal = Field(gt=0)
    beta_low: Decimal = Field(ge=0)
    beta_mid: Decimal = Field(ge=0)
    beta_high: Decimal = Field(ge=0)
    beta_provenance: str = Field(min_length=1, max_length=1_000)
    ke_low: Decimal = Field(gt=0)
    ke_mid: Decimal = Field(gt=0)
    ke_high: Decimal = Field(gt=0)

    @model_validator(mode="after")
    def validate_ordering(self) -> Self:
        if not self.ke_low <= self.ke_mid <= self.ke_high:
            raise ValueError("ke band must be ordered low <= mid <= high")
        return self


class ValuationInputs(Contract):
    """Every input the model consumed for one name, as read at the cutoff."""

    pit_as_of: date
    pit_knowledge_date: date
    reporting_currency: str | None = Field(default=None, max_length=10)
    currency_verified: bool
    #: The AUDUSD rate, populated ONLY for a USD reporter. Retained with its
    #: original meaning rather than renamed to something general: `payload` is
    #: content-addressed and append-only (0054), and a consumer reading
    #: `fx_audusd` must never start receiving an NZD rate under that name.
    #: `fx_rate`/`fx_pair` below are the general form — read those.
    fx_audusd: Decimal | None = Field(default=None, gt=0)
    fx_as_of: date | None = None
    #: The AUD-base pair actually used (`AUDUSD`, `AUDNZD`, …) and its rate, in
    #: the quoted currency's units per one AUD. Both None when the reporter is
    #: already in AUD. `fx_as_of` is shared: it dates whichever rate was used.
    fx_pair: str | None = Field(default=None, min_length=6, max_length=6)
    fx_rate: Decimal | None = Field(default=None, gt=0)
    book_value_ps_native: Decimal = Field(gt=0)
    book_value_ps_aud: Decimal = Field(gt=0)
    roe_trailing: Decimal = Field(gt=0)
    roe_average: Decimal | None = None
    roe_periods: int = Field(ge=1)
    eps_ttm: Decimal | None = None
    dividend_ttm_native: Decimal | None = None
    dividend_ttm_aud: Decimal | None = None
    payout_ratio: Decimal = Field(ge=0, le=1)
    payout_clipped: bool
    franking_pct: Decimal = Field(ge=0, le=100)
    last_close: Decimal = Field(gt=0)
    last_close_dt: date

    @model_validator(mode="after")
    def validate_dates(self) -> Self:
        if self.pit_knowledge_date < self.pit_as_of:
            raise ValueError("pit_knowledge_date cannot precede pit_as_of")
        if (self.fx_rate is None) != (self.fx_as_of is None):
            raise ValueError("fx_rate and fx_as_of travel together")
        if (self.fx_rate is None) != (self.fx_pair is None):
            raise ValueError("fx_rate and fx_pair travel together")
        # The legacy field is the USD special case of the general one, so when
        # both are present they must agree — otherwise a reader of each gets a
        # different number for the same conversion.
        if self.fx_audusd is not None:
            if self.fx_pair != "AUDUSD":
                raise ValueError("fx_audusd is only set for an AUDUSD conversion")
            if self.fx_audusd != self.fx_rate:
                raise ValueError("fx_audusd and fx_rate disagree on the same conversion")
        return self


class ScenarioValue(Contract):
    label: ScenarioLabel
    probability: Decimal = Field(ge=0, le=1)
    roe_factor: Decimal = Field(gt=0)
    roe_start: Decimal
    value_ke_low: Decimal = Field(ge=0)
    value_ke_mid: Decimal = Field(ge=0)
    value_ke_high: Decimal = Field(ge=0)


class Sensitivities(Contract):
    """Figures computed alongside the registered value. None of them IS the value."""

    fading_excess_w050_ke_mid: Decimal = Field(ge=0)
    average_roe_ke_mid: Decimal | None = None
    average_roe_start: Decimal | None = None
    unadjusted_franking_ke_mid: Decimal = Field(ge=0)


class GapRecord(Contract):
    name: str = Field(min_length=1, max_length=80)
    detail: str = Field(min_length=1, max_length=2_000)
    table: str | None = Field(default=None, max_length=100)
    column: str | None = Field(default=None, max_length=100)
    observed: str | None = Field(default=None, max_length=500)
    required: str | None = Field(default=None, max_length=500)


class ValuationRun(ContentAddressedContract):
    run_id: str = Field(min_length=1, max_length=200)
    symbol: str = Field(min_length=1, max_length=40)
    as_of: date
    knowledge_cutoff: datetime
    created_at: datetime
    method: ValuationMethod
    terminal_convention: RegisteredTerminalConvention
    franking_convention: FrankingConvention
    return_base: ReturnBase
    horizon_years: int = Field(ge=1, le=30)
    outcome: ValuationOutcome
    #: Probability-weighted value at Ke mid under the registered convention.
    value_per_share: Decimal | None = Field(default=None, ge=0)
    value_ke_low: Decimal | None = Field(default=None, ge=0)
    value_ke_high: Decimal | None = Field(default=None, ge=0)
    value_to_price: Decimal | None = Field(default=None, ge=0)
    data_mode: DataMode
    preregistration_id: str = Field(min_length=1, max_length=200)
    ke: KeBand
    inputs: ValuationInputs | None = None
    scenarios: tuple[ScenarioValue, ...] = Field(default=(), max_length=10)
    sensitivities: Sensitivities | None = None
    gaps: tuple[GapRecord, ...] = Field(default=(), max_length=50)
    flags: tuple[str, ...] = Field(default=(), max_length=20)

    @model_validator(mode="after")
    def validate_outcome_shape(self) -> Self:
        if self.knowledge_cutoff.date() != self.as_of:
            raise ValueError("as_of must equal the UTC knowledge_cutoff date")
        if self.created_at < self.knowledge_cutoff:
            raise ValueError("created_at cannot precede knowledge_cutoff")
        valued_fields = (
            self.value_per_share,
            self.value_ke_low,
            self.value_ke_high,
            self.value_to_price,
        )
        if self.outcome == "valued":
            if any(v is None for v in valued_fields):
                raise ValueError("a valued run carries every value field")
            if self.inputs is None or self.sensitivities is None or not self.scenarios:
                raise ValueError("a valued run carries inputs, scenarios and sensitivities")
            if self.gaps:
                raise ValueError("a valued run carries no gaps — a gap is a gate, not a footnote")
        else:
            if any(v is not None for v in valued_fields):
                raise ValueError("a blocked run carries no value")
            if not self.gaps:
                raise ValueError("a blocked run names at least one gap")
            if self.scenarios or self.sensitivities is not None:
                raise ValueError("a blocked run carries no scenario or sensitivity figures")
        return self
