from __future__ import annotations
from typing import Any, Dict
from datetime import datetime

class AnalysisAgent:
    async def run(self, cmr_results: dict) -> dict:
        searches = cmr_results.get('searches', []) if isinstance(cmr_results, dict) else []
        summary: dict[str, Any] = {'total_collections': 0, 'total_granules': 0, 'queries': []}
        for s in searches:
            cols = (s.get('collections') or {}).get('items', [])
            grans = (s.get('granules') or {}).get('items', [])
            summary['total_collections'] += len(cols)
            summary['total_granules'] += len(grans)
            providers = {((c.get('meta') or {}).get('provider-id') or 'unknown') for c in cols}
            titles = [(c.get('umm') or {}).get('ShortName') or (c.get('umm') or {}).get('LongName') for c in cols[:5]]
            summary['queries'].append({
                'query': s.get('query'),
                'collections_found': len(cols),
                'granules_found': len(grans),
                'providers': sorted([p for p in providers if p]),
                'example_collections': [t for t in titles if t],
            })
        return summary
