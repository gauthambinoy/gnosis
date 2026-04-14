"""
Gnosis Swarm Intelligence — Agents form teams autonomously.
Agents can:
1. Broadcast capability advertisements
2. Discover other agents by skill
3. Request help (hire) other agents
4. Form dynamic swarms for complex tasks
5. Vote on decisions (consensus)
6. Share rewards/credit for collaborative work
"""
import asyncio
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Optional
from collections import defaultdict

@dataclass
class AgentCapability:
    agent_id: str = ""
    name: str = ""
    skills: list[str] = field(default_factory=list)
    specialization: str = ""
    trust_score: float = 0.5
    availability: str = "available"  # available, busy, offline
    tasks_completed: int = 0
    success_rate: float = 1.0
    avg_response_ms: float = 500
    registered_at: float = field(default_factory=time.time)

@dataclass
class SwarmTask:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    description: str = ""
    requester_id: str = ""
    required_skills: list[str] = field(default_factory=list)
    assigned_agents: list[str] = field(default_factory=list)
    status: str = "open"  # open, recruiting, active, voting, completed, failed
    created_at: float = field(default_factory=time.time)
    completed_at: float = 0
    subtasks: list[dict] = field(default_factory=list)
    results: list[dict] = field(default_factory=list)
    consensus: Optional[dict] = None
    reward_distribution: dict = field(default_factory=dict)

@dataclass
class SwarmMessage:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    from_agent: str = ""
    to_agent: str = ""  # Empty = broadcast
    message_type: str = ""  # recruit, accept, reject, result, vote, capability_ad
    content: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

class SwarmEngine:
    """Decentralized agent swarm coordination."""
    
    def __init__(self):
        self._registry: dict[str, AgentCapability] = {}
        self._tasks: dict[str, SwarmTask] = {}
        self._messages: list[SwarmMessage] = []
        self._message_inbox: dict[str, list[SwarmMessage]] = defaultdict(list)
        self._swarm_history: list[dict] = []
    
    # ─── Agent Registry ───
    
    def register_agent(self, agent_id: str, data: dict) -> dict:
        """Register an agent's capabilities in the swarm."""
        cap = AgentCapability(
            agent_id=agent_id,
            name=data.get("name", agent_id),
            skills=data.get("skills", []),
            specialization=data.get("specialization", "general"),
            trust_score=data.get("trust_score", 0.5),
        )
        self._registry[agent_id] = cap
        
        # Broadcast capability advertisement
        self._broadcast(SwarmMessage(
            from_agent=agent_id,
            message_type="capability_ad",
            content={"skills": cap.skills, "specialization": cap.specialization},
        ))
        
        return asdict(cap)
    
    def unregister_agent(self, agent_id: str) -> bool:
        return self._registry.pop(agent_id, None) is not None
    
    def discover_agents(self, skills: list[str] = None, specialization: str = "") -> list[dict]:
        """Find agents by skills or specialization."""
        results = []
        for cap in self._registry.values():
            if cap.availability == "offline":
                continue
            score = 0
            if skills:
                matching = set(skills) & set(cap.skills)
                score = len(matching) / len(skills) if skills else 0
            if specialization and specialization.lower() in cap.specialization.lower():
                score += 0.5
            if score > 0 or (not skills and not specialization):
                entry = asdict(cap)
                entry["match_score"] = min(score, 1.0)
                results.append(entry)
        
        results.sort(key=lambda x: (x["match_score"], x["success_rate"], x["trust_score"]), reverse=True)
        return results
    
    # ─── Swarm Tasks ───
    
    async def create_swarm_task(self, data: dict) -> dict:
        """Create a task that needs multiple agents."""
        task = SwarmTask(
            description=data.get("description", ""),
            requester_id=data.get("requester_id", ""),
            required_skills=data.get("required_skills", []),
        )
        
        # Auto-decompose into subtasks
        task.subtasks = self._decompose_task(task)
        
        # Auto-recruit agents
        task.status = "recruiting"
        recruited = await self._recruit_agents(task)
        
        if recruited:
            task.assigned_agents = [r["agent_id"] for r in recruited]
            task.status = "active"
            
            # Distribute subtasks
            for i, subtask in enumerate(task.subtasks):
                agent_idx = i % len(task.assigned_agents)
                subtask["assigned_to"] = task.assigned_agents[agent_idx]
                subtask["status"] = "assigned"
        else:
            task.status = "open"  # No agents found, wait
        
        self._tasks[task.id] = task
        return asdict(task)
    
    def _decompose_task(self, task: SwarmTask) -> list[dict]:
        """Decompose a complex task into subtasks."""
        subtasks = []
        desc_lower = task.description.lower()
        
        # Heuristic decomposition based on keywords
        if "and" in desc_lower or "then" in desc_lower:
            parts = task.description.replace(" then ", " AND ").split(" AND ")
            if len(parts) == 1:
                parts = task.description.split(" and ")
            for i, part in enumerate(parts):
                part = part.strip()
                if len(part) > 5:
                    subtasks.append({
                        "id": f"sub-{uuid.uuid4().hex[:6]}",
                        "description": part,
                        "order": i,
                        "status": "pending",
                        "assigned_to": "",
                        "result": None,
                    })
        
        if not subtasks:
            subtasks.append({
                "id": f"sub-{uuid.uuid4().hex[:6]}",
                "description": task.description,
                "order": 0,
                "status": "pending",
                "assigned_to": "",
                "result": None,
            })
        
        return subtasks
    
    async def _recruit_agents(self, task: SwarmTask) -> list[dict]:
        """Auto-recruit agents for a task based on required skills."""
        candidates = self.discover_agents(skills=task.required_skills)
        recruited = []
        
        for candidate in candidates[:5]:  # Max 5 agents per swarm
            if candidate["availability"] == "available":
                # Send recruitment message
                msg = SwarmMessage(
                    from_agent="swarm_coordinator",
                    to_agent=candidate["agent_id"],
                    message_type="recruit",
                    content={"task_id": task.id, "description": task.description[:200]},
                )
                self._send_message(msg)
                
                # Auto-accept for now (in real implementation, agents would decide)
                recruited.append(candidate)
                
                # Update availability
                if candidate["agent_id"] in self._registry:
                    self._registry[candidate["agent_id"]].availability = "busy"
        
        return recruited
    
    async def submit_result(self, task_id: str, agent_id: str, result: dict) -> dict:
        """Agent submits result for a swarm task."""
        task = self._tasks.get(task_id)
        if not task:
            return {"error": "Task not found"}
        
        task.results.append({
            "agent_id": agent_id,
            "result": result,
            "submitted_at": time.time(),
        })
        
        # Update subtask status
        for subtask in task.subtasks:
            if subtask.get("assigned_to") == agent_id:
                subtask["status"] = "completed"
                subtask["result"] = result
        
        # Check if all subtasks complete
        all_done = all(s["status"] == "completed" for s in task.subtasks)
        if all_done:
            task.status = "voting"
            task.consensus = await self._reach_consensus(task)
            task.status = "completed"
            task.completed_at = time.time()
            
            # Distribute rewards (credit)
            task.reward_distribution = self._distribute_credit(task)
            
            # Free agents
            for aid in task.assigned_agents:
                if aid in self._registry:
                    self._registry[aid].availability = "available"
                    self._registry[aid].tasks_completed += 1
            
            self._swarm_history.append(asdict(task))
        
        return asdict(task)
    
    async def _reach_consensus(self, task: SwarmTask) -> dict:
        """Agents vote on the best combined result."""
        if not task.results:
            return {"method": "none", "outcome": "no results"}
        
        if len(task.results) == 1:
            return {"method": "single", "outcome": "accepted", "winner": task.results[0]["agent_id"]}
        
        # Simple scoring: each result gets quality score based on completeness
        scores = {}
        for r in task.results:
            result_str = str(r.get("result", ""))
            score = min(len(result_str) / 100, 5.0)  # Length-based heuristic
            if r.get("result", {}).get("success"):
                score += 2
            scores[r["agent_id"]] = score
        
        winner = max(scores, key=scores.get) if scores else task.results[0]["agent_id"]
        return {
            "method": "quality_score",
            "scores": scores,
            "winner": winner,
            "outcome": "consensus_reached",
        }
    
    def _distribute_credit(self, task: SwarmTask) -> dict:
        """Distribute credit/reward among participating agents."""
        if not task.assigned_agents:
            return {}
        
        total_credit = 100
        distribution = {}
        
        if task.consensus and task.consensus.get("scores"):
            total_score = sum(task.consensus["scores"].values())
            for agent_id, score in task.consensus["scores"].items():
                distribution[agent_id] = round((score / max(total_score, 1)) * total_credit, 1)
        else:
            per_agent = total_credit / len(task.assigned_agents)
            for agent_id in task.assigned_agents:
                distribution[agent_id] = round(per_agent, 1)
        
        # Update trust scores
        for agent_id, credit in distribution.items():
            if agent_id in self._registry:
                self._registry[agent_id].trust_score = min(1.0, self._registry[agent_id].trust_score + credit * 0.001)
        
        return distribution
    
    # ─── Messaging ───
    
    def _broadcast(self, message: SwarmMessage):
        self._messages.append(message)
        for agent_id in self._registry:
            if agent_id != message.from_agent:
                self._message_inbox[agent_id].append(message)
    
    def _send_message(self, message: SwarmMessage):
        self._messages.append(message)
        if message.to_agent:
            self._message_inbox[message.to_agent].append(message)
    
    def get_inbox(self, agent_id: str, limit: int = 20) -> list[dict]:
        messages = self._message_inbox.get(agent_id, [])
        return [asdict(m) for m in messages[-limit:]]
    
    # ─── Queries ───
    
    def get_task(self, task_id: str) -> Optional[dict]:
        task = self._tasks.get(task_id)
        return asdict(task) if task else None
    
    def list_tasks(self, status: str = "") -> list[dict]:
        tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        return [asdict(t) for t in tasks]
    
    def get_registry(self) -> list[dict]:
        return [asdict(c) for c in self._registry.values()]
    
    def get_stats(self) -> dict:
        return {
            "registered_agents": len(self._registry),
            "available_agents": sum(1 for c in self._registry.values() if c.availability == "available"),
            "active_tasks": sum(1 for t in self._tasks.values() if t.status in ("recruiting", "active", "voting")),
            "completed_tasks": sum(1 for t in self._tasks.values() if t.status == "completed"),
            "total_messages": len(self._messages),
            "total_swarm_history": len(self._swarm_history),
        }

swarm_engine = SwarmEngine()
