from __future__ import annotations
from typing import Any

class SynthesisAgent:
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

    async def run(self, query: str, analysis: dict) -> str:
        if self.llm is None:
            # Templated fallback
            parts = [
                f"Query: {query}",
                f"Total collections: {analysis.get('total_collections', 0)}",
                f"Total granules: {analysis.get('total_granules', 0)}",
            ]
            for q in analysis.get('queries', [])[:3]:
                parts.append(
                    f"- '{q.get('query')}' -> collections={q.get('collections_found')}, granules={q.get('granules_found')}, providers={','.join(q.get('providers', []))}"
                )
            parts.append("Recommendations: refine temporal/spatial filters and select collections with consistent coverage.")
            return "\n".join(parts)
        prompt = (
            "You are an Earth science data expert. Given a user's query and analysis metadata (counts, examples), "
            "write a concise, structured recommendation: 1) Summary 2) Datasets to consider 3) Gaps & trade-offs 4) Next steps."
        )
        msg = await self.llm.ainvoke(f"{prompt}\nUser query: {query}\nAnalysis JSON: {analysis}")
        return getattr(msg, 'content', str(msg))
