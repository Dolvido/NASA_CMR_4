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
        """
        Produce a two-stage CMR search plan:
        1) Expand concept terms using LLM-generated related terms
        2) Plan variable-first lookups, then map to related collections, then granules

        Returns plan dict with:
        - expanded_terms: list[str]
        - stages: [
            {
              "query": str,
              "variable_terms": list[str],
              "collection_params": dict,
              "granule_params": dict,
            }
          ]
        """
        base_terms: List[str] = []
        lowered = user_query.lower()
        # collect seeds from subqueries and user_query tokens
        seeds: List[str] = []
        seeds.extend([s.strip() for s in subqueries if s and len(s.strip()) > 0])
        # naive tokenization by spaces
        seeds.extend([t.strip() for t in lowered.replace(",", " ").split() if t.strip()])

        expanded = await self._expand_terms(seeds)

        # Build stages. Each subquery becomes a stage with shared expanded terms
        stages = []
        for sq in (subqueries or [user_query]):
            collection_params = {
                # Prefer richer fields in addition to keyword to avoid empty hits
                # These are recognized CMR query params for collections
                # short_name: collection short name
                # science_keywords_h: science keyword hierarchy
            }
            granule_params = {}
            # variable-first terms are the expanded list
            stages.append(
                {
                    "query": sq,
                    "variable_terms": list(dict.fromkeys(expanded)),  # de-duplicate preserve order
                    "collection_params": collection_params,
                    "granule_params": granule_params,
                }
            )

        return {"expanded_terms": list(dict.fromkeys(expanded)), "stages": stages}



