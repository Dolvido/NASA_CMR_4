from __future__ import annotations
import re
from cmr_agent.types import IntentType

SYSTEM_PROMPT = (
    'You classify NASA CMR user queries into intents: exploratory, specific, or analytical. '
    'Return a JSON object with intent and decomposed subqueries.'
)

class IntentAgent:
    def __init__(self):
        try:
            from cmr_agent.llm.router import LLMRouter
            self.router = LLMRouter()
            try:
                self.llm = self.router.get()
            except Exception:
                self.llm = None
        except Exception:
            self.router = None
            self.llm = None

    async def run(self, query: str) -> tuple[IntentType, list[str]]:
        if self.llm is None:
            # heuristic fallback
            lowered = query.lower()
            if any(k in lowered for k in ['compare', 'relationship', 'impact', 'effect']):
                intent: IntentType = 'analytical'
            elif any(k in lowered for k in ['find', 'search', 'datasets', 'granules', 'variables']):
                intent = 'specific'
            else:
                intent = 'exploratory'
            # naive subquery split by 'and', commas
            parts = [p.strip() for p in re.split(r"[,;]|\band\b", query) if p.strip()]
            return intent, parts or [query]

        import json
        prompt = f"{SYSTEM_PROMPT}\nQuery: {query}\nRespond as JSON with keys: intent, subqueries."
        msg = await self.llm.ainvoke(prompt)
        content = getattr(msg, 'content', str(msg))
        intent: IntentType = 'exploratory'
        subqueries: list[str] = [query]
        try:
            data = json.loads(content)
            if 'intent' in data:
                intent = data['intent']  # type: ignore[assignment]
            if 'subqueries' in data and isinstance(data['subqueries'], list):
                subqueries = data['subqueries']
        except Exception:
            pass
        return intent, subqueries
