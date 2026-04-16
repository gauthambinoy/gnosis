"""Gnosis Persona Inheritance — Parent persona templates with trait inheritance."""
import uuid
import logging
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional

logger = logging.getLogger("gnosis.persona_inheritance")


@dataclass
class PersonaTemplate:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    base_traits: dict = field(default_factory=dict)
    overridable: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PersonaInheritanceEngine:
    def __init__(self):
        self._templates: Dict[str, PersonaTemplate] = {}

    def create_template(self, name: str, base_traits: dict = None, overridable: List[str] = None) -> PersonaTemplate:
        template = PersonaTemplate(name=name, base_traits=base_traits or {},
                                   overridable=overridable or list((base_traits or {}).keys()))
        self._templates[template.id] = template
        logger.info(f"Created persona template: {template.id} ({name})")
        return template

    def get_template(self, template_id: str) -> Optional[PersonaTemplate]:
        return self._templates.get(template_id)

    def list_templates(self) -> List[dict]:
        return [asdict(t) for t in self._templates.values()]

    def delete_template(self, template_id: str) -> bool:
        if template_id in self._templates:
            del self._templates[template_id]
            return True
        return False

    def inherit(self, template_id: str, overrides: dict = None) -> dict:
        template = self._templates.get(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")
        merged = dict(template.base_traits)
        if overrides:
            for key, value in overrides.items():
                if key in template.overridable:
                    merged[key] = value
                else:
                    logger.warning(f"Trait '{key}' is not overridable in template {template_id}")
        return {"template_id": template_id, "template_name": template.name, "merged_traits": merged}


persona_inheritance_engine = PersonaInheritanceEngine()
