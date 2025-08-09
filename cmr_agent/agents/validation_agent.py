from __future__ import annotations
from typing import Dict, List


class ValidationAgent:
    async def run(self, query: str, subqueries: list[str]) -> Dict:
        """Validate the user query and return structured feedback."""
        reasons: List[str] = []
        feasible = True

        if not query or not query.strip():
            feasible = False
            reasons.append('Empty query')

        if len(query) < 8:
            reasons.append('Very short query; may be ambiguous')

        # simple out-of-scope detection
        banned = ['medical records', 'social security', 'bank account']
        if any(b in query.lower() for b in banned):
            feasible = False
            reasons.append('Out-of-scope content detected')

        if len(subqueries) > 5:
            reasons.append('High complexity; will decompose into steps')

        return {
            'feasible': feasible,
            'reasons': reasons,
            'suggested_alternatives': []
        }
