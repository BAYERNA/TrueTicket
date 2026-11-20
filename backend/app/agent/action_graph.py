from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from ..services.actions import execute_action


class ActionState(TypedDict, total=False):
    case_id: str
    type: str
    approval_id: str
    document: dict
    approval: dict
    result: dict


def build_action_graph(db, checkpointer):
    def approve(state):
        decision = interrupt({"case_id": state["case_id"], "type": state["type"],
                              "approval_id": state["approval_id"], "document": state["document"]})
        return {"approval": decision}

    def execute(state):
        return {"result": execute_action(db, state)}

    graph = StateGraph(ActionState)
    graph.add_node("human_approval", approve)
    graph.add_node("execute_action", execute)
    graph.add_edge(START, "human_approval")
    graph.add_edge("human_approval", "execute_action")
    graph.add_edge("execute_action", END)
    return graph.compile(checkpointer=checkpointer)
