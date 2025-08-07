from __future__ import annotations
from typing import Tuple

class ValidationAgent:
    async def run(self, query: str, subqueries: list[str]) -> tuple[bool, str]:
        if not query or not query.strip():
            return False, 'Empty query'
        notes: list[str] = []
        if len(query) < 8:
            notes.append('Very short query; may be ambiguous')
        # simple out-of-scope detection
        banned = ['medical records', 'social security', 'bank account']
        if any(b in query.lower() for b in banned):
            return False, 'Out-of-scope content detected'
        if len(subqueries) > 5:
            notes.append('High complexity; will decompose into steps')
        return True, '; '.join(notes)
