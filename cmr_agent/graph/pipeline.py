from __future__ import annotations
from typing import Any, Dict
from langgraph.graph import StateGraph, END
from cmr_agent.types import QueryState
from cmr_agent.agents.intent_agent import IntentAgent
from cmr_agent.agents.validation_agent import ValidationAgent
from cmr_agent.agents.cmr_agent import CMRAgent
from cmr_agent.agents.analysis_agent import AnalysisAgent
from cmr_agent.agents.synthesis_agent import SynthesisAgent
from cmr_agent.agents.retrieval_agent import RetrievalAgent
from cmr_agent.utils import infer_temporal, infer_bbox

# Use the TypedDict-defined state schema
StateType = QueryState

# Nodes
async def start_step(state: StateType) -> StateType:
    history = state.get('history', [])
    history.append(state.get('user_query', ''))
    state['history'] = history
    return state

async def intent_step(state: StateType) -> StateType:
    agent = IntentAgent()
    intent, subqueries = await agent.run(state['user_query'])
    state.update({'intent': intent, 'subqueries': subqueries})
    start, end = infer_temporal(state['user_query'])
    bbox = infer_bbox(state['user_query'])
    if start and end:
        state['temporal'] = (start, end)
    if bbox:
        state['bbox'] = bbox
    # retrieve context for better downstream reasoning
    retriever = RetrievalAgent()
    state['context'] = {'retrieved': retriever.store.similarity_search(state['user_query'], k=5)}
    return state

async def validation_step(state: StateType) -> StateType:
    agent = ValidationAgent()
    ok, notes = await agent.run(state['user_query'], state.get('subqueries', []))
    state.update({'validated': ok, 'validation_notes': notes})
    return state

async def cmr_step(state: StateType) -> StateType:
    agent = CMRAgent()
    try:
        res = await agent.run(state['user_query'], state.get('subqueries', []))
        state['cmr_results'] = res
    finally:
        await agent.close()
    return state

async def analysis_step(state: StateType) -> StateType:
    agent = AnalysisAgent()
    state['analysis'] = await agent.run(state.get('cmr_results', {}))
    return state

async def synthesis_step(state: StateType) -> StateType:
    agent = SynthesisAgent()
    state['synthesis'] = await agent.run(
        state['user_query'], state.get('analysis', {}), state.get('history', [])
    )
    return state

# Graph construction

def build_graph():
    graph = StateGraph(StateType)
    graph.add_node('start_step', start_step)
    graph.add_node('intent_step', intent_step)
    graph.add_node('validation_step', validation_step)
    graph.add_node('cmr_step', cmr_step)
    graph.add_node('analysis_step', analysis_step)
    graph.add_node('synthesis_step', synthesis_step)

    graph.set_entry_point('start_step')
    graph.add_edge('start_step', 'intent_step')
    graph.add_edge('intent_step', 'validation_step')

    def route_after_validation(state: StateType):
        return 'cmr_step' if state.get('validated') else 'synthesis_step'

    graph.add_conditional_edges('validation_step', route_after_validation, {
        'cmr_step': 'cmr_step',
        'synthesis_step': 'synthesis_step',
    })

    graph.add_edge('cmr_step', 'analysis_step')
    graph.add_edge('analysis_step', 'synthesis_step')
    graph.add_edge('synthesis_step', END)

    return graph.compile()

