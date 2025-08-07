from __future__ import annotations
import re, asyncio
from datetime import datetime
from typing import Any, Dict, Tuple
from cmr_agent.cmr.client import AsyncCMRClient
from cmr_agent.config import settings

REGION_TO_BBOX = {
    'sub-saharan africa': (-20.0, -35.0, 52.0, 20.0),
    'ssa': (-20.0, -35.0, 52.0, 20.0),
    'global': (-180.0, -90.0, 180.0, 90.0),
}

def infer_temporal(text: str) -> Tuple[str | None, str | None]:
    # capture full 4-digit years 1900-2099
    years = [int(y) for y in re.findall(r"((?:19|20)\d{2})", text)]
    if len(years) >= 2:
        years.sort()
        return f"{years[0]}-01-01T00:00:00Z", f"{years[-1]}-12-31T23:59:59Z"
    return None, None

def infer_bbox(text: str) -> Tuple[float, float, float, float] | None:
    lowered = text.lower()
    for key, bbox in REGION_TO_BBOX.items():
        if key in lowered:
            w, s, e, n = bbox
            return w, s, e, n
    return None

class CMRAgent:
    def __init__(self):
        self.client = AsyncCMRClient(settings.cmr_base_url)

    async def run(self, query: str, subqueries: list[str]) -> dict:
        async def search_for(q: str) -> dict:
            temporal = infer_temporal(q)
            bbox = infer_bbox(q)
            params: Dict[str, Any] = {
                'page_size': 25,
                'keyword': q,
            }
            # Only constrain provider if configured differently than default 'CMR_ALL'
            provider = getattr(settings, 'cmr_provider', None)
            if provider and provider not in ('', 'ALL', 'CMR_ALL'):
                params['provider'] = provider
            if temporal[0] and temporal[1]:
                params['temporal'] = f"{temporal[0]},{temporal[1]}"
            if bbox:
                w, s, e, n = bbox
                params['bounding_box'] = f"{w},{s},{e},{n}"
            collections_task = self.client.search_collections(params)
            async def granules(params: Dict[str, Any]) -> dict:
                try:
                    cols = await collections_task
                    items = (cols or {}).get('items', [])
                    if items:
                        concept_ids = [i.get('meta', {}).get('concept-id') for i in items if i.get('meta')]
                        gid = concept_ids[0]
                        gparams = {k: v for k, v in params.items() if k != 'page_size'}
                        if gid:
                            gparams['collection_concept_id'] = gid
                        gparams['page_size'] = 50
                        return await self.client.search_granules(gparams)
                except Exception:
                    pass
                return {'items': []}
            results = await asyncio.gather(collections_task, granules(params), return_exceptions=True)
            collections, granules_res = results
            return {
                'query': q,
                'collections': collections if isinstance(collections, dict) else {'error': str(collections)},
                'granules': granules_res if isinstance(granules_res, dict) else {'error': str(granules_res)},
            }
        searches = await asyncio.gather(*(search_for(q) for q in (subqueries or [query])))
        return {'searches': searches}

    async def close(self):
        await self.client.close()
