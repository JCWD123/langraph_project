from langchain_core.messages import ToolMessage

from graph.state import plan_state
from langgraph.prebuilt import tools_condition
from langgraph.graph.state import StateGraph, CompiledStateGraph, END
def decide_to_tool(state: plan_state):
    current_step = state["current_step"]
    route = tools_condition(state)
    # if route == END:
    #     return END
    if state["messages"][-1].tool_calls:
        for call in state["messages"][-1].tool_calls:
            if 'name' in call:
                return call['name']
    else:
        if len(state['steps']) == current_step:
            return "report_agent"
        return "update_plan_agent"
def Rout2SolveAgent(state:plan_state):
    current_step = state["current_step"]
    if len(state["messages"]) > 0 and isinstance(state["messages"][-1], ToolMessage):
        if f"step{current_step + 1}" in state["steps2results"]:
            state["steps2results"][f"step{current_step + 1}"]['tool_message'] = state["messages"][-1]
    return "solve_agent"
