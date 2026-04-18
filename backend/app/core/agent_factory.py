"""
Gnosis Agent Factory — Create complete AI agents from natural language.
The killer feature: "Describe it → Gnosis builds it"
"""

import time
import uuid
import re
from dataclasses import dataclass, field, asdict
from typing import Optional

# Intent categories the factory can handle
INTENT_TEMPLATES = {
    "monitor": {
        "keywords": [
            "monitor",
            "watch",
            "track",
            "check",
            "alert",
            "notify when",
            "keep eye",
        ],
        "description": "Continuously monitor something and alert on changes",
        "requires": ["schedule", "notification"],
        "default_schedule": "0 */6 * * *",  # Every 6 hours
    },
    "scrape": {
        "keywords": [
            "scrape",
            "extract",
            "pull data",
            "get info from",
            "crawl",
            "collect from website",
        ],
        "description": "Extract data from websites or APIs",
        "requires": ["web_access"],
        "default_schedule": "0 0 * * *",  # Daily
    },
    "automate_email": {
        "keywords": [
            "email",
            "send mail",
            "inbox",
            "reply to",
            "forward",
            "summarize emails",
        ],
        "description": "Email automation — read, send, summarize, auto-reply",
        "requires": ["email_integration"],
    },
    "data_pipeline": {
        "keywords": [
            "transform",
            "convert",
            "process data",
            "clean data",
            "merge",
            "analyze data",
            "csv",
            "spreadsheet",
        ],
        "description": "Process, transform, or analyze data",
        "requires": ["file_access"],
    },
    "social_media": {
        "keywords": [
            "tweet",
            "post",
            "social media",
            "linkedin",
            "twitter",
            "instagram",
            "schedule post",
        ],
        "description": "Social media management and posting",
        "requires": ["social_integration"],
    },
    "report": {
        "keywords": [
            "report",
            "summary",
            "digest",
            "dashboard",
            "weekly report",
            "daily summary",
            "compile",
        ],
        "description": "Generate periodic reports or summaries",
        "requires": ["schedule", "notification"],
        "default_schedule": "0 9 * * 1",  # Monday 9 AM
    },
    "chatbot": {
        "keywords": [
            "chatbot",
            "answer questions",
            "customer support",
            "help desk",
            "FAQ",
            "respond to",
        ],
        "description": "Interactive chatbot for Q&A or support",
        "requires": ["knowledge_base"],
    },
    "workflow": {
        "keywords": [
            "when",
            "if",
            "then",
            "trigger",
            "whenever",
            "automatically",
            "on event",
        ],
        "description": "Event-driven workflow automation",
        "requires": ["webhook"],
    },
    "research": {
        "keywords": [
            "research",
            "find",
            "search for",
            "look up",
            "investigate",
            "compare",
            "analyze",
        ],
        "description": "Research and analysis tasks",
        "requires": [],
    },
    "content": {
        "keywords": [
            "write",
            "create content",
            "blog",
            "article",
            "generate",
            "draft",
            "copywriting",
        ],
        "description": "Content creation and writing",
        "requires": [],
    },
}


@dataclass
class FactoryAnalysis:
    """Result of analyzing a user's natural language request."""

    raw_input: str = ""
    detected_intents: list[str] = field(default_factory=list)
    confidence: float = 0.0
    entities: dict = field(
        default_factory=dict
    )  # Extracted: urls, emails, schedules, etc.
    suggested_name: str = ""
    suggested_description: str = ""


@dataclass
class AgentBlueprint:
    """Blueprint for an agent to be created."""

    name: str = ""
    description: str = ""
    system_prompt: str = ""
    model: str = "fast"
    tools_needed: list[str] = field(default_factory=list)
    input_schema: dict = field(default_factory=dict)


@dataclass
class DeploymentPlan:
    """Complete plan for what the factory will create."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    status: str = "draft"  # draft, approved, deploying, deployed, failed
    user_input: str = ""
    analysis: dict = field(default_factory=dict)
    agents: list[dict] = field(default_factory=list)
    pipeline: Optional[dict] = None
    schedule: Optional[dict] = None
    integrations: list[dict] = field(default_factory=list)
    estimated_cost_per_run: str = ""
    created_at: float = field(default_factory=time.time)
    deployed_at: float = 0
    # What was actually created
    created_agent_ids: list[str] = field(default_factory=list)
    created_pipeline_id: str = ""
    created_schedule_id: str = ""


class AgentFactory:
    """Creates complete AI agents from natural language descriptions."""

    def __init__(self):
        self._plans: dict[str, DeploymentPlan] = {}
        self._deployments: list[dict] = []

    # ─── Analysis ───

    def analyze(self, user_input: str) -> dict:
        """Analyze natural language input and return a deployment plan."""
        analysis = self._analyze_intent(user_input)
        plan = self._generate_plan(user_input, analysis)
        self._plans[plan.id] = plan
        return asdict(plan)

    def _analyze_intent(self, text: str) -> FactoryAnalysis:
        """Extract intents, entities, and confidence from text."""
        text_lower = text.lower()
        analysis = FactoryAnalysis(raw_input=text)

        # Detect intents
        intent_scores = {}
        for intent_name, config in INTENT_TEMPLATES.items():
            score = sum(1 for kw in config["keywords"] if kw in text_lower)
            if score > 0:
                intent_scores[intent_name] = score

        if intent_scores:
            sorted_intents = sorted(
                intent_scores.items(), key=lambda x: x[1], reverse=True
            )
            analysis.detected_intents = [i[0] for i in sorted_intents[:3]]
            analysis.confidence = min(sorted_intents[0][1] / 3.0, 1.0)
        else:
            analysis.detected_intents = ["workflow"]
            analysis.confidence = 0.3

        # Extract entities
        analysis.entities = self._extract_entities(text)

        # Generate name
        analysis.suggested_name = self._generate_name(text, analysis.detected_intents)
        analysis.suggested_description = text[:200]

        return analysis

    def _extract_entities(self, text: str) -> dict:
        """Extract URLs, emails, schedules, etc. from text."""
        entities = {}

        # URLs
        urls = re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+', text)
        if urls:
            entities["urls"] = urls

        # Emails
        emails = re.findall(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
        if emails:
            entities["emails"] = emails

        # Time patterns
        time_patterns = {
            "every hour": "0 * * * *",
            "hourly": "0 * * * *",
            "every day": "0 9 * * *",
            "daily": "0 9 * * *",
            "every week": "0 9 * * 1",
            "weekly": "0 9 * * 1",
            "every month": "0 9 1 * *",
            "monthly": "0 9 1 * *",
            "every morning": "0 8 * * *",
            "every evening": "0 18 * * *",
            "every night": "0 22 * * *",
            "twice a day": "0 9,18 * * *",
            "every 5 minutes": "*/5 * * * *",
            "every 15 minutes": "*/15 * * * *",
            "every 30 minutes": "*/30 * * * *",
        }
        text_lower = text.lower()
        for pattern, cron in time_patterns.items():
            if pattern in text_lower:
                entities["schedule"] = cron
                entities["schedule_description"] = pattern
                break

        # Numbers
        numbers = re.findall(r"\b(\d+)\b", text)
        if numbers:
            entities["numbers"] = numbers[:5]

        return entities

    def _generate_name(self, text: str, intents: list) -> str:
        """Generate a catchy agent name from the description."""
        prefixes = {
            "monitor": "🔍 Monitor",
            "scrape": "🕷️ Scraper",
            "automate_email": "📧 Email",
            "data_pipeline": "⚙️ Data",
            "social_media": "📱 Social",
            "report": "📊 Report",
            "chatbot": "💬 Chat",
            "workflow": "🔄 Workflow",
            "research": "🔬 Research",
            "content": "✍️ Content",
        }

        prefix = prefixes.get(intents[0], "🤖") if intents else "🤖"

        # Extract key noun
        words = text.split()[:8]
        clean = " ".join(w for w in words if len(w) > 2)[:40]

        return f"{prefix} Agent — {clean}"

    def _generate_plan(
        self, user_input: str, analysis: FactoryAnalysis
    ) -> DeploymentPlan:
        """Generate a complete deployment plan from analysis."""
        plan = DeploymentPlan(
            user_input=user_input,
            analysis=asdict(analysis),
        )

        primary_intent = (
            analysis.detected_intents[0] if analysis.detected_intents else "workflow"
        )
        intent_config = INTENT_TEMPLATES.get(primary_intent, {})

        # Build system prompt based on intent
        system_prompt = self._build_system_prompt(
            user_input, primary_intent, analysis.entities
        )

        # Create main agent blueprint
        main_agent = {
            "name": analysis.suggested_name,
            "description": user_input[:500],
            "system_prompt": system_prompt,
            "model": "fast",
            "personality": "efficient",
            "trust_level": 2,
            "tools_needed": intent_config.get("requires", []),
        }
        plan.agents.append(main_agent)

        # Add helper agents for complex tasks
        if len(analysis.detected_intents) > 1:
            for intent in analysis.detected_intents[1:]:
                helper_config = INTENT_TEMPLATES.get(intent, {})
                helper = {
                    "name": f"Helper — {intent.replace('_', ' ').title()}",
                    "description": f"Handles {helper_config.get('description', intent)} subtask",
                    "system_prompt": f"You are a specialized assistant for {helper_config.get('description', intent)}. Help the main agent by handling this specific subtask.",
                    "model": "fast",
                    "tools_needed": helper_config.get("requires", []),
                }
                plan.agents.append(helper)

        # Create pipeline if multiple agents
        if len(plan.agents) > 1:
            steps = []
            for i, agent in enumerate(plan.agents):
                steps.append(
                    {
                        "name": agent["name"],
                        "agent_index": i,
                        "order": i,
                        "pass_output_to_next": True,
                    }
                )
            plan.pipeline = {
                "name": f"Pipeline — {analysis.suggested_name}",
                "steps": steps,
                "retry_on_failure": True,
                "max_retries": 2,
            }

        # Set up schedule if needed
        schedule_cron = analysis.entities.get("schedule")
        if not schedule_cron and "schedule" in intent_config.get("requires", []):
            schedule_cron = intent_config.get("default_schedule", "0 9 * * *")

        if schedule_cron:
            plan.schedule = {
                "cron": schedule_cron,
                "description": analysis.entities.get(
                    "schedule_description", "Scheduled run"
                ),
                "timezone": "UTC",
                "enabled": True,
            }

        # Integrations
        if analysis.entities.get("urls"):
            plan.integrations.append(
                {
                    "type": "web_access",
                    "config": {"urls": analysis.entities["urls"]},
                }
            )
        if analysis.entities.get("emails") or "email" in str(
            intent_config.get("requires", [])
        ):
            plan.integrations.append(
                {
                    "type": "email",
                    "config": {"recipients": analysis.entities.get("emails", [])},
                }
            )
        if "notification" in intent_config.get("requires", []):
            plan.integrations.append(
                {
                    "type": "notification",
                    "config": {"channels": ["email", "in_app"]},
                }
            )

        # Cost estimate
        tokens_per_run = 500 * len(plan.agents)
        plan.estimated_cost_per_run = (
            f"~{tokens_per_run} tokens (~${tokens_per_run * 0.000002:.4f})"
        )

        return plan

    def _build_system_prompt(self, user_input: str, intent: str, entities: dict) -> str:
        """Build an optimized system prompt for the agent with injection protection."""
        from app.core.input_sanitizer import build_safe_system_prompt, detect_injection

        desc = INTENT_TEMPLATES.get(intent, {}).get("description", "general automation")

        base_instructions = f"""You are a Gnosis AI agent specialized in: {desc}.

Guidelines:
- Be precise and actionable in your responses
- Return structured data when possible (JSON)
- Report errors clearly with suggestions
- Track your progress and report completion status"""

        if entities.get("urls"):
            base_instructions += f"\n- Target URLs: {', '.join(entities['urls'])}"
        if entities.get("emails"):
            base_instructions += (
                f"\n- Notification emails: {', '.join(entities['emails'])}"
            )

        # Log potential injection attempts (advisory, does not block)
        injection_warning = detect_injection(user_input)
        if injection_warning:
            import logging

            logging.getLogger("gnosis.security").warning(
                "Prompt injection attempt in agent factory: %s", injection_warning
            )

        return build_safe_system_prompt(base_instructions, user_input)

    def _estimate_runs(self, cron: str) -> int:
        """Rough estimate of monthly runs from a cron expression."""
        if "* * * * *" in cron:
            return 43200  # Every minute
        if "*/5" in cron:
            return 8640
        if "*/15" in cron:
            return 2880
        if "*/30" in cron:
            return 1440
        if "0 * * * *" in cron:
            return 720  # Hourly
        if "0 */6" in cron:
            return 120
        if "0 9 * * *" in cron:
            return 30  # Daily
        if "0 9 * * 1" in cron:
            return 4  # Weekly
        if "0 9 1 * *" in cron:
            return 1  # Monthly
        return 30

    # ─── Deployment ───

    async def deploy(self, plan_id: str) -> dict:
        """Deploy a plan — create all agents, pipelines, schedules."""
        plan = self._plans.get(plan_id)
        if not plan:
            return {"error": "Plan not found"}

        plan.status = "deploying"

        try:
            # Create agents
            from app.api.agents import _agents

            for agent_data in plan.agents:
                agent_id = uuid.uuid4().hex[:12]
                _agents[agent_id] = {
                    "id": agent_id,
                    "name": agent_data["name"],
                    "description": agent_data["description"],
                    "system_prompt": agent_data["system_prompt"],
                    "model": agent_data.get("model", "fast"),
                    "personality": agent_data.get("personality", "efficient"),
                    "trust_level": agent_data.get("trust_level", 2),
                    "status": "active",
                    "created_at": time.time(),
                    "updated_at": time.time(),
                    "execution_count": 0,
                }
                plan.created_agent_ids.append(agent_id)

            # Create pipeline if defined
            if plan.pipeline and len(plan.created_agent_ids) > 1:
                from app.core.pipeline import pipeline_engine

                steps = [
                    {
                        "agent_id": plan.created_agent_ids[step["agent_index"]],
                        "name": step["name"],
                    }
                    for step in plan.pipeline["steps"]
                ]
                pipeline = pipeline_engine.create_pipeline(
                    name=plan.pipeline["name"],
                    steps=steps,
                )
                plan.created_pipeline_id = pipeline.id

            # Create schedule if defined
            if plan.schedule and plan.created_agent_ids:
                from app.core.scheduler import scheduler_engine

                schedule = scheduler_engine.create(
                    agent_id=plan.created_agent_ids[0],
                    name=plan.schedule["description"],
                    cron_expression=plan.schedule["cron"],
                    input_data={"prompt": plan.user_input},
                )
                plan.created_schedule_id = schedule.id

            plan.status = "deployed"
            plan.deployed_at = time.time()

        except Exception as e:
            plan.status = "failed"
            return {"error": str(e), "plan": asdict(plan)}

        self._deployments.append(asdict(plan))
        return asdict(plan)

    # ─── CRUD ───

    def get_plan(self, plan_id: str) -> Optional[dict]:
        plan = self._plans.get(plan_id)
        return asdict(plan) if plan else None

    def list_plans(self) -> list[dict]:
        plans = sorted(self._plans.values(), key=lambda p: p.created_at, reverse=True)
        return [asdict(p) for p in plans]

    def delete_plan(self, plan_id: str) -> bool:
        return self._plans.pop(plan_id, None) is not None

    def get_deployments(self) -> list[dict]:
        return self._deployments

    def get_stats(self) -> dict:
        return {
            "total_plans": len(self._plans),
            "deployed": sum(1 for p in self._plans.values() if p.status == "deployed"),
            "draft": sum(1 for p in self._plans.values() if p.status == "draft"),
            "total_agents_created": sum(
                len(p.created_agent_ids) for p in self._plans.values()
            ),
            "available_intents": list(INTENT_TEMPLATES.keys()),
        }


# Singleton
agent_factory = AgentFactory()
