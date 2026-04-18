"""Gnosis Prompt Compressor — Compress long prompts to fit token limits."""
import logging
import re

logger = logging.getLogger("gnosis.prompt_compressor")

FILLER_WORDS = [
    "actually", "basically", "certainly", "definitely", "essentially",
    "honestly", "just", "literally", "obviously", "really", "simply",
    "surely", "totally", "very", "absolutely", "perhaps", "maybe",
    "quite", "rather", "somewhat", "particularly", "specifically",
]

ABBREVIATIONS = {
    "do not": "don't",
    "can not": "can't",
    "will not": "won't",
    "would not": "wouldn't",
    "should not": "shouldn't",
    "is not": "isn't",
    "are not": "aren't",
    "have not": "haven't",
    "has not": "hasn't",
    "for example": "e.g.",
    "that is": "i.e.",
    "in other words": "i.e.",
    "and so on": "etc.",
}


class PromptCompressorEngine:
    def __init__(self, avg_chars_per_token: float = 4.0):
        self._avg_chars_per_token = avg_chars_per_token

    def estimate_tokens(self, text: str) -> int:
        return max(1, int(len(text) / self._avg_chars_per_token))

    def _remove_filler_words(self, text: str) -> str:
        for word in FILLER_WORDS:
            text = re.sub(rf'\b{word}\b\s*', '', text, flags=re.IGNORECASE)
        return re.sub(r'\s+', ' ', text).strip()

    def _apply_abbreviations(self, text: str) -> str:
        for full, abbrev in ABBREVIATIONS.items():
            text = re.sub(rf'\b{full}\b', abbrev, text, flags=re.IGNORECASE)
        return text

    def _remove_redundant_whitespace(self, text: str) -> str:
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        return text.strip()

    def _truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        max_chars = int(max_tokens * self._avg_chars_per_token)
        if len(text) <= max_chars:
            return text
        truncated = text[:max_chars]
        last_space = truncated.rfind(' ')
        if last_space > max_chars * 0.8:
            truncated = truncated[:last_space]
        return truncated + "..."

    def compress(self, text: str, max_tokens: int = 0) -> dict:
        original_tokens = self.estimate_tokens(text)
        compressed = self._remove_redundant_whitespace(text)
        compressed = self._remove_filler_words(compressed)
        compressed = self._apply_abbreviations(compressed)
        compressed = self._remove_redundant_whitespace(compressed)
        if max_tokens > 0:
            compressed = self._truncate_to_tokens(compressed, max_tokens)
        compressed_tokens = self.estimate_tokens(compressed)
        savings = round(1 - compressed_tokens / max(1, original_tokens), 2) if original_tokens > 0 else 0.0
        logger.info(f"Compressed prompt: {original_tokens} -> {compressed_tokens} tokens ({savings:.0%} savings)")
        return {
            "original_text": text,
            "compressed_text": compressed,
            "original_tokens": original_tokens,
            "compressed_tokens": compressed_tokens,
            "savings_pct": savings,
        }


prompt_compressor_engine = PromptCompressorEngine()
