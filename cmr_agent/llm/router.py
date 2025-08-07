from __future__ import annotations
from typing import Optional
from cmr_agent.config import settings

# Lazy-optional imports to avoid hard dependency issues
try:
    from langchain_openai import ChatOpenAI  # type: ignore
except Exception:
    ChatOpenAI = None  # type: ignore

try:
    from langchain_anthropic import ChatAnthropic  # type: ignore
except Exception:
    ChatAnthropic = None  # type: ignore

class LLMRouter:
    def __init__(self):
        self.primary: Optional[object] = None
        self.secondary: Optional[object] = None
        if settings.openai_api_key and ChatOpenAI is not None:
            self.primary = ChatOpenAI(model='gpt-4o-mini', temperature=0.2, api_key=settings.openai_api_key)
        if settings.anthropic_api_key and ChatAnthropic is not None:
            anthropic = ChatAnthropic(model='claude-3-5-sonnet-20240620', temperature=0.2, api_key=settings.anthropic_api_key)
            if self.primary is None:
                self.primary = anthropic
            else:
                self.secondary = anthropic

    def get(self) -> object:
        if self.primary is None and self.secondary is None:
            raise RuntimeError('No LLM providers configured')
        return self.primary or self.secondary

    def fallback(self) -> Optional[object]:
        return self.secondary
