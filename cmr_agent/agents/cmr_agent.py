from __future__ import annotations

import asyncio
from typing import Any, Dict

from cmr_agent.cmr.client import AsyncCMRClient
from cmr_agent.config import settings
from cmr_agent.utils import infer_temporal, infer_bbox


class CMRAgent:
    def __init__(self):
        self.client = AsyncCMRClient(settings.cmr_base_url)

    async def run(self, query: str, subqueries: list[str]) -> dict:
        async def search_for(q: str) -> dict:
            temporal = infer_temporal(q)
            bbox = infer_bbox(q)
            params: Dict[str, Any] = {
                "page_size": 25,
                "keyword": q,
            }
            provider = getattr(settings, "cmr_provider", None)
            if provider and provider not in ("", "ALL", "CMR_ALL"):
                params["provider"] = provider
            if temporal[0] and temporal[1]:
                params["temporal"] = f"{temporal[0]},{temporal[1]}"
            if bbox:
                w, s, e, n = bbox
                params["bounding_box"] = f"{w},{s},{e},{n}"

            collections_task = self.client.search_collections(params)

            async def granules(params: Dict[str, Any]) -> dict:
                try:
                    cols = await collections_task
                    items = (cols or {}).get("items", [])
                    if items:
                        concept_ids = [i.get("meta", {}).get("concept-id") for i in items if i.get("meta")]
                        gid = concept_ids[0]
                        gparams = {k: v for k, v in params.items() if k != "page_size"}
                        if gid:
                            gparams["collection_concept_id"] = gid
                        gparams["page_size"] = 50
                        return await self.client.search_granules(gparams)
                except Exception:
                    pass
                return {"items": []}

            variables_task = self.client.search_variables({"keyword": q, "page_size": 25})

            results = await asyncio.gather(
                collections_task, granules(params), variables_task, return_exceptions=True
            )
            collections, granules_res, variables_res = results
            return {
                "query": q,
                "collections": collections if isinstance(collections, dict) else {"error": str(collections)},
                "granules": granules_res if isinstance(granules_res, dict) else {"error": str(granules_res)},
                "variables": variables_res if isinstance(variables_res, dict) else {"error": str(variables_res)},
            }

        searches = await asyncio.gather(*(search_for(q) for q in (subqueries or [query])))
        return {"searches": searches}

    async def close(self):
        await self.client.close()
