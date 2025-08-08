from __future__ import annotations
from typing import Any, Dict, List
from datetime import datetime

class AnalysisAgent:
    async def run(self, cmr_results: dict) -> dict:
        searches = cmr_results.get('searches', []) if isinstance(cmr_results, dict) else []
        summary: dict[str, Any] = {
            'total_collections': 0,
            'total_granules': 0,
            'total_variables': 0,
            'queries': [],
        }

        for s in searches:
            cols = (s.get('collections') or {}).get('items', [])
            grans = (s.get('granules') or {}).get('items', [])
            vars = (s.get('variables') or {}).get('items', [])

            summary['total_collections'] += len(cols)
            summary['total_granules'] += len(grans)
            summary['total_variables'] += len(vars)

            providers = {((c.get('meta') or {}).get('provider-id') or 'unknown') for c in cols}
            titles = [
                (c.get('umm') or {}).get('ShortName') or (c.get('umm') or {}).get('LongName')
                for c in cols[:5]
            ]

            # temporal coverage and spatial extent from granules
            start: datetime | None = None
            end: datetime | None = None
            bbox: List[float] | None = None  # [west, south, east, north]

            for g in grans:
                umm = g.get('umm') or {}

                # Temporal
                te = (umm.get('TemporalExtent') or {}).get('RangeDateTime')
                if te:
                    try:
                        b = datetime.fromisoformat(
                            (te.get('BeginningDateTime') or '').replace('Z', '+00:00')
                        )
                        e = datetime.fromisoformat(
                            (te.get('EndingDateTime') or '').replace('Z', '+00:00')
                        )
                        start = b if start is None or b < start else start
                        end = e if end is None or e > end else end
                    except Exception:
                        # Skip malformed timestamps
                        continue

                # Spatial
                se = (umm.get('SpatialExtent') or {})
                geom = (se.get('HorizontalSpatialDomain') or {}).get('Geometry') or {}
                boxes = geom.get('BoundingBox') or geom.get('BoundingRectangles') or []
                if isinstance(boxes, dict):
                    boxes = [boxes]
                for box in boxes:
                    try:
                        w = float(box.get('WestBoundingCoordinate'))
                        s_ = float(box.get('SouthBoundingCoordinate'))
                        e_ = float(box.get('EastBoundingCoordinate'))
                        n = float(box.get('NorthBoundingCoordinate'))
                        if bbox is None:
                            bbox = [w, s_, e_, n]
                        else:
                            bbox = [
                                min(bbox[0], w),
                                min(bbox[1], s_),
                                max(bbox[2], e_),
                                max(bbox[3], n),
                            ]
                    except Exception:
                        # Skip malformed boxes
                        continue

            coverage: Dict[str, Any] = {}
            if start and end:
                coverage = {
                    'start': start.strftime('%Y-%m-%d'),
                    'end': end.strftime('%Y-%m-%d'),
                }

            spatial: Dict[str, Any] = {}
            if bbox:
                spatial = {'bbox': bbox}

            example_vars: List[str] = []
            related: List[str] = []
            for v in vars[:5]:
                name = (v.get('umm') or {}).get('Name')
                if name:
                    example_vars.append(name)
                assocs = (v.get('associations') or {}).get('collections', [])
                for a in assocs:
                    cid = a.get('concept_id')
                    if cid:
                        related.append(cid)

            summary['queries'].append({
                'query': s.get('query'),
                'collections_found': len(cols),
                'granules_found': len(grans),
                'variables_found': len(vars),
                'providers': sorted([p for p in providers if p]),
                'example_collections': [t for t in titles if t],
                'example_variables': example_vars,
                'temporal_coverage': coverage,
                'spatial_extent': spatial,
                'related_collections': sorted(set(related)),
            })

        return summary
