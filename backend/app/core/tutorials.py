"""Interactive tutorial system with step-by-step walkthroughs."""
import uuid
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List
from datetime import datetime, timezone

logger = logging.getLogger("gnosis.tutorials")

@dataclass
class TutorialStep:
    title: str = ""
    content: str = ""
    action_type: str = ""  # click, navigate, input, observe
    target: str = ""

@dataclass
class Tutorial:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    steps: List[dict] = field(default_factory=list)
    category: str = "general"
    difficulty: str = "beginner"
    estimated_minutes: int = 5

@dataclass
class TutorialProgress:
    user_id: str = ""
    tutorial_id: str = ""
    current_step: int = 0
    completed: bool = False
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

BUILTIN_TUTORIALS = [
    Tutorial(id="tut-first-agent", title="Create Your First Agent", description="Learn how to create and configure an AI agent from scratch", category="getting-started", difficulty="beginner", estimated_minutes=5, steps=[
        {"title": "Navigate to Agent Factory", "content": "Click on the Factory tab in the sidebar", "action_type": "navigate", "target": "/factory"},
        {"title": "Choose Agent Type", "content": "Select a base template for your agent", "action_type": "click", "target": "agent-type-selector"},
        {"title": "Configure Persona", "content": "Set the agent's name, description, and personality", "action_type": "input", "target": "agent-config-form"},
        {"title": "Test Your Agent", "content": "Send a test message to verify it works", "action_type": "input", "target": "agent-chat"},
    ]),
    Tutorial(id="tut-pipeline", title="Build a Pipeline", description="Chain multiple agents to handle complex workflows", category="intermediate", difficulty="intermediate", estimated_minutes=10, steps=[
        {"title": "Open Pipelines", "content": "Navigate to the Pipelines section", "action_type": "navigate", "target": "/pipelines"},
        {"title": "Create Pipeline", "content": "Click 'New Pipeline' and give it a name", "action_type": "click", "target": "new-pipeline-btn"},
        {"title": "Add Steps", "content": "Drag agents to build your pipeline flow", "action_type": "click", "target": "pipeline-editor"},
    ]),
    Tutorial(id="tut-memory", title="Memory System Deep Dive", description="Understand the 4-tier memory architecture", category="advanced", difficulty="intermediate", estimated_minutes=8, steps=[
        {"title": "Memory Overview", "content": "Gnosis uses 4 memory tiers: Correction > Episodic > Semantic > Procedural", "action_type": "observe", "target": "memory-panel"},
        {"title": "Store a Memory", "content": "Create a semantic memory entry manually", "action_type": "input", "target": "memory-form"},
    ]),
    Tutorial(id="tut-security", title="Security Best Practices", description="Secure your agents and data", category="security", difficulty="beginner", estimated_minutes=5, steps=[
        {"title": "Review Trust Levels", "content": "Each agent has trust levels 0-3", "action_type": "observe", "target": "trust-settings"},
        {"title": "Enable PII Detection", "content": "Turn on PII redaction for sensitive data", "action_type": "click", "target": "pii-toggle"},
    ]),
    Tutorial(id="tut-prompting", title="Advanced Prompting", description="Master prompt engineering for better results", category="advanced", difficulty="advanced", estimated_minutes=15, steps=[
        {"title": "System Prompts", "content": "Customize the system prompt for precise control", "action_type": "input", "target": "system-prompt-editor"},
        {"title": "Temperature Tuning", "content": "Adjust temperature for creativity vs consistency", "action_type": "input", "target": "temperature-slider"},
    ]),
]

class TutorialEngine:
    def __init__(self):
        self._tutorials: Dict[str, Tutorial] = {t.id: t for t in BUILTIN_TUTORIALS}
        self._progress: Dict[str, Dict[str, TutorialProgress]] = {}  # user_id -> {tutorial_id -> progress}

    def list_tutorials(self, category: str = None) -> List[dict]:
        tuts = list(self._tutorials.values())
        if category:
            tuts = [t for t in tuts if t.category == category]
        return [asdict(t) for t in tuts]

    def start_tutorial(self, user_id: str, tutorial_id: str) -> dict:
        if tutorial_id not in self._tutorials:
            return {"error": "Tutorial not found"}
        progress = TutorialProgress(user_id=user_id, tutorial_id=tutorial_id)
        if user_id not in self._progress:
            self._progress[user_id] = {}
        self._progress[user_id][tutorial_id] = progress
        return asdict(progress)

    def advance_step(self, user_id: str, tutorial_id: str) -> dict:
        prog = self._progress.get(user_id, {}).get(tutorial_id)
        if not prog:
            return {"error": "Tutorial not started"}
        tut = self._tutorials[tutorial_id]
        if prog.current_step < len(tut.steps) - 1:
            prog.current_step += 1
        else:
            prog.completed = True
        return asdict(prog)

    def get_progress(self, user_id: str) -> List[dict]:
        return [asdict(p) for p in self._progress.get(user_id, {}).values()]

tutorial_engine = TutorialEngine()
