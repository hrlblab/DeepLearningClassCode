# Advanced: The Same Agent with LangChain, LangGraph and MCP

This folder rebuilds the travel agent from [`Agent/firstAgent.py`](../Agent/firstAgent.py) with three widely used tools:

| Tool | Role in this agent |
|---|---|
| [MCP](https://modelcontextprotocol.io) (Model Context Protocol) | Publishes `get_weather` and `get_attraction` from a separate **tool server** that any MCP-compatible agent can use |
| [LangChain](https://python.langchain.com) | Connects to the LLM (`ChatOpenAI` on OpenRouter) and turns MCP tools into LangChain tools |
| [LangGraph](https://langchain-ai.github.io/langgraph/) | Runs the agent loop as a graph: `agent → tools → agent → …` until the LLM stops calling tools |

The task is the same: check today's weather in Nashville, then recommend an attraction that suits it.

## Files

```
advanced/
├── travel_mcp_server.py   # MCP server: exposes get_weather and get_attraction
├── langgraph_agent.py     # LangGraph agent: loads tools from the server and runs the loop
├── APIkeys.txt            # Your real keys (create it yourself)
└── README.md
```

## Quick start

You need an [OpenRouter](https://openrouter.ai/keys) API key and a [Tavily](https://www.tavily.com/) API key (free tier available).

```bash
pip install langchain langchain-openai langgraph langchain-mcp-adapters mcp tavily-python requests
python langgraph_agent.py
```

> **Never commit `APIkeys.txt`.** It is listed in `.gitignore`.

You do not need to start the MCP server yourself: the agent launches it as a subprocess.

Example output (trimmed):

```
Tools loaded from MCP server: ['get_weather', 'get_attraction']
User input: Hello, please help me check today's weather in Nashville, ...
========================================
[agent] Action: get_weather({'city': 'Nashville'})
[tools] Observation: Nashville current weather: Clear, temperature 11 degrees Celsius
========================================
[agent] Action: get_attraction({'city': 'Nashville', 'weather': 'Clear'})
[tools] Observation: In clear weather, Nashville offers several worthwhile tourist attractions. ...
========================================
[agent] Final answer: Today's weather in Nashville is clear ... I recommend visiting the Country Music Hall of Fame & Museum ...
```

## How it works

```
                 ┌──────────────────────────── LangGraph ───────────────────────────┐
  user request → │  START → [agent] ──tool_calls?──yes──→ [tools] ──┐               │
                 │             ↑   └──no──→ END (final answer)       │               │
                 │             └─────────────────────────────────────┘               │
                 └──────────────────────────────────────┬────────────────────────────┘
                                                         │ MCP over stdio
                                              travel_mcp_server.py
                                          (get_weather, get_attraction)
```

1. **MCP server** (`travel_mcp_server.py`): `@mcp.tool()` turns each function into an MCP tool. Its docstring and type hints become the description and input schema the LLM sees.
2. **MCP client** (`MultiServerMCPClient`): starts the server, asks it which tools it has, and wraps them as LangChain tools.
3. **LLM** (`ChatOpenAI(...).bind_tools(tools)`): sends the tool schemas to the model. The model replies with structured `tool_calls` instead of free text.
4. **Graph** (`StateGraph(MessagesState)`): the `agent` node calls the LLM; `tools_condition` routes to the `tools` node when there are tool calls, or ends; the `tools` node runs them and loops back.

## Compared with `firstAgent.py`

| Concept | `firstAgent.py` (by hand) | This folder (frameworks) |
|---|---|---|
| Tools | Functions in the same file | Served by a separate MCP server |
| Telling the LLM about tools | Listed by hand in the system prompt | Schemas sent automatically by `bind_tools` |
| Choosing an action | LLM writes `Action: get_weather(city="...")` as text | LLM returns structured `tool_calls` (function calling) |
| Parsing | Regex | None needed |
| Loop | `for i in range(5)` | LangGraph graph with `recursion_limit=10` |
| Memory | `prompt_history` list of strings | `MessagesState` list of chat messages |
| Stopping | LLM writes `Finish[...]` | LLM replies without tool calls |

The ideas are unchanged: **LLM + tools + loop**. The frameworks replace the fragile parts (prompt-listed tools, regex parsing) with structured APIs, and MCP makes the tools reusable by other agents.

## Try it

- **Reuse the MCP server elsewhere:** any MCP client (for example Claude Desktop or Cursor) can call these tools by running `python travel_mcp_server.py`.
- **Add a tool:** add a new `@mcp.tool()` function to the server. The agent picks it up automatically, with no change to the agent or the prompt.
- **Inspect the graph:** add `print(app.get_graph().draw_mermaid())` after `graph.compile()` and paste the output into [mermaid.live](https://mermaid.live).
