"""Gnosis Prompt Optimizer — Automatically improve user prompts for better results."""
import re
import logging
from dataclasses import dataclass
from typing import Dict, List

logger = logging.getLogger("gnosis.prompt_optimizer")


@dataclass
class OptimizedPrompt:
    original: str
    optimized: str
    improvements: List[str]
    estimated_quality_boost: float  # 0-100% improvement estimate


class PromptOptimizer:
    """Rule-based prompt optimizer with pattern matching."""
    
    OPTIMIZATION_RULES = [
        {
            "name": "add_specificity",
            "pattern": r"^.{1,20}$",  # Very short prompts
            "action": "expand",
            "boost": 25,
        },
        {
            "name": "add_format_instruction",
            "check": lambda p: "format" not in p.lower() and "json" not in p.lower() and "list" not in p.lower(),
            "suffix": "\nProvide your response in a clear, structured format.",
            "boost": 10,
        },
        {
            "name": "add_step_by_step",
            "check": lambda p: any(w in p.lower() for w in ["how", "explain", "why", "analyze"]) and "step" not in p.lower(),
            "suffix": " Think through this step by step.",
            "boost": 15,
        },
        {
            "name": "add_context_request",
            "check": lambda p: len(p.split()) < 10 and "?" in p,
            "prefix": "Given the available context, ",
            "boost": 12,
        },
        {
            "name": "remove_fluff",
            "patterns_remove": [r"\bplease\b", r"\bkindly\b", r"\bcan you\b", r"\bcould you\b", r"\bi want you to\b"],
            "boost": 5,
        },
    ]
    
    def __init__(self):
        self._history: Dict[str, List[dict]] = {}  # agent_id -> optimization history
    
    def optimize(self, prompt: str, agent_id: str = None) -> OptimizedPrompt:
        original = prompt.strip()
        optimized = original
        improvements = []
        total_boost = 0
        
        for rule in self.OPTIMIZATION_RULES:
            # Pattern-based check
            if "pattern" in rule:
                if not re.match(rule["pattern"], optimized):
                    continue
            
            # Lambda check
            if "check" in rule:
                if not rule["check"](optimized):
                    continue
            
            # Apply optimization
            if "suffix" in rule:
                optimized = optimized.rstrip('.') + rule["suffix"]
                improvements.append(rule["name"].replace("_", " ").title())
                total_boost += rule["boost"]
            
            if "prefix" in rule:
                optimized = rule["prefix"] + optimized[0].lower() + optimized[1:]
                improvements.append(rule["name"].replace("_", " ").title())
                total_boost += rule["boost"]
            
            if "patterns_remove" in rule:
                for pattern in rule["patterns_remove"]:
                    new_optimized = re.sub(pattern, "", optimized, flags=re.IGNORECASE).strip()
                    if new_optimized != optimized:
                        optimized = new_optimized
                        total_boost += rule["boost"]
                if optimized != original:
                    improvements.append("Removed fluff words")
        
        # Clean up whitespace
        optimized = re.sub(r'\s+', ' ', optimized).strip()
        
        result = OptimizedPrompt(
            original=original,
            optimized=optimized if optimized != original else original,
            improvements=improvements,
            estimated_quality_boost=min(50, total_boost),
        )
        
        # Track history
        if agent_id:
            self._history.setdefault(agent_id, []).append({
                "original": original[:200],
                "optimized": optimized[:200],
                "boost": result.estimated_quality_boost,
            })
        
        return result
    
    def get_history(self, agent_id: str) -> List[dict]:
        return list(reversed(self._history.get(agent_id, [])))[:50]
    
    @property
    def stats(self) -> dict:
        total_optimizations = sum(len(h) for h in self._history.values())
        avg_boost = 0
        if total_optimizations > 0:
            all_boosts = [o["boost"] for h in self._history.values() for o in h]
            avg_boost = sum(all_boosts) / len(all_boosts)
        return {"total_optimizations": total_optimizations, "avg_quality_boost": round(avg_boost, 1)}


prompt_optimizer = PromptOptimizer()
