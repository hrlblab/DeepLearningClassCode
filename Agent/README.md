# Your First Agent in 5 Minutes

A minimal LLM agent, written in plain Python, that solves a task step by step with the **Thought → Action → Observation** loop.

Given the request:

> *Hello, please help me check today's weather in Nashville, and then recommend a suitable tourist attraction based on the weather.*

the agent:

1. **Thinks** about what it needs, then calls `get_weather` to get live weather from [wttr.in](https://wttr.in).
2. **Observes** the result, then calls `get_attraction` to search the web with [Tavily](https://www.tavily.com/) for attractions that suit that weather.
3. **Finishes** with a recommendation using `Finish[...]`.

Adapted from [Hello-Agents, Chapter 1.3](https://datawhalechina.github.io/hello-agents/#/en/chapter1/Chapter1-Introduction-to-Agents?id=_13-hands-on-experience-implementing-your-first-agent-in-5-minutes) by Datawhale.

## Project structure

```
.
├── firstAgent.py          # The agent: prompt, tools, LLM client, main loop
├── APIkeys.txt            # Your real keys (create it yourself)
└── README.md
```

## Quick start

### 1. Install dependencies

Requires Python 3.9+.

```bash
pip install requests tavily-python openai
```

| Package | Purpose |
|---|---|
| `requests` | HTTP calls to the weather API |
| `tavily-python` | Web search for attraction recommendations |
| `openai` | Client for OpenRouter's OpenAI-compatible API |

### 2. Get API keys

| Key | Where to get it | Used for |
|---|---|---|
| `OPENROUTER_API_KEY` | [openrouter.ai/keys](https://openrouter.ai/keys) | The LLM that does the thinking |
| `TAVILY_API_KEY` | [tavily.com](https://www.tavily.com/) (free tier available) | Searching for attractions |

The weather tool uses wttr.in, which needs no key.

### 3. Add your keys

Copy the template and fill in your own keys:

```bash
cp APIkeys.example.txt APIkeys.txt
```

```
OPENROUTER_API_KEY=sk-or-v1-...
TAVILY_API_KEY=tvly-...
```

`firstAgent.py` loads every `KEY=value` line from `APIkeys.txt` into environment variables at startup, so no key is ever written in the code.

> **Never commit `APIkeys.txt`.** It is listed in `.gitignore`. If a key is ever pushed to GitHub, revoke it and create a new one.

### 4. Run

```bash
python firstAgent.py
```

Example output (trimmed):

```
User input: Hello, please help me check today's weather in Nashville, ...
========================================
--- Loop 1 ---
Thought: I need to first get the current weather in Nashville ...
Action: get_weather(city="Nashville")
Observation: Nashville current weather: Clear, temperature ... degrees Celsius
========================================
--- Loop 2 ---
Thought: The weather is clear and mild. Now I should find suitable attractions ...
Action: get_attraction(city="Nashville", weather="Clear")
Observation: ...
========================================
--- Loop 3 ---
Action: Finish[Nashville's clear weather and mild temperature make it perfect for visiting ...]
Task completed, final answer: ...
```

The agent stops after `Finish[...]`, or after at most 5 loops.

## How it works

| Component | Role |
|---|---|
| `AGENT_SYSTEM_PROMPT` | Tells the LLM its role, the available tools, and the required `Thought:` / `Action:` output format |
| `get_weather(city)` | Tool: fetches current weather from wttr.in |
| `get_attraction(city, weather)` | Tool: searches Tavily for attractions that suit the weather |
| `OpenAICompatibleClient` | Sends the prompt history to the LLM on OpenRouter |
| Main loop | Parses each `Action` with regex, runs the matching tool, and appends the `Observation` to the history for the next step |

## Customize

- **Change the question:** edit `user_prompt` in `firstAgent.py`, for example to another city.
- **Change the model:** set `MODEL_ID` to any model ID listed at [openrouter.ai/models](https://openrouter.ai/models) (default: `openai/gpt-4.1-mini`).
- **Use another provider:** any OpenAI-compatible service works. Change `BASE_URL`, `MODEL_ID`, and the key name.
- **Add a tool:** write a Python function, add it to `available_tools`, and describe it in `AGENT_SYSTEM_PROMPT`.

## Troubleshooting

| Error | Fix |
|---|---|
| `FileNotFoundError: ... APIkeys.txt` | Create `APIkeys.txt` next to `firstAgent.py` (see step 3) |
| `KeyError: 'OPENROUTER_API_KEY'` | Check the key name and the `KEY=value` format in `APIkeys.txt` |
| `Error code: 401` | The OpenRouter key is wrong or revoked |
| `Error code: 402` | Not enough OpenRouter credit: add credit or raise the key's limit |
| `Error: TAVILY_API_KEY environment variable not configured.` | Add `TAVILY_API_KEY` to `APIkeys.txt` |
