"""
Utility functions for context detection only.
Language detection is handled by LLM.
"""
from typing import Dict
from config import CONTEXT_PATTERNS


def detect_lease_context(text: str) -> Dict[str, bool]:
    """
    Detect specific lease contexts from user message.
    Used to inject contextual clauses (furnished, commercial, etc.) into the prompt.

    Returns:
        Dictionary of detected contexts, e.g. {'furnished': True, 'commercial': False, ...}
    """
    text_lower = text.lower()
    return {
        key: any(word in text_lower for word in patterns)
        for key, patterns in CONTEXT_PATTERNS.items()
    }