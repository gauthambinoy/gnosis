"""Gnosis Context Assembler — compresses memory context into <800 token prompts."""

from app.core.memory_engine import MemoryContext


MAX_CONTEXT_TOKENS = 800
CHARS_PER_TOKEN = 4  # rough estimate


class ContextAssembler:
    """Assembles compressed context from memory retrieval for LLM prompts."""

    def assemble(self, context: MemoryContext, trigger_summary: str = "") -> str:
        """Build a compressed context string under 800 tokens."""
        sections = []
        budget = MAX_CONTEXT_TOKENS * CHARS_PER_TOKEN  # ~3200 chars

        # 1. CORRECTIONS — always included in full (highest priority)
        if context.corrections:
            correction_text = "CORRECTIONS (OBEY THESE FIRST):\n"
            for c in context.corrections[:5]:
                correction_text += f"• {self._truncate(c.content, 200)}\n"
            sections.append(correction_text)
            budget -= len(correction_text)

        # 2. TRIGGER — what just happened
        if trigger_summary:
            trigger_text = f"CURRENT TRIGGER:\n{self._truncate(trigger_summary, 300)}\n"
            sections.append(trigger_text)
            budget -= len(trigger_text)

        # 3. PROCEDURES — how to handle similar situations
        if context.procedures and budget > 200:
            proc_text = "PROCEDURES:\n"
            for p in context.procedures[:3]:
                line = f"• {self._truncate(p.content, 150)}\n"
                if len(proc_text) + len(line) < budget // 3:
                    proc_text += line
            sections.append(proc_text)
            budget -= len(proc_text)

        # 4. RELEVANT KNOWLEDGE — semantic facts
        if context.knowledge and budget > 200:
            know_text = "KNOWLEDGE:\n"
            for k in context.knowledge[:3]:
                line = f"• {self._truncate(k.content, 150)}\n"
                if len(know_text) + len(line) < budget // 3:
                    know_text += line
            sections.append(know_text)
            budget -= len(know_text)

        # 5. RECENT CONTEXT — from sensory buffer
        if context.recent and budget > 100:
            recent_text = "RECENT:\n"
            for r in context.recent[-3:]:
                line = f"• {self._truncate(r.content, 100)}\n"
                if len(recent_text) + len(line) < budget:
                    recent_text += line
            sections.append(recent_text)

        assembled = "\n".join(sections)

        # Final safety truncation
        max_chars = MAX_CONTEXT_TOKENS * CHARS_PER_TOKEN
        if len(assembled) > max_chars:
            assembled = assembled[: max_chars - 3] + "..."

        return assembled

    def estimate_tokens(self, text: str) -> int:
        return len(text) // CHARS_PER_TOKEN

    def _truncate(self, text: str, max_chars: int) -> str:
        if len(text) <= max_chars:
            return text
        return text[: max_chars - 3] + "..."


# Global singleton
context_assembler = ContextAssembler()
