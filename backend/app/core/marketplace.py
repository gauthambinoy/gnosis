"""Gnosis Marketplace — Browse, publish, and clone community agents."""
import uuid
import copy
import logging
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger("gnosis.marketplace")


@dataclass
class MarketplaceAgent:
    id: str
    name: str
    description: str
    category: str  # productivity, data, communication, development, creative, finance, hr, custom
    config: dict  # Agent configuration (sanitized)
    author: str = "anonymous"
    author_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    rating: float = 0.0
    rating_count: int = 0
    clone_count: int = 0
    featured: bool = False
    published_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class AgentReview:
    id: str
    marketplace_agent_id: str
    user_id: str
    rating: int  # 1-5
    comment: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


CATEGORIES = [
    {"id": "productivity", "name": "Productivity", "icon": "⚡", "description": "Task automation & scheduling"},
    {"id": "data", "name": "Data & Analytics", "icon": "📊", "description": "Data processing & insights"},
    {"id": "communication", "name": "Communication", "icon": "💬", "description": "Email, Slack, messaging"},
    {"id": "development", "name": "Development", "icon": "🛠️", "description": "Code review, CI/CD, DevOps"},
    {"id": "creative", "name": "Creative", "icon": "🎨", "description": "Content generation & design"},
    {"id": "finance", "name": "Finance", "icon": "💰", "description": "Budgeting, invoicing, tracking"},
    {"id": "hr", "name": "HR & Recruitment", "icon": "👥", "description": "Hiring, onboarding, feedback"},
    {"id": "custom", "name": "Custom", "icon": "🔧", "description": "User-created workflows"},
]


class MarketplaceEngine:
    def __init__(self):
        self._agents: Dict[str, MarketplaceAgent] = {}
        self._reviews: Dict[str, List[AgentReview]] = {}  # marketplace_agent_id -> reviews
        self._seed_marketplace()

    def _seed_marketplace(self):
        """Pre-populate with starter agents."""
        starters = [
            {"name": "Email Summarizer", "description": "Summarizes daily emails into actionable bullet points", "category": "communication", "tags": ["email", "summary", "daily"], "featured": True,
             "config": {"persona": "You are an email analyst. Summarize emails concisely.", "model_tier": "fast", "integrations": ["gmail"]}},
            {"name": "Code Reviewer", "description": "Reviews pull requests and suggests improvements", "category": "development", "tags": ["code", "review", "github"], "featured": True,
             "config": {"persona": "You are a senior code reviewer. Focus on bugs, security, performance.", "model_tier": "standard", "integrations": ["github"]}},
            {"name": "Meeting Notes Bot", "description": "Generates structured meeting notes with action items", "category": "productivity", "tags": ["meetings", "notes", "action-items"], "featured": True,
             "config": {"persona": "You convert meeting transcripts into structured notes with action items.", "model_tier": "fast"}},
            {"name": "Data Pipeline Monitor", "description": "Monitors data pipelines and alerts on anomalies", "category": "data", "tags": ["monitoring", "alerts", "data"],
             "config": {"persona": "You monitor data pipeline metrics and flag anomalies.", "model_tier": "standard"}},
            {"name": "Social Media Composer", "description": "Creates engaging social media posts from briefs", "category": "creative", "tags": ["social", "content", "marketing"],
             "config": {"persona": "You craft engaging social media posts. Be creative, concise, and on-brand.", "model_tier": "standard"}},
            {"name": "Invoice Processor", "description": "Extracts data from invoices and categorizes expenses", "category": "finance", "tags": ["invoices", "expenses", "extraction"],
             "config": {"persona": "You extract structured data from invoices: vendor, amount, date, category.", "model_tier": "fast"}},
        ]
        for s in starters:
            agent = MarketplaceAgent(
                id=str(uuid.uuid4()), name=s["name"], description=s["description"],
                category=s["category"], config=s["config"], tags=s.get("tags", []),
                featured=s.get("featured", False), author="Gnosis Team",
                rating=4.5 + (hash(s["name"]) % 5) / 10, rating_count=10 + hash(s["name"]) % 40,
                clone_count=50 + hash(s["name"]) % 200,
            )
            self._agents[agent.id] = agent

    def publish(self, name: str, description: str, category: str, config: dict,
                author: str = "anonymous", author_id: str = None, tags: list = None) -> MarketplaceAgent:
        sanitized_config = {k: v for k, v in config.items() if k not in ("api_keys", "secrets", "tokens")}
        agent = MarketplaceAgent(
            id=str(uuid.uuid4()), name=name, description=description, category=category,
            config=sanitized_config, author=author, author_id=author_id, tags=tags or [],
        )
        self._agents[agent.id] = agent
        logger.info(f"Agent published to marketplace: {agent.id}")
        return agent

    def browse(self, category: str = None, search: str = None, featured_only: bool = False,
               sort_by: str = "popular", limit: int = 20, offset: int = 0) -> tuple[List[MarketplaceAgent], int]:
        agents = list(self._agents.values())
        if category:
            agents = [a for a in agents if a.category == category]
        if featured_only:
            agents = [a for a in agents if a.featured]
        if search:
            search_lower = search.lower()
            agents = [a for a in agents if search_lower in a.name.lower() or search_lower in a.description.lower() or any(search_lower in t for t in a.tags)]

        sort_fns = {
            "popular": lambda a: a.clone_count,
            "rating": lambda a: a.rating,
            "newest": lambda a: a.published_at,
            "name": lambda a: a.name.lower(),
        }
        agents.sort(key=sort_fns.get(sort_by, sort_fns["popular"]), reverse=sort_by != "name")

        total = len(agents)
        return agents[offset:offset + limit], total

    def get_agent(self, agent_id: str) -> Optional[MarketplaceAgent]:
        return self._agents.get(agent_id)

    def clone_config(self, agent_id: str) -> Optional[dict]:
        agent = self._agents.get(agent_id)
        if not agent:
            return None
        agent.clone_count += 1
        return copy.deepcopy(agent.config)

    def add_review(self, marketplace_agent_id: str, user_id: str, rating: int, comment: str = "") -> Optional[AgentReview]:
        agent = self._agents.get(marketplace_agent_id)
        if not agent:
            return None
        rating = max(1, min(5, rating))
        review = AgentReview(
            id=str(uuid.uuid4()), marketplace_agent_id=marketplace_agent_id,
            user_id=user_id, rating=rating, comment=comment,
        )
        self._reviews.setdefault(marketplace_agent_id, []).append(review)
        # Update average
        reviews = self._reviews[marketplace_agent_id]
        agent.rating = sum(r.rating for r in reviews) / len(reviews)
        agent.rating_count = len(reviews)
        return review

    def get_reviews(self, marketplace_agent_id: str) -> List[AgentReview]:
        return list(reversed(self._reviews.get(marketplace_agent_id, [])))

    def get_categories(self) -> list:
        return CATEGORIES

    @property
    def stats(self) -> dict:
        return {
            "total_agents": len(self._agents),
            "total_categories": len(CATEGORIES),
            "featured_count": sum(1 for a in self._agents.values() if a.featured),
            "total_clones": sum(a.clone_count for a in self._agents.values()),
        }


marketplace_engine = MarketplaceEngine()
