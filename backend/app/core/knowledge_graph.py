"""Gnosis Knowledge Graph — Entity-relationship graph from agent memory."""

import uuid
import re
import logging
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

logger = logging.getLogger("gnosis.knowledge_graph")


@dataclass
class Entity:
    id: str
    name: str
    entity_type: str  # person, organization, concept, tool, action, location
    agent_id: Optional[str] = None
    mentions: int = 1
    first_seen: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    last_seen: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    properties: dict = field(default_factory=dict)


@dataclass
class Relationship:
    id: str
    source_id: str
    target_id: str
    relation_type: str  # uses, creates, manages, belongs_to, relates_to, depends_on
    weight: float = 1.0
    context: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class KnowledgeGraphEngine:
    """Builds and queries a knowledge graph from agent interactions."""

    ENTITY_PATTERNS = {
        "person": r"\b([A-Z][a-z]+ [A-Z][a-z]+)\b",
        "organization": r"\b([A-Z][a-z]*(?:\s[A-Z][a-z]*)*(?:\sInc\.?|\sCorp\.?|\sLLC\.?|\sLtd\.?)?)\b",
        "tool": r"\b((?:Python|JavaScript|TypeScript|React|Node|Docker|Kubernetes|AWS|GCP|Azure|PostgreSQL|Redis|MongoDB|FastAPI|Next\.js|Git|GitHub|Slack|Jira))\b",
    }

    RELATION_KEYWORDS = {
        "uses": ["uses", "using", "utilized", "with"],
        "creates": ["creates", "created", "built", "generated", "produces"],
        "manages": ["manages", "manages", "handles", "controls"],
        "depends_on": ["depends on", "requires", "needs"],
        "relates_to": ["relates to", "connected to", "associated with", "about"],
    }

    def __init__(self):
        self._entities: Dict[str, Entity] = {}
        self._relationships: Dict[str, Relationship] = {}
        self._name_to_id: Dict[str, str] = {}  # normalized_name -> entity_id
        self._agent_entities: Dict[str, Set[str]] = {}  # agent_id -> entity_ids

    def _normalize(self, name: str) -> str:
        return name.strip().lower()

    def add_entity(
        self, name: str, entity_type: str, agent_id: str = None, properties: dict = None
    ) -> Entity:
        norm = self._normalize(name)
        if norm in self._name_to_id:
            entity = self._entities[self._name_to_id[norm]]
            entity.mentions += 1
            entity.last_seen = datetime.now(timezone.utc).isoformat()
            if properties:
                entity.properties.update(properties)
            return entity

        entity = Entity(
            id=str(uuid.uuid4()),
            name=name,
            entity_type=entity_type,
            agent_id=agent_id,
            properties=properties or {},
        )
        self._entities[entity.id] = entity
        self._name_to_id[norm] = entity.id
        if agent_id:
            self._agent_entities.setdefault(agent_id, set()).add(entity.id)
        return entity

    def add_relationship(
        self, source_name: str, target_name: str, relation_type: str, context: str = ""
    ) -> Optional[Relationship]:
        source_norm = self._normalize(source_name)
        target_norm = self._normalize(target_name)

        source_id = self._name_to_id.get(source_norm)
        target_id = self._name_to_id.get(target_norm)

        if not source_id or not target_id:
            return None

        # Check for existing relationship
        for rel in self._relationships.values():
            if (
                rel.source_id == source_id
                and rel.target_id == target_id
                and rel.relation_type == relation_type
            ):
                rel.weight += 1.0
                return rel

        rel = Relationship(
            id=str(uuid.uuid4()),
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            context=context[:200],
        )
        self._relationships[rel.id] = rel
        return rel

    def extract_from_text(self, text: str, agent_id: str = None) -> dict:
        """Extract entities and relationships from text."""
        entities_found = []

        # Extract known tool entities
        for match in re.finditer(self.ENTITY_PATTERNS["tool"], text):
            entity = self.add_entity(match.group(1), "tool", agent_id)
            entities_found.append(entity)

        # Extract person-like names
        for match in re.finditer(self.ENTITY_PATTERNS["person"], text):
            name = match.group(1)
            if len(name.split()) == 2 and not any(
                w in name.lower() for w in ["the", "this", "that"]
            ):
                entity = self.add_entity(name, "person", agent_id)
                entities_found.append(entity)

        # Extract relationships based on keywords
        rels_found = []
        for rel_type, keywords in self.RELATION_KEYWORDS.items():
            for keyword in keywords:
                pattern = rf"(\w+(?:\s\w+)?)\s+{keyword}\s+(\w+(?:\s\w+)?)"
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    source, target = match.group(1).strip(), match.group(2).strip()
                    # Only create relationship if both entities exist
                    if (
                        self._normalize(source) in self._name_to_id
                        and self._normalize(target) in self._name_to_id
                    ):
                        rel = self.add_relationship(
                            source, target, rel_type, context=match.group(0)
                        )
                        if rel:
                            rels_found.append(rel)

        return {
            "entities_extracted": len(entities_found),
            "relationships_extracted": len(rels_found),
        }

    def get_graph(self, agent_id: str = None) -> dict:
        """Get the full graph as nodes + edges for visualization."""
        if agent_id:
            entity_ids = self._agent_entities.get(agent_id, set())
            nodes = [self._entities[eid] for eid in entity_ids if eid in self._entities]
            edges = [
                r
                for r in self._relationships.values()
                if r.source_id in entity_ids or r.target_id in entity_ids
            ]
        else:
            nodes = list(self._entities.values())
            edges = list(self._relationships.values())

        return {
            "nodes": [
                {
                    "id": n.id,
                    "name": n.name,
                    "type": n.entity_type,
                    "mentions": n.mentions,
                    "properties": n.properties,
                }
                for n in nodes
            ],
            "edges": [
                {
                    "id": e.id,
                    "source": e.source_id,
                    "target": e.target_id,
                    "type": e.relation_type,
                    "weight": e.weight,
                }
                for e in edges
            ],
            "node_count": len(nodes),
            "edge_count": len(edges),
        }

    def get_entity_neighborhood(self, entity_name: str, depth: int = 1) -> dict:
        """Get an entity and its connected entities."""
        norm = self._normalize(entity_name)
        entity_id = self._name_to_id.get(norm)
        if not entity_id:
            return {"error": "Entity not found"}

        visited = {entity_id}
        nodes = [self._entities[entity_id]]
        edges = []

        frontier = {entity_id}
        for _ in range(depth):
            next_frontier = set()
            for eid in frontier:
                for rel in self._relationships.values():
                    if rel.source_id == eid and rel.target_id not in visited:
                        next_frontier.add(rel.target_id)
                        edges.append(rel)
                    elif rel.target_id == eid and rel.source_id not in visited:
                        next_frontier.add(rel.source_id)
                        edges.append(rel)
            visited.update(next_frontier)
            nodes.extend(
                [self._entities[eid] for eid in next_frontier if eid in self._entities]
            )
            frontier = next_frontier

        return {
            "nodes": [
                {
                    "id": n.id,
                    "name": n.name,
                    "type": n.entity_type,
                    "mentions": n.mentions,
                }
                for n in nodes
            ],
            "edges": [
                {
                    "id": e.id,
                    "source": e.source_id,
                    "target": e.target_id,
                    "type": e.relation_type,
                    "weight": e.weight,
                }
                for e in edges
            ],
        }

    def search_entities(self, query: str, entity_type: str = None) -> List[Entity]:
        query_lower = query.lower()
        results = [e for e in self._entities.values() if query_lower in e.name.lower()]
        if entity_type:
            results = [e for e in results if e.entity_type == entity_type]
        return sorted(results, key=lambda e: e.mentions, reverse=True)

    @property
    def stats(self) -> dict:
        type_counts = {}
        for e in self._entities.values():
            type_counts[e.entity_type] = type_counts.get(e.entity_type, 0) + 1
        return {
            "total_entities": len(self._entities),
            "total_relationships": len(self._relationships),
            "entity_types": type_counts,
        }


knowledge_graph_engine = KnowledgeGraphEngine()
