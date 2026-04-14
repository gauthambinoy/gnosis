"""Gnosis Chorus — agent-to-agent communication and collaboration."""
import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Awaitable

from app.core.event_bus import event_bus


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------
MessageHandler = Callable[[dict], Awaitable[dict | None]]


class AgentChorus:
    """Enables agents to collaborate, share knowledge, and delegate tasks."""

    def __init__(self):
        self.channels: dict[str, list[str]] = {}  # channel_name → [agent_ids]
        self.message_log: list[dict] = []
        self._max_log = 5000
        self._agent_handlers: dict[str, MessageHandler] = {}  # agent_id → handler
        self._knowledge_providers: dict[str, Callable[[str], Awaitable[list[dict]]]] = {}

    # ------------------------------------------------------------------
    # Channel management
    # ------------------------------------------------------------------
    def subscribe(self, agent_id: str, channel: str):
        """Subscribe agent to a communication channel."""
        if channel not in self.channels:
            self.channels[channel] = []
        if agent_id not in self.channels[channel]:
            self.channels[channel].append(agent_id)

    def unsubscribe(self, agent_id: str, channel: str):
        """Unsubscribe agent from a channel."""
        if channel in self.channels:
            self.channels[channel] = [a for a in self.channels[channel] if a != agent_id]

    def list_channels(self) -> dict[str, list[str]]:
        """Return all channels with their subscribers."""
        return dict(self.channels)

    # ------------------------------------------------------------------
    # Handler registration
    # ------------------------------------------------------------------
    def register_handler(self, agent_id: str, handler: MessageHandler):
        """Register a message handler for an agent (for delegation & queries)."""
        self._agent_handlers[agent_id] = handler

    def register_knowledge_provider(
        self, agent_id: str, provider: Callable[[str], Awaitable[list[dict]]]
    ):
        """Register a knowledge provider — called during request_knowledge."""
        self._knowledge_providers[agent_id] = provider

    # ------------------------------------------------------------------
    # Messaging
    # ------------------------------------------------------------------
    def _log_message(self, msg: dict):
        self.message_log.append(msg)
        if len(self.message_log) > self._max_log:
            self.message_log = self.message_log[-self._max_log:]

    async def broadcast(self, sender_id: str, channel: str, message: dict):
        """Broadcast message to all agents in a channel."""
        msg_record = {
            "id": str(uuid.uuid4()),
            "type": "broadcast",
            "sender": sender_id,
            "channel": channel,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._log_message(msg_record)

        recipients = [
            aid for aid in self.channels.get(channel, []) if aid != sender_id
        ]

        # Fire handlers concurrently
        tasks = []
        for aid in recipients:
            handler = self._agent_handlers.get(aid)
            if handler:
                tasks.append(self._safe_call(handler, msg_record))

        if tasks:
            await asyncio.gather(*tasks)

        # Also emit on event bus for real-time WebSocket push
        await event_bus.emit("chorus.broadcast", {
            "sender": sender_id,
            "channel": channel,
            "message": message,
            "recipients": recipients,
        })

    async def send(self, sender_id: str, recipient_id: str, message: dict) -> dict:
        """Direct message from one agent to another."""
        msg_record = {
            "id": str(uuid.uuid4()),
            "type": "direct",
            "sender": sender_id,
            "recipient": recipient_id,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "response": None,
        }

        handler = self._agent_handlers.get(recipient_id)
        if handler:
            response = await self._safe_call(handler, msg_record)
            msg_record["response"] = response
        else:
            msg_record["response"] = {"error": "no_handler", "agent": recipient_id}

        self._log_message(msg_record)
        return msg_record

    # ------------------------------------------------------------------
    # Delegation
    # ------------------------------------------------------------------
    async def delegate(self, from_agent: str, to_agent: str, task: dict) -> dict:
        """One agent delegates a subtask to another. Returns result."""
        delegation_id = str(uuid.uuid4())
        msg_record = {
            "id": delegation_id,
            "type": "delegation",
            "sender": from_agent,
            "recipient": to_agent,
            "task": task,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "pending",
            "result": None,
        }

        handler = self._agent_handlers.get(to_agent)
        if handler:
            try:
                result = await handler({
                    "type": "delegation",
                    "delegation_id": delegation_id,
                    "from": from_agent,
                    "task": task,
                })
                msg_record["status"] = "completed"
                msg_record["result"] = result
            except Exception as exc:
                msg_record["status"] = "failed"
                msg_record["result"] = {"error": str(exc)}
        else:
            msg_record["status"] = "failed"
            msg_record["result"] = {"error": f"Agent {to_agent} has no handler"}

        self._log_message(msg_record)

        await event_bus.emit("chorus.delegation", {
            "delegation_id": delegation_id,
            "from": from_agent,
            "to": to_agent,
            "status": msg_record["status"],
        })

        return msg_record

    # ------------------------------------------------------------------
    # Knowledge sharing
    # ------------------------------------------------------------------
    async def request_knowledge(self, requester: str, query: str) -> list[dict]:
        """Agent asks all other agents for relevant knowledge from their memories."""
        results: list[dict] = []

        tasks = {}
        for agent_id, provider in self._knowledge_providers.items():
            if agent_id != requester:
                tasks[agent_id] = self._safe_call(provider, query)

        if not tasks:
            return results

        gathered = await asyncio.gather(*tasks.values(), return_exceptions=True)
        for agent_id, resp in zip(tasks.keys(), gathered):
            if isinstance(resp, Exception):
                continue
            if isinstance(resp, list):
                for item in resp:
                    results.append({"source_agent": agent_id, **item})
            elif resp is not None:
                results.append({"source_agent": agent_id, "data": resp})

        self._log_message({
            "id": str(uuid.uuid4()),
            "type": "knowledge_request",
            "requester": requester,
            "query": query,
            "results_count": len(results),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        return results

    # ------------------------------------------------------------------
    # Voting / consensus
    # ------------------------------------------------------------------
    async def vote(self, agents: list[str], proposal: dict) -> dict:
        """Consensus mechanism — agents vote on a proposed action."""
        vote_id = str(uuid.uuid4())
        votes: dict[str, Any] = {}

        ballot = {
            "type": "vote_request",
            "vote_id": vote_id,
            "proposal": proposal,
        }

        tasks = {}
        for agent_id in agents:
            handler = self._agent_handlers.get(agent_id)
            if handler:
                tasks[agent_id] = self._safe_call(handler, ballot)

        if tasks:
            gathered = await asyncio.gather(*tasks.values(), return_exceptions=True)
            for agent_id, resp in zip(tasks.keys(), gathered):
                if isinstance(resp, Exception):
                    votes[agent_id] = {"vote": "abstain", "reason": str(resp)}
                elif isinstance(resp, dict):
                    votes[agent_id] = resp
                else:
                    votes[agent_id] = {"vote": "abstain", "reason": "invalid_response"}
        else:
            # No handlers — auto-abstain
            for agent_id in agents:
                votes[agent_id] = {"vote": "abstain", "reason": "no_handler"}

        # Tally
        approve = sum(1 for v in votes.values() if v.get("vote") == "approve")
        reject = sum(1 for v in votes.values() if v.get("vote") == "reject")
        abstain = len(votes) - approve - reject
        total = len(votes) or 1

        result = {
            "vote_id": vote_id,
            "proposal": proposal,
            "votes": votes,
            "tally": {"approve": approve, "reject": reject, "abstain": abstain},
            "consensus": approve > total / 2,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self._log_message({
            "id": vote_id,
            "type": "vote",
            **result,
        })

        await event_bus.emit("chorus.vote", result)
        return result

    # ------------------------------------------------------------------
    # Conversation history
    # ------------------------------------------------------------------
    def get_conversation(self, channel: str, limit: int = 50) -> list[dict]:
        """Get recent messages in a channel."""
        channel_msgs = [
            m for m in self.message_log
            if m.get("channel") == channel or m.get("type") == "direct"
            and (m.get("sender") in self.channels.get(channel, [])
                 or m.get("recipient") in self.channels.get(channel, []))
        ]
        return channel_msgs[-limit:]

    def get_agent_messages(self, agent_id: str, limit: int = 50) -> list[dict]:
        """Get all messages involving a specific agent."""
        relevant = [
            m for m in self.message_log
            if m.get("sender") == agent_id or m.get("recipient") == agent_id
        ]
        return relevant[-limit:]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    async def _safe_call(fn, *args):
        """Call async function catching exceptions."""
        try:
            return await fn(*args)
        except Exception as exc:
            return exc


# Global singleton
chorus = AgentChorus()
