"""Contextual help tips for UI elements."""

import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List

logger = logging.getLogger("gnosis.help")


@dataclass
class HelpTip:
    id: str = ""
    element_id: str = ""
    title: str = ""
    content: str = ""
    category: str = "general"
    related_docs: List[str] = field(default_factory=list)


BUILTIN_TIPS = [
    HelpTip(
        id="h1",
        element_id="trust-level",
        title="Trust Levels",
        content="Trust levels (0-3) control what actions agents can perform autonomously",
        category="security",
    ),
    HelpTip(
        id="h2",
        element_id="memory-tier",
        title="Memory Tiers",
        content="4 tiers: Correction (highest) > Episodic > Semantic > Procedural",
        category="memory",
    ),
    HelpTip(
        id="h3",
        element_id="temperature",
        title="Temperature",
        content="Controls randomness: 0=deterministic, 1=creative. Default 0.7",
        category="llm",
    ),
    HelpTip(
        id="h4",
        element_id="pipeline",
        title="Pipelines",
        content="Chain multiple agents to handle complex multi-step workflows",
        category="pipelines",
    ),
    HelpTip(
        id="h5",
        element_id="cortex-layers",
        title="Cortex Layers",
        content="5 layers: Input Processing, Context Building, Reasoning, Action Selection, Output",
        category="architecture",
    ),
    HelpTip(
        id="h6",
        element_id="persona",
        title="Agent Persona",
        content="Define personality, tone, and communication style for each agent",
        category="agents",
    ),
    HelpTip(
        id="h7",
        element_id="rpa",
        title="RPA Tasks",
        content="Automate browser interactions using Playwright-powered task execution",
        category="automation",
    ),
    HelpTip(
        id="h8",
        element_id="swarm",
        title="Agent Swarm",
        content="Multiple agents collaborate to solve complex problems together",
        category="swarm",
    ),
    HelpTip(
        id="h9",
        element_id="oracle",
        title="Oracle",
        content="Ask questions and get answers from your agents with full context",
        category="oracle",
    ),
    HelpTip(
        id="h10",
        element_id="knowledge-base",
        title="Knowledge Base",
        content="Upload documents for agents to reference during conversations",
        category="knowledge",
    ),
    HelpTip(
        id="h11",
        element_id="execution",
        title="Executions",
        content="Each agent task run is tracked as an execution with full audit trail",
        category="core",
    ),
    HelpTip(
        id="h12",
        element_id="webhook",
        title="Webhooks",
        content="Receive notifications when agents complete tasks or encounter errors",
        category="integrations",
    ),
    HelpTip(
        id="h13",
        element_id="api-key",
        title="API Keys",
        content="Generate time-boxed tokens for external integrations",
        category="security",
    ),
    HelpTip(
        id="h14",
        element_id="budget",
        title="Budget Limits",
        content="Set daily/monthly spending limits per agent or workspace",
        category="billing",
    ),
    HelpTip(
        id="h15",
        element_id="pii",
        title="PII Detection",
        content="Automatically detect and redact personal information in agent responses",
        category="compliance",
    ),
]


class HelpEngine:
    def __init__(self):
        self._tips: Dict[str, HelpTip] = {t.element_id: t for t in BUILTIN_TIPS}

    def get_tip(self, element_id: str) -> dict:
        tip = self._tips.get(element_id)
        return asdict(tip) if tip else None

    def search_tips(self, query: str) -> List[dict]:
        q = query.lower()
        return [
            asdict(t)
            for t in self._tips.values()
            if q in t.title.lower() or q in t.content.lower()
        ]

    def list_tips(self, category: str = None) -> List[dict]:
        tips = list(self._tips.values())
        if category:
            tips = [t for t in tips if t.category == category]
        return [asdict(t) for t in tips]


help_engine = HelpEngine()
