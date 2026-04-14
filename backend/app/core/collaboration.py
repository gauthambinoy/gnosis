"""Gnosis Collaboration — Multi-agent discussion rooms."""
import uuid, asyncio, logging
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger("gnosis.collaboration")


@dataclass
class RoomMessage:
    id: str
    room_id: str
    agent_id: str
    agent_name: str
    content: str
    message_type: str = "discussion"  # discussion, proposal, decision, question, answer
    in_reply_to: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class CollaborationRoom:
    id: str
    name: str
    topic: str
    agent_ids: List[str] = field(default_factory=list)
    agent_names: Dict[str, str] = field(default_factory=dict)  # agent_id -> name
    messages: List[RoomMessage] = field(default_factory=list)
    status: str = "active"  # active, resolved, archived
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resolved_at: Optional[str] = None
    conclusion: Optional[str] = None
    max_rounds: int = 5


class CollaborationEngine:
    def __init__(self):
        self._rooms: Dict[str, CollaborationRoom] = {}
        self._execute_fn = None
    
    def set_executor(self, fn):
        self._execute_fn = fn
    
    def create_room(self, name: str, topic: str, agent_ids: List[str], 
                    agent_names: Dict[str, str] = None, max_rounds: int = 5) -> CollaborationRoom:
        room = CollaborationRoom(
            id=str(uuid.uuid4()),
            name=name,
            topic=topic,
            agent_ids=agent_ids,
            agent_names=agent_names or {aid: f"Agent-{aid[:6]}" for aid in agent_ids},
            max_rounds=max_rounds,
        )
        self._rooms[room.id] = room
        logger.info(f"Collaboration room created: {room.id} with {len(agent_ids)} agents")
        return room
    
    def get_room(self, room_id: str) -> Optional[CollaborationRoom]:
        return self._rooms.get(room_id)
    
    def list_rooms(self, status: str = None) -> List[CollaborationRoom]:
        rooms = list(self._rooms.values())
        if status:
            rooms = [r for r in rooms if r.status == status]
        return sorted(rooms, key=lambda r: r.created_at, reverse=True)
    
    def add_message(self, room_id: str, agent_id: str, content: str, 
                    message_type: str = "discussion", in_reply_to: str = None) -> Optional[RoomMessage]:
        room = self._rooms.get(room_id)
        if not room:
            return None
        msg = RoomMessage(
            id=str(uuid.uuid4()),
            room_id=room_id,
            agent_id=agent_id,
            agent_name=room.agent_names.get(agent_id, agent_id[:8]),
            content=content,
            message_type=message_type,
            in_reply_to=in_reply_to,
        )
        room.messages.append(msg)
        return msg
    
    async def run_discussion(self, room_id: str) -> CollaborationRoom:
        """Run an automated discussion between agents in the room."""
        room = self._rooms.get(room_id)
        if not room:
            raise ValueError("Room not found")
        
        # Initial prompt for each agent based on the topic
        context_history = []
        
        for round_num in range(room.max_rounds):
            for agent_id in room.agent_ids:
                agent_name = room.agent_names.get(agent_id, agent_id[:8])
                
                # Build context from previous messages
                history_text = "\n".join([
                    f"{m.agent_name}: {m.content}" for m in room.messages[-10:]
                ]) if room.messages else "No messages yet."
                
                prompt = f"""You are {agent_name} in a collaborative discussion about: {room.topic}

Previous discussion:
{history_text}

Round {round_num + 1}/{room.max_rounds}. Share your perspective, build on others' ideas, or propose solutions. Be concise (2-3 sentences max)."""
                
                if self._execute_fn:
                    try:
                        result = await self._execute_fn(agent_id, {"task": prompt})
                        response = result.get("output", result.get("response", str(result)))[:500]
                    except Exception as e:
                        response = f"[Could not contribute: {str(e)[:100]}]"
                else:
                    # Dry run mode
                    response = f"[{agent_name}] Perspective on '{room.topic}' (round {round_num + 1}): This is a simulated contribution."
                
                msg_type = "discussion" if round_num < room.max_rounds - 1 else "decision"
                self.add_message(room_id, agent_id, response, message_type=msg_type)
        
        room.status = "resolved"
        room.resolved_at = datetime.now(timezone.utc).isoformat()
        
        # Generate conclusion from last messages
        last_messages = [m.content for m in room.messages[-len(room.agent_ids):]]
        room.conclusion = " | ".join(last_messages)[:500]
        
        return room
    
    def resolve_room(self, room_id: str, conclusion: str) -> Optional[CollaborationRoom]:
        room = self._rooms.get(room_id)
        if not room:
            return None
        room.status = "resolved"
        room.resolved_at = datetime.now(timezone.utc).isoformat()
        room.conclusion = conclusion
        return room
    
    def archive_room(self, room_id: str) -> bool:
        room = self._rooms.get(room_id)
        if room:
            room.status = "archived"
            return True
        return False
    
    @property
    def stats(self) -> dict:
        statuses = {}
        for r in self._rooms.values():
            statuses[r.status] = statuses.get(r.status, 0) + 1
        return {
            "total_rooms": len(self._rooms),
            "total_messages": sum(len(r.messages) for r in self._rooms.values()),
            "by_status": statuses,
        }


collaboration_engine = CollaborationEngine()
