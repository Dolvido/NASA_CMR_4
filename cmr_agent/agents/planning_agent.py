from __future__ import annotations

from typing import Dict, List, Tuple


# Minimal domain synonym map. This can be extended or loaded from a vector store later.
DOMAIN_SYNONYMS: Dict[str, List[str]] = {
    "rain": ["precipitation", "rainfall", "GPM", "IMERG", "TRMM"],
    "rainfall": ["precipitation", "GPM", "IMERG", "TRMM"],
    "precipitation": ["GPM", "IMERG", "TRMM", "rain"],
    "aerosol": ["aerosols", "PM2.5", "MAIAC", "MISR", "MODIS"],
    "air quality": ["PM2.5", "PM10", "NO2", "O3", "AOD", "aerosol"],
    "temperature": ["LST", "land surface temperature", "MODIS", "ECOSTRESS"],
    "soil moisture": ["SMAP", "SMOS", "ASCAT"],
    "vegetation": ["NDVI", "EVI", "MOD13", "VIIRS"],
    "wind": ["ASCAT", "wind speed", "wind direction"],
}


class PlanningAgent:
    async def run(self, user_query: str, subqueries: List[str]) -> Dict:
        """
        Produce a two-stage CMR search plan:
        1) Expand concept terms using domain synonyms
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

        expanded: List[str] = []
        for term in seeds:
            if term in expanded:
                continue
            expanded.append(term)
            # expand using DOMAIN_SYNONYMS where keys or substrings match
            for key, syns in DOMAIN_SYNONYMS.items():
                if key in term or term in key:
                    for s in syns:
                        if s.lower() not in expanded:
                            expanded.append(s.lower())

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



