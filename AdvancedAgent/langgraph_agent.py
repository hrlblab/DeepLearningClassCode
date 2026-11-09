"""
The same travel agent as ../five_miniutes/firstAgent.py, rebuilt with LangChain + LangGraph + MCP.

  firstAgent.py (by hand)                 this file (frameworks)
  -------------------------------------   ------------------------------------------
  Tools = Python functions in the file    Tools served by an MCP server (travel_mcp_server.py)
  Tool list written in the system prompt  Tool schemas sent automatically (function calling)
  Regex parses "Action: ..." text         LLM returns structured tool_calls
  for-loop, at most 5 rounds              LangGraph graph: agent -> tools -> agent ...
  prompt_history list of strings          MessagesState (list of chat messages)
"""
import asyncio
import os
import sys
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

HERE = Path(__file__).resolve().parent

# --- 1. Load API keys from APIkeys.txt in this folder ---
with open(HERE / "APIkeys.txt") as f:
    for line in f:
        if "=" in line:
            name, value = line.strip().split("=", 1)
            os.environ.setdefault(name, value)

# --- 2. LLM (LangChain) ---
# ChatOpenAI works with any OpenAI-compatible API, here OpenRouter
llm = ChatOpenAI(
    model="openai/gpt-4.1-mini",
    api_key=os.environ["OPENROUTER_API_KEY"],
    base_url="https://openrouter.ai/api/v1",
    max_tokens=1024,
)

# Much shorter than AGENT_SYSTEM_PROMPT: no tool list and no output format,
# because tools and tool calls are handled by the API, not by parsing text.
SYSTEM_PROMPT = (
    "You are an intelligent travel assistant. Use the available tools step by step "
    "to answer the user's request, then give a short final recommendation."
)

USER_PROMPT = (
    "Hello, please help me check today's weather in Nashville, and then recommend "
    "a suitable tourist attraction based on the weather."
)


async def main():
    # --- 3. Tools from the MCP server ---
    # The client starts travel_mcp_server.py as a subprocess and asks it which tools it has
    client = MultiServerMCPClient({
        "travel": {
            "transport": "stdio",
            "command": sys.executable,
            "args": [str(HERE / "travel_mcp_server.py")],
        }
    })
    tools = await client.get_tools()
    print("Tools loaded from MCP server:", [t.name for t in tools])

    # Tell the LLM which tools exist (their names, descriptions and JSON schemas)
    llm_with_tools = llm.bind_tools(tools)

    # --- 4. The agent loop as a LangGraph graph ---
    async def agent(state: MessagesState):
        """Thought + Action: the LLM either answers or requests tool calls."""
        response = await llm_with_tools.ainvoke(
            [SystemMessage(SYSTEM_PROMPT)] + state["messages"]
        )
        return {"messages": [response]}

    graph = StateGraph(MessagesState)
    graph.add_node("agent", agent)
    graph.add_node("tools", ToolNode(tools))       # Observation: runs the requested tools
    graph.add_edge(START, "agent")
    # If the last AI message has tool_calls go to "tools", otherwise finish
    graph.add_conditional_edges("agent", tools_condition)
    graph.add_edge("tools", "agent")               # loop back with the results
    app = graph.compile()

    # --- 5. Run and print each step ---
    print(f"User input: {USER_PROMPT}\n" + "=" * 40)
    async for update in app.astream(
        {"messages": [HumanMessage(USER_PROMPT)]},
        {"recursion_limit": 10},   # safety limit, like range(5) in firstAgent.py
        stream_mode="updates",
    ):
        for node, data in update.items():
            for msg in data["messages"]:
                if isinstance(msg, AIMessage) and msg.tool_calls:
                    for call in msg.tool_calls:
                        print(f"[{node}] Action: {call['name']}({call['args']})")
                elif isinstance(msg, ToolMessage):
                    # MCP results arrive as content blocks; keep only their text
                    text = msg.content if isinstance(msg.content, str) else " ".join(
                        b.get("text", "") for b in msg.content if isinstance(b, dict))
                    print(f"[{node}] Observation: {text}\n" + "=" * 40)
                elif isinstance(msg, AIMessage):
                    print(f"[{node}] Final answer: {msg.content}")


if __name__ == "__main__":
    asyncio.run(main())

