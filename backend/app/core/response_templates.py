"""Gnosis Response Templates — Format agent responses in various output formats."""
import uuid
import logging
import json
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional

logger = logging.getLogger("gnosis.response_templates")


@dataclass
class ResponseTemplate:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    format: str = "markdown"  # markdown/json/plain/html/table
    structure: str = ""
    example: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ResponseTemplateEngine:
    VALID_FORMATS = {"markdown", "json", "plain", "html", "table"}

    def __init__(self):
        self._templates: Dict[str, ResponseTemplate] = {}

    def create_template(self, name: str, format: str = "markdown", structure: str = "",
                        example: str = "") -> ResponseTemplate:
        if format not in self.VALID_FORMATS:
            raise ValueError(f"Invalid format: {format}. Must be one of {self.VALID_FORMATS}")
        template = ResponseTemplate(name=name, format=format, structure=structure, example=example)
        self._templates[template.id] = template
        logger.info(f"Created response template: {template.id} ({name})")
        return template

    def get_template(self, template_id: str) -> Optional[ResponseTemplate]:
        return self._templates.get(template_id)

    def list_templates(self) -> List[dict]:
        return [asdict(t) for t in self._templates.values()]

    def update_template(self, template_id: str, **kwargs) -> Optional[ResponseTemplate]:
        template = self._templates.get(template_id)
        if not template:
            return None
        for k, v in kwargs.items():
            if hasattr(template, k) and k not in ("id", "created_at"):
                setattr(template, k, v)
        return template

    def delete_template(self, template_id: str) -> bool:
        if template_id in self._templates:
            del self._templates[template_id]
            return True
        return False

    def apply_template(self, content: str, template_id: str) -> str:
        template = self._templates.get(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")
        fmt = template.format
        if fmt == "markdown":
            return f"# Response\n\n{content}\n"
        elif fmt == "json":
            return json.dumps({"content": content, "template": template.name}, indent=2)
        elif fmt == "html":
            return f"<div class='response'><h2>{template.name}</h2><p>{content}</p></div>"
        elif fmt == "table":
            lines = content.split("\n")
            header = "| # | Content |"
            separator = "|---|---------|"
            rows = "\n".join(f"| {i+1} | {line} |" for i, line in enumerate(lines) if line.strip())
            return f"{header}\n{separator}\n{rows}"
        else:
            return content


response_template_engine = ResponseTemplateEngine()
