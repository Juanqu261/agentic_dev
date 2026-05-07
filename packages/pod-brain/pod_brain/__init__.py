"""
pod-brain: LangGraph orchestration engine for Agentic DevStudio.

Public API surface imported by apps/studio-api:
  get_graph()      — async factory returning the compiled graph
  build_graph()    — synchronous builder for testing
  PodState         — TypedDict for type hints
  DesignPlan       — Pydantic model (Architect output)
  QAResult         — Pydantic model (QA output)
  HumanDecision    — Pydantic model (interrupt resume payload)
"""
from pod_brain.graph.pod_graph import build_graph, get_graph
from pod_brain.graph.state import DesignPlan, HumanDecision, PodState, QAResult

__all__ = [
    "get_graph",
    "build_graph",
    "PodState",
    "DesignPlan",
    "QAResult",
    "HumanDecision",
]
