# CLAUDE.md — Project Context for AI Agents

## What This Is

**The Hidden Layer** is an LLM-powered spy-themed coding exercise for teaching agentic AI. Students provide a system prompt; the framework calls Gemini to drive an agent through a grid-based mission, collecting dossiers, talking to NPCs, and defeating robots.

## Repo Structure

```
agentic_ai_spy/              # Core game engine (DO NOT break student-facing API)
  hidden_layer/
    agent.py                 # Agent loop, think_llm(), parse_tool_call()
    oracle.py                # NPC dialogue: stub (keyword) + LLM (Gemini)
    game_world.py            # Map, cells, NPCs, items, facilities
    operative.py             # Player state (health, dossiers, inventory, position)
    tools.py                 # 5 tools: scan, move, talk, collect, fabricate
    micro_mission.py         # 3x3 simplified mission for web app
    serialization.py         # Game state → JSON (fog of war)
    display.py               # Notebook visualization
  the_hidden_layer_*.ipynb   # 6 Jupyter notebooks (training/micro/full + solutions)
  requirements.txt           # google-genai

web/                         # FastAPI web server + frontend
  server.py                  # REST + WebSocket API, session management, auto mode
  requirements.txt           # fastapi, uvicorn, google-genai, google-api-core
  static/                    # React frontend (served as static files)

tests/
  test_serialization.py
```

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, Uvicorn, WebSockets
- **LLM**: Google Gemini API (`google-genai`, model: `gemini-2.5-flash`)
- **Frontend**: React, served as static files via FastAPI
- **Education**: Jupyter notebooks

## Key Architecture

### Game Loop (auto mode)
```
scan() → think_llm(state, history) → Gemini API → parse TOOL: call → execute tool → repeat
```

### Tool Call Format
Parser (`parse_tool_call` in `agent.py`) accepts:
1. `TOOL: move(direction="east")` — canonical format
2. `move(direction="east")` — bare call fallback (LLMs often skip the prefix)

Known tools: `move`, `talk`, `collect`, `fabricate`, `scan`

### Web Server (`web/server.py`)
- Sessions tracked in-memory by session ID
- WebSocket at `/ws/game/{session_id}` for manual and auto mode
- Auto mode: runs agent loop async, sends `turn_update` events, stops on 3 consecutive errors
- Gemini API key configurable at runtime via `POST /api/key`

### Oracle (`oracle.py`)
- `gemini_call_with_retry()`: exponential backoff on rate limits
- `google.api_core` import is optional (graceful fallback if missing)
- Stub oracle as fallback when no API key is set

## Common Pitfalls

- **LLM response parsing**: Gemini often omits the `TOOL:` prefix — the parser handles this
- **`google.api_core` dependency**: May not be installed; oracle retry handles ImportError gracefully
- **Tool execution errors in auto loop**: Wrapped in try-except so one bad turn doesn't crash the loop
- **Port conflicts**: Server cleans up orphaned processes on startup

## Development Guidelines

- Students only provide a system prompt — they don't modify `hidden_layer/` code
- Don't break the student-facing API: `think_llm()`, `parse_tool_call()`, tool signatures
- The web app uses the **micro mission** (3x3 grid, 3 dossiers, 30 turns max)
- Notebooks use the **full mission** (8x8 grid, 10 dossiers, 100 turns max)
- Game logs are JSON files with per-turn state, useful for debugging agent behavior
