"""Tests for recipe gallery."""
import pytest
from app.core.recipes import RecipeEngine


class TestRecipeEngine:
    def setup_method(self):
        self.engine = RecipeEngine()

    def test_list_recipes(self):
        recipes = self.engine.list_recipes()
        assert len(recipes) >= 8

    def test_list_by_category(self):
        coding = self.engine.list_recipes(category="coding")
        assert len(coding) > 0
        assert all(r["category"] == "coding" for r in coding)

    def test_get_recipe(self):
        recipe = self.engine.get_recipe("recipe-code-review")
        assert recipe is not None
        assert recipe["name"] == "Code Reviewer"

    def test_get_nonexistent(self):
        assert self.engine.get_recipe("no-such-recipe") is None

    def test_deploy_recipe(self):
        result = self.engine.deploy_recipe("recipe-code-review", "user-1")
        assert "agent_id" in result
        assert result["status"] == "created"

    def test_deploy_nonexistent_recipe(self):
        result = self.engine.deploy_recipe("no-such-recipe", "user-1")
        assert "error" in result

    def test_deploy_increments_uses(self):
        self.engine.deploy_recipe("recipe-research", "user-1")
        recipe = self.engine.get_recipe("recipe-research")
        assert recipe["uses"] >= 1

    def test_recipe_has_required_fields(self):
        recipe = self.engine.get_recipe("recipe-code-review")
        for field in ["id", "name", "description", "category", "tools", "persona", "difficulty"]:
            assert field in recipe
