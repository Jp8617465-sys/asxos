"""Live target-architecture cockpit.

Run with ``make decision-demo``. This app is intentionally separate from
``asxos.api.main`` so viewing a synthetic prototype neither bypasses production
startup guards nor requires database, email, or model credentials.
"""

from __future__ import annotations

from functools import lru_cache

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict

from asxos.domain.decision_engine.demo import build_demo_brief
from asxos.domain.decision_engine.renderer import render_decision_brief
from asxos.domain.decision_engine.types import DecisionBrief, DecisionCase


class PrototypeHealth(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: str
    mode: str


@lru_cache(maxsize=1)
def _brief() -> DecisionBrief:
    return build_demo_brief()


app = FastAPI(
    title="ASXOS target-architecture prototype",
    description="Read-only synthetic research-to-decision vertical slice.",
    version="0.1.0",
)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def cockpit() -> HTMLResponse:
    return HTMLResponse(render_decision_brief(_brief()))


@app.get("/api/brief", response_model=DecisionBrief)
def decision_brief() -> DecisionBrief:
    return _brief()


@app.get("/api/cases/{case_id}", response_model=DecisionCase)
def decision_case(case_id: str) -> DecisionCase:
    case = next((candidate for candidate in _brief().cases if candidate.case_id == case_id), None)
    if case is None:
        raise HTTPException(status_code=404, detail="decision case not found")
    return case


@app.get("/health", response_model=PrototypeHealth)
def health() -> PrototypeHealth:
    return PrototypeHealth(status="ok", mode="synthetic_prototype")
