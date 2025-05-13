from typing import List
from typing import TypedDict, Annotated
from langgraph.graph.message import AnyMessage, add_messages
from langchain_core.runnables import RunnableLambda

from langgraph.prebuilt import ToolNode
from langchain_core.messages import ToolMessage
class plan_state(TypedDict):
    task: str
    messages: Annotated[list[AnyMessage], add_messages]
    plan: str
    steps: List
    steps2results: List
    # current_step: int
    documents: List
def handle_tool_error(state:plan_state) -> dict:
    error = state.get("error")
    tool_calls = state["messages"][-1].tool_calls
    return {
        "messages": [
            ToolMessage(
                content=f"Error: {repr(error)}\n please fix your mistakes.",
                tool_call_id=tc["id"],
            )
            for tc in tool_calls
        ]
    }
def create_tool_node_with_fallback(tools: list) -> dict:
    return ToolNode(tools).with_fallbacks(
        [RunnableLambda(handle_tool_error)], exception_key="error"
    )
