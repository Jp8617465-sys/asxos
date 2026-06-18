"""
model_a training configurations — declarative, side-effect-free.

A :class:`ModelTrainingConfig` describes HOW a model_a version is trained: the
price basis for features/returns/target, the regression target unit, the
liquidity price basis, the label horizon, and the purge/embargo. It is pure
data — importing or constructing one trains nothing, writes no artefact, touches
no database, and activates no model.

It exists so a future, non-active v1_6 *shadow* training step can thread its
fields into ``loader.load_panel`` / ``train.train_model_a`` /
``metadata.build_artifact_metadata`` without re-deriving them. Until that wiring
lands, the production retrain job (``jobs/retrain_model_a.py``) is unchanged and
keeps training v1_5 with its built-in defaults.

Activation is deliberately NOT representable here. Training never activates a
model; flipping ``model_versions.is_active`` is a separate, explicit operator
step (``asx model activate <version>`` → ``asxos/cli/model.py``). The retrain
job only ever inserts a candidate row with ``is_active = FALSE``. See
``.claude/rules/ml-conventions.md`` and CLAUDE.md.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from asxos.domain.models.metadata import (
    DEFAULT_LABEL_HORIZON_DAYS,
    build_artifact_metadata,
)

_PRICE_BASES = ("close", "adj_close")
_TARGET_UNITS = ("basis_points", "fraction")


@dataclass(frozen=True)
class ModelTrainingConfig:
    """Declarative, side-effect-free recipe for training a model_a version.

    Defaults reproduce the active v1_5 behaviour exactly (raw close, basis-point
    target, no adj_close column). The frozen dataclass has no field that can
    activate a model — activation is out of band by design.
    """

    model_version: str
    price_basis: str = "close"
    target_unit: str = "basis_points"
    liquidity_price_basis: str = "close"
    include_adj_close: bool = False
    label_horizon_days: int = DEFAULT_LABEL_HORIZON_DAYS
    purge_embargo_days: int = DEFAULT_LABEL_HORIZON_DAYS

    def __post_init__(self) -> None:
        if self.price_basis not in _PRICE_BASES:
            raise ValueError(f"price_basis must be one of {_PRICE_BASES}, got {self.price_basis!r}")
        if self.target_unit not in _TARGET_UNITS:
            raise ValueError(f"target_unit must be one of {_TARGET_UNITS}, got {self.target_unit!r}")
        # Liquidity dollar-volume is real tradeable dollars: always raw close,
        # in every mode (mirrors FeatureEngine._liquidity, which never uses the
        # adj basis). A non-"close" value here would be a contract violation.
        if self.liquidity_price_basis != "close":
            raise ValueError("liquidity_price_basis must be 'close' (raw tradeable dollars)")
        # An adj_close price basis is only meaningful if the loader actually
        # selects the adj_close column.
        if self.price_basis == "adj_close" and not self.include_adj_close:
            raise ValueError("price_basis='adj_close' requires include_adj_close=True")
        if self.label_horizon_days <= 0 or self.purge_embargo_days < 0:
            raise ValueError("label_horizon_days must be > 0 and purge_embargo_days >= 0")

    @property
    def train_model_a_kwargs(self) -> dict[str, str]:
        """Keyword args to thread into ``train_model_a`` (and ``build_target``).

        For the v1_5 defaults these are ``target_unit="basis_points"`` and
        ``price_basis="close"`` — exactly the values ``train_model_a`` already
        defaults to, so threading them is byte-identical to today's call.
        """
        return {"target_unit": self.target_unit, "price_basis": self.price_basis}

    @property
    def load_panel_kwargs(self) -> dict[str, bool]:
        """Keyword args to thread into ``loader.load_panel``."""
        return {"include_adj_close": self.include_adj_close}

    def to_artifact_metadata(self, *, train_start: str, train_end: str) -> dict[str, Any]:
        """Build this config's self-describing v1_6 artefact metadata.

        Pure: returns a dict via ``metadata.build_artifact_metadata`` and writes
        nothing. Activation is not represented in the output.
        """
        return build_artifact_metadata(
            model_version=self.model_version,
            target_unit=self.target_unit,
            price_basis=self.price_basis,
            liquidity_price_basis=self.liquidity_price_basis,
            label_horizon_days=self.label_horizon_days,
            purge_embargo_days=self.purge_embargo_days,
            train_start=train_start,
            train_end=train_end,
        )


# v1_5 — the ACTIVE production model. Defaults preserve current behaviour
# exactly (raw close, basis-point target, no adj_close). Provided for parity.
MODEL_A_V1_5_CONFIG = ModelTrainingConfig(model_version="model_a_v1_5")

# v1_6 — the SHADOW path. adj_close basis + fractional target; liquidity stays
# raw close. NOT active and NOT trained by this change; the production job still
# trains v1_5. A future shadow run threads this config's kwargs into the
# loader / trainer / metadata builder.
MODEL_A_V1_6_CONFIG = ModelTrainingConfig(
    model_version="model_a_v1_6",
    price_basis="adj_close",
    target_unit="fraction",
    liquidity_price_basis="close",
    include_adj_close=True,
)


# Version → config registry. Unknown versions fall back to the v1_5 baseline
# recipe so any non-v1_6 retrain stays byte-identical to the legacy path.
_CONFIGS_BY_VERSION: dict[str, ModelTrainingConfig] = {
    MODEL_A_V1_5_CONFIG.model_version: MODEL_A_V1_5_CONFIG,
    MODEL_A_V1_6_CONFIG.model_version: MODEL_A_V1_6_CONFIG,
}


def select_training_config(model_version: str) -> ModelTrainingConfig:
    """Map a full model version (e.g. "model_a_v1_6") to its training config.

    Returns the exact ``MODEL_A_V1_5_CONFIG`` singleton for any unrecognised
    version, so a caller may use identity (``is MODEL_A_V1_5_CONFIG``) to decide
    whether a version carries the v1_6 self-describing contract. Pure lookup —
    no side effects, no DB, no activation.
    """
    return _CONFIGS_BY_VERSION.get(model_version, MODEL_A_V1_5_CONFIG)


def training_panel_columns(
    config: ModelTrainingConfig,
    feature_cols: list[str],
    *,
    base_cols: tuple[str, ...] = ("symbol", "dt", "close"),
) -> list[str]:
    """Columns to retain per batch before concatenating the training panel.

    Always keeps symbol/dt/raw-close (build_target's per-symbol grouping and the
    raw-close liquidity dollar-volume) plus the model features. Under an
    adj_close basis the adjusted column is additionally retained so build_target
    and the FeatureEngine can read it. Returned sorted for determinism.
    """
    cols = set(base_cols) | set(feature_cols)
    if config.include_adj_close:
        cols.add("adj_close")
    return sorted(cols)
