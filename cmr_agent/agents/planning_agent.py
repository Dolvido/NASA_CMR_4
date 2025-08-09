from __future__ import annotations

from typing import Dict, List


SYSTEM_PROMPT = (
    "You expand scientific terms with related synonyms or abbreviations. "
    "Respond as a JSON list of lowercase strings."
)


class PlanningAgent:
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

    async def _expand_terms(self, seeds: List[str]) -> List[str]:
        expanded: List[str] = []
        expanded.extend([s.lower() for s in seeds if s])
        if not self.llm or not seeds:
            return list(dict.fromkeys(expanded))
        import json
        prompt = f"{SYSTEM_PROMPT}\nTerms: {', '.join(seeds)}"
        try:
            msg = await self.llm.ainvoke(prompt)
            content = getattr(msg, 'content', str(msg))
            data = json.loads(content)
            if isinstance(data, list):
                for term in data:
                    if isinstance(term, str):
                        t = term.lower().strip()
                        if t and t not in expanded:
                            expanded.append(t)
        except Exception:
            pass
        return list(dict.fromkeys(expanded))

    async def run(self, user_query: str, subqueries: List[str]) -> Dict:
        """Create a high level execution plan for the CMR pipeline.

        The plan follows a variable → collection → granule search strategy and
        exposes explicit stage dependencies so the executor can schedule work in
        parallel where possible.
        """

        lowered = user_query.lower()
        seeds: List[str] = []
        seeds.extend([s.strip() for s in subqueries if s and len(s.strip()) > 0])
        seeds.extend([t.strip() for t in lowered.replace(",", " ").split() if t.strip()])

        expanded = await self._expand_terms(seeds)

        # Criteria shared across stages
        criteria = {"query": user_query, "expanded_terms": expanded}

        stages = [
            {
                "name": "collection_search",
                "type": "collection_search",
                "criteria": criteria,
                "depends_on": [],
            },
            {
                "name": "granule_search",
                "type": "granule_search",
                "criteria": criteria,
                "depends_on": ["collection_search"],
            },
            {
                "name": "variable_search",
                "type": "variable_search",
                "criteria": criteria,
                "depends_on": [],
            },
        ]

        return {"parallel": True, "expanded_terms": expanded, "stages": stages}



