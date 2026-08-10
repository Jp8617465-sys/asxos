"""Research-to-decision contracts and composition services.

The first consumer is the read-only target-architecture prototype. Production
adapters can later load the same contracts from Supabase without coupling the
domain model to a database or renderer.
"""

from asxos.domain.decision_engine.demo import build_demo_brief
from asxos.domain.decision_engine.types import DecisionBrief, DecisionCase, DecisionPacket

__all__ = ["DecisionBrief", "DecisionCase", "DecisionPacket", "build_demo_brief"]
