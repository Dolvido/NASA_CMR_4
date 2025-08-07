import asyncio
import json
import sys
from cmr_agent.graph.pipeline import build_graph

async def main():
    query = ' '.join(sys.argv[1:]) or 'Find precipitation datasets for Sub-Saharan Africa 2015-2023'
    graph = build_graph()
    result = await graph.ainvoke({'user_query': query})
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    asyncio.run(main())
