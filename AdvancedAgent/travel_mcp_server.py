"""
MCP server that exposes the two travel tools from firstAgent.py.

MCP (Model Context Protocol) is a standard way to publish tools so that ANY
MCP-compatible agent (LangGraph, Claude Desktop, Cursor, ...) can discover and
call them. The agent never imports these functions: it starts this file as a
separate process and talks to it over stdin/stdout.

Run on its own (for debugging):  python travel_mcp_server.py
Normally it is started automatically by langgraph_agent.py.
"""
import os
from pathlib import Path

import requests
from mcp.server.fastmcp import FastMCP
from tavily import TavilyClient

# Load TAVILY_API_KEY from APIkeys.txt in this folder
KEY_FILE = Path(__file__).resolve().parent / "APIkeys.txt"
with open(KEY_FILE) as f:
    for line in f:
        if "=" in line:
            name, value = line.strip().split("=", 1)
            os.environ.setdefault(name, value)

mcp = FastMCP("travel", log_level="WARNING")  # quiet: hide per-request logs


# The docstring and type hints become the tool description and input schema
# that the LLM sees. No hand-written "# Available Tools" prompt is needed.
@mcp.tool()
def get_weather(city: str) -> str:
    """Get the current real-time weather for a city."""
    url = f"https://wttr.in/{city}?format=j1"
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        current = response.json()["current_condition"][0]
        desc = current["weatherDesc"][0]["value"]
        temp_c = current["temp_C"]
        return f"{city} current weather: {desc}, temperature {temp_c} degrees Celsius"
    except requests.exceptions.RequestException as e:
        return f"Error: network problem when querying weather - {e}"
    except (KeyError, IndexError) as e:
        return f"Error: failed to parse weather data, city name may be invalid - {e}"


@mcp.tool()
def get_attraction(city: str, weather: str) -> str:
    """Search the web for tourist attractions in a city that suit the given weather."""
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return "Error: TAVILY_API_KEY is not configured."
    query = f"'{city}' most worthwhile tourist attractions and reasons in '{weather}' weather"
    try:
        response = TavilyClient(api_key=api_key).search(
            query=query, search_depth="basic", include_answer=True
        )
        if response.get("answer"):
            return response["answer"]
        results = [f"- {r['title']}: {r['content']}" for r in response.get("results", [])]
        return "\n".join(results) or "Sorry, no relevant attractions found."
    except Exception as e:
        return f"Error: Tavily search failed - {e}"


if __name__ == "__main__":
    # stdio transport: messages travel over stdin/stdout, so never print() here
    mcp.run(transport="stdio")
