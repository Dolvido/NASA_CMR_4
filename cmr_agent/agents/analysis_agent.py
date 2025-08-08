from __future__ import annotations
from typing import Any, Dict, List, Tuple
from datetime import datetime

class AnalysisAgent:
    async def run(
        self,
        cmr_results: dict,
        temporal_constraint: Tuple[str, str] | None = None,
        bbox_constraint: Tuple[float, float, float, float] | None = None,
    ) -> dict:
        searches = cmr_results.get('searches', []) if isinstance(cmr_results, dict) else []
        summary: dict[str, Any] = {
            'total_collections': 0,
            'total_granules': 0,
            'total_variables': 0,
            'queries': [],
        }

        knowledge_nodes = {"collections": set(), "variables": set(), "instruments": set()}
        knowledge_edges: List[Dict[str, str]] = []  # {source, target, type}

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

            # Instruments knowledge graph edges
            for c in cols:
                cid = (c.get('meta') or {}).get('concept-id')
                umm_c = (c.get('umm') or {})
                if cid:
                    knowledge_nodes["collections"].add(cid)
                platforms = umm_c.get('Platforms') or []
                if isinstance(platforms, dict):
                    platforms = [platforms]
                for p in platforms:
                    instruments = (p or {}).get('Instruments') or []
                    if isinstance(instruments, dict):
                        instruments = [instruments]
                    for instr in instruments:
                        name = (instr or {}).get('ShortName') or (instr or {}).get('LongName')
                        if name:
                            knowledge_nodes["instruments"].add(name)
                            if cid:
                                knowledge_edges.append({"source": cid, "target": name, "type": "collection-instrument"})

            # Variables knowledge graph edges
            for v in vars:
                vname = (v.get('umm') or {}).get('Name')
                if vname:
                    knowledge_nodes["variables"].add(vname)
                assocs = (v.get('associations') or {}).get('collections', [])
                for a in assocs:
                    cid = a.get('concept_id')
                    if cid and vname:
                        knowledge_edges.append({"source": vname, "target": cid, "type": "variable-collection"})

            # Compute simple latency/resolution placeholders if available on collections
            resolutions: List[str] = []
            latencies: List[int] = []
            for c in cols[:5]:
                umm_c = (c.get('umm') or {})
                # UMM-C often encodes processing level and granule spatial resolution in AdditionalAttributes
                addl = umm_c.get('AdditionalAttributes') or []
                for a in addl:
                    if isinstance(a, dict) and (a.get('Name') or '').lower().startswith('spatial resolution'):
                        val = (a.get('Values') or [])
                        if val:
                            resolutions.append(str(val[0]))
                # Simple heuristic latency: days since end coverage to now; if coverage available
            latency_days = None
            try:
                if end is not None:
                    latency_days = (datetime.utcnow() - end).days
            except Exception:
                latency_days = None

            # Estimate temporal gaps based on sorted granule temporal extents
            temporal_gaps: List[Dict[str, str]] = []
            try:
                intervals: List[tuple[datetime, datetime]] = []
                for g in grans:
                    umm = g.get('umm') or {}
                    te = (umm.get('TemporalExtent') or {}).get('RangeDateTime')
                    if te:
                        b = datetime.fromisoformat((te.get('BeginningDateTime') or '').replace('Z', '+00:00'))
                        e = datetime.fromisoformat((te.get('EndingDateTime') or '').replace('Z', '+00:00'))
                        intervals.append((b, e))
                intervals.sort(key=lambda x: x[0])
                for i in range(1, len(intervals)):
                    prev_end = intervals[i-1][1]
                    curr_start = intervals[i][0]
                    if curr_start > prev_end:
                        temporal_gaps.append({
                            'gap_start': prev_end.strftime('%Y-%m-%d'),
                            'gap_end': curr_start.strftime('%Y-%m-%d'),
                            'gap_days': str((curr_start - prev_end).days),
                        })
            except Exception:
                temporal_gaps = []

            # Constraint overlap scoring
            def temporal_overlap_days() -> int:
                if not (start and end and temporal_constraint):
                    return 0
                try:
                    req_start = datetime.fromisoformat(temporal_constraint[0].replace('Z', '+00:00'))
                    req_end = datetime.fromisoformat(temporal_constraint[1].replace('Z', '+00:00'))
                    latest_start = max(start, req_start)
                    earliest_end = min(end, req_end)
                    if latest_start <= earliest_end:
                        return (earliest_end - latest_start).days
                except Exception:
                    pass
                return 0

            def spatial_iou() -> float:
                if not (bbox and bbox_constraint):
                    return 0.0
                w1, s1, e1, n1 = bbox
                w2, s2, e2, n2 = bbox_constraint
                inter_w = max(w1, w2)
                inter_s = max(s1, s2)
                inter_e = min(e1, e2)
                inter_n = min(n1, n2)
                inter_area = max(0.0, inter_e - inter_w) * max(0.0, inter_n - inter_s)
                area1 = max(0.0, e1 - w1) * max(0.0, n1 - s1)
                area2 = max(0.0, e2 - w2) * max(0.0, n2 - s2)
                union = area1 + area2 - inter_area if area1 + area2 - inter_area > 0 else 1.0
                return inter_area / union

            t_days = temporal_overlap_days()
            s_iou = spatial_iou()
            res_score = 1.0 if resolutions else 0.0
            score = (t_days / 365.0) * 0.5 + s_iou * 0.3 + res_score * 0.2

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
                'resolutions': resolutions,
                'latency_days': latency_days,
                'temporal_gaps': temporal_gaps,
                'score': round(score, 3),
            })

        # Attach lightweight knowledge graph
        summary['knowledge_graph'] = {
            'nodes': {
                'collections': sorted(list(knowledge_nodes['collections'])),
                'variables': sorted(list(knowledge_nodes['variables'])),
                'instruments': sorted(list(knowledge_nodes['instruments'])),
            },
            'edges': knowledge_edges,
        }

        return summary
