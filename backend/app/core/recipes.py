"""Pre-built agent recipes for quick deployment."""

import uuid
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List

logger = logging.getLogger("gnosis.recipes")


@dataclass
class Recipe:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    category: str = "general"
    config: dict = field(default_factory=dict)
    tools: List[str] = field(default_factory=list)
    persona: str = ""
    difficulty: str = "beginner"
    uses: int = 0


BUILTIN_RECIPES = [
    Recipe(
        id="recipe-code-review",
        name="Code Reviewer",
        description="Reviews code for bugs, security issues, and style",
        category="coding",
        tools=["code_analysis", "linting"],
        persona="Senior developer with security focus",
        difficulty="intermediate",
    ),
    Recipe(
        id="recipe-research",
        name="Research Assistant",
        description="Researches topics and provides summaries with sources",
        category="research",
        tools=["web_search", "summarizer"],
        persona="Academic researcher",
        difficulty="beginner",
    ),
    Recipe(
        id="recipe-meeting",
        name="Meeting Summarizer",
        description="Turns meeting transcripts into actionable summaries",
        category="productivity",
        tools=["summarizer", "action_items"],
        persona="Executive assistant",
        difficulty="beginner",
    ),
    Recipe(
        id="recipe-data",
        name="Data Analyst",
        description="Analyzes datasets and generates insights",
        category="data",
        tools=["data_analysis", "charting"],
        persona="Data scientist",
        difficulty="advanced",
    ),
    Recipe(
        id="recipe-writer",
        name="Creative Writer",
        description="Writes creative content with various styles",
        category="creative",
        tools=["writing", "editing"],
        persona="Versatile author",
        difficulty="beginner",
    ),
    Recipe(
        id="recipe-email",
        name="Email Drafter",
        description="Drafts professional emails based on context",
        category="productivity",
        tools=["writing", "tone_analysis"],
        persona="Communications specialist",
        difficulty="beginner",
    ),
    Recipe(
        id="recipe-bugs",
        name="Bug Hunter",
        description="Systematically finds and reports software bugs",
        category="coding",
        tools=["testing", "code_analysis"],
        persona="QA engineer with attention to detail",
        difficulty="intermediate",
    ),
    Recipe(
        id="recipe-docs",
        name="Documentation Writer",
        description="Generates comprehensive documentation from code",
        category="coding",
        tools=["code_analysis", "writing"],
        persona="Technical writer",
        difficulty="intermediate",
    ),
]


class RecipeEngine:
    def __init__(self):
        self._recipes: Dict[str, Recipe] = {r.id: r for r in BUILTIN_RECIPES}

    def list_recipes(self, category: str = None) -> List[dict]:
        recipes = list(self._recipes.values())
        if category:
            recipes = [r for r in recipes if r.category == category]
        return [asdict(r) for r in recipes]

    def get_recipe(self, recipe_id: str) -> dict:
        r = self._recipes.get(recipe_id)
        return asdict(r) if r else None

    def deploy_recipe(self, recipe_id: str, user_id: str) -> dict:
        recipe = self._recipes.get(recipe_id)
        if not recipe:
            return {"error": "Recipe not found"}
        recipe.uses += 1
        agent_id = str(uuid.uuid4())
        return {
            "agent_id": agent_id,
            "name": recipe.name,
            "recipe_id": recipe_id,
            "deployed_by": user_id,
            "status": "created",
        }


recipe_engine = RecipeEngine()
