# Claude Agent SDK: Weather Tool Example

**Group:** Elijah and Lookman

A user asks "What is the weather in New York?", the agent calls a custom `get_weather` tool, and Claude answers with live data.

## Overview

The Claude Agent SDK is Anthropic's library for building agents in Python or TypeScript. It first shipped in 2025 as the Claude Code SDK and was renamed the Claude Agent SDK later that year. It packages the agent loop, built-in tools, context management, permissions, sessions and hooks that power Claude Code, so you can embed that agent in your own app. Packages: `claude-agent-sdk` (Python) and `@anthropic-ai/claude-agent-sdk` (TypeScript).

## 1. What it replaces

- **The loop itself:** it calls the model, runs the tools Claude asks for, sends back the results and repeats until Claude is done. You write tool functions and read a stream of messages.
- **Tools:** built-in Read, Write, Edit, Bash, Glob, Grep, WebSearch and WebFetch, plus your own tools through MCP (in-process with `@tool`, or external servers).
- **State and persistence:** each session's history is saved to disk automatically. You can resume or fork a session by its ID, and long conversations are compacted automatically when they fill the context window.
- **Retries and errors:** the runtime retries API errors. If a tool throws, the error goes back to Claude as a tool result and the loop keeps going, so Claude can retry or change approach.
- **Approvals:** permission modes, allow/deny lists, a `can_use_tool` callback and hooks.
- **Tracing:** every tool call and result arrives as a typed message, and the final `ResultMessage` reports turns, usage and cost. Hooks let you log each step, and OpenTelemetry export is available through Claude Code's telemetry settings. There is no hosted tracing dashboard like LangSmith.

## 2. Execution model

One model-driven loop, not a graph or a crew. Claude repeats "gather context → act with tools → check the result" until the task is done, and can hand focused subtasks to subagents.

```
query(prompt) ─► Claude ─► tool_use? ──yes──► permission check ─► run tool ─► result ─┐
                   ▲                                                                 │
                   └─────────────────────────────────────────────────────────────────┘
                   no ─► ResultMessage (final answer)
```

Under the hood, the SDK runs the Claude Code engine as a subprocess and streams messages back to your code.

## 3. State and human approval

- **State** is the conversation transcript plus whatever the agent writes to the filesystem. There is no typed state object like in LangGraph. Sessions are stored on disk; continue one with `resume=<session_id>` or branch it with `fork_session`.
- **Human in the loop:**
  - `permission_mode` sets the overall policy (`default`, `acceptEdits`, `plan`, `bypassPermissions`).
  - `allowed_tools` / `disallowed_tools` pre-approve or block specific tools.
  - The `can_use_tool` callback asks your code (and through it, a human) before each tool call, and can allow it, deny it or change its input.
  - `PreToolUse` hooks can allow, deny or ask before a tool runs.
  - The agent can ask the user clarifying questions mid-task.

## 4. Use it when / skip it when

**Use it when** the agent needs to work on files or a computer for many steps: coding agents (bug fixing, refactoring, PR review), research agents that search, read and write a report, ops or data agents that run scripts and inspect logs, document-processing agents.

**Skip it when:**
- **It's a single LLM call** (classification, extraction, chat). The plain Claude API is cheaper and faster.
- **You need a fixed, deterministic workflow** with explicit branches and checkpoints. LangGraph or your own loop fits better.
- **You want Anthropic to host the agent.** Use Managed Agents.
- **Latency and cost per request matter a lot.** The full Claude Code engine adds overhead (one weather question cost about $0.51 in our run).
- **Your backend isn't Python or TypeScript.** Other languages can only drive it as a CLI subprocess.

## Implementation

[`weather.py`](weather.py) defines a `get_weather(city)` tool with `@tool`, wraps it with `create_sdk_mcp_server`, and passes it to `query()`. It pre-approves the tool with `allowed_tools=["mcp__weather__get_weather"]` and sets `tools=[]` so the agent has no built-in tools. Weather data comes from [Open-Meteo](https://open-meteo.com/) (free, no API key).

### Run it

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=your-key   # or be logged in to Claude Code locally
python weather.py
python weather.py "What's the weather in Chicago?"
```

### Sample output

```
[tool call] mcp__weather__get_weather({'city': 'New York'})

It's clear in New York right now, with a temperature of 60.8°F (feels like 57.1°F) and a light wind at 5.6 mph.

[success] turns=2 cost=$0.5092
```
