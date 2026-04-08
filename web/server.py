"""
Web server — The Support Layer.

FastAPI + WebSocket backend, equivalent to web/server.py in the spy game.
Manages game sessions, manual + auto mode, and real-time state broadcast.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import uuid
from dataclasses import dataclass, field

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

# Add parent dir to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from support_desk_game.core.support_agent import SupportAgent
from support_desk_game.core.support_desk import SupportDesk, TicketStatus
from support_desk_game.core.micro_shift import create_micro_shift, MICRO_WIN_CSAT, MICRO_MAX_TURNS
from support_desk_game.core.tools import DeskTools, ToolResult
from support_desk_game.core.agent import parse_tool_call, build_observation, SHIFT_BRIEFING
from support_desk_game.core.serialization import game_state_to_dict, turn_event_to_dict
from support_desk_game.core.oracle import LLMOracle

app = FastAPI(title="The Support Layer")

# Serve static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------

@dataclass
class GameSession:
    agent: SupportAgent
    desk: SupportDesk
    tools: DeskTools
    turn: int = 0
    max_turns: int = MICRO_MAX_TURNS
    win_csat: int = MICRO_WIN_CSAT
    history: list[dict] = field(default_factory=list)
    auto_running: bool = False
    auto_task: asyncio.Task | None = None
    last_active: float = field(default_factory=time.time)
    game_log: list[dict] = field(default_factory=list)
    gemini_client: object = None


sessions: dict[str, GameSession] = {}

# Gemini API key (set via env or UI)
gemini_api_key: str | None = os.environ.get("GEMINI_API_KEY")


def create_session() -> tuple[str, GameSession]:
    """Create a fresh game session."""
    agent, desk = create_micro_shift()
    oracle = _make_oracle()
    tools = DeskTools(agent, desk, oracle)
    session_id = uuid.uuid4().hex[:8]
    session = GameSession(agent=agent, desk=desk, tools=tools)
    sessions[session_id] = session
    return session_id, session


def _make_oracle():
    """Create an oracle based on available API key."""
    if gemini_api_key:
        try:
            from google import genai
            client = genai.Client(api_key=gemini_api_key)
            return LLMOracle(client=client)
        except ImportError:
            pass
    return None  # Falls back to stub oracle in DeskTools


# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    """Serve the main page."""
    from fastapi.responses import FileResponse
    return FileResponse(os.path.join(static_dir, "index.html"))


@app.post("/api/game/new")
async def new_game():
    """Create a new game session."""
    session_id, session = create_session()
    state = game_state_to_dict(session.agent, session.desk, session.turn, session.max_turns, session.win_csat)
    return {"session_id": session_id, "state": state}


@app.get("/api/game/{session_id}")
async def get_game(session_id: str):
    """Get the current game state."""
    session = sessions.get(session_id)
    if not session:
        return JSONResponse({"error": "Session not found"}, status_code=404)
    state = game_state_to_dict(session.agent, session.desk, session.turn, session.max_turns, session.win_csat)
    return state


@app.get("/api/game/{session_id}/log")
async def get_log(session_id: str):
    """Download the structured game log."""
    session = sessions.get(session_id)
    if not session:
        return JSONResponse({"error": "Session not found"}, status_code=404)
    return session.game_log


@app.get("/api/key/status")
async def key_status():
    """Check if a Gemini API key is configured."""
    return {"configured": gemini_api_key is not None}


@app.post("/api/key")
async def set_key(payload: dict):
    """Set the Gemini API key at runtime."""
    global gemini_api_key
    key = payload.get("key", "").strip()
    if not key:
        return JSONResponse({"error": "No key provided"}, status_code=400)
    gemini_api_key = key
    os.environ["GEMINI_API_KEY"] = key
    return {"configured": True}


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------

@app.websocket("/ws/game/{session_id}")
async def ws_game(ws: WebSocket, session_id: str):
    await ws.accept()
    session = sessions.get(session_id)
    if not session:
        await ws.send_json({"type": "error", "message": "Session not found"})
        await ws.close()
        return

    try:
        while True:
            data = await ws.receive_json()
            msg_type = data.get("type")
            session.last_active = time.time()

            if msg_type == "manual_action":
                await handle_manual_action(ws, session, data)

            elif msg_type == "start_auto":
                system_prompt = data.get("system_prompt", "")
                think_code = data.get("think_code", "")
                await handle_start_auto(ws, session, system_prompt, think_code)

            elif msg_type == "stop_auto":
                await handle_stop_auto(ws, session)

            elif msg_type == "reset":
                session = await handle_reset(ws, session_id)

            elif msg_type == "get_state":
                state = game_state_to_dict(session.agent, session.desk, session.turn, session.max_turns, session.win_csat)
                await ws.send_json({"type": "state_update", "state": state})

    except WebSocketDisconnect:
        if session.auto_task and not session.auto_task.done():
            session.auto_task.cancel()
            session.auto_running = False


# ---------------------------------------------------------------------------
# Manual mode handler
# ---------------------------------------------------------------------------

async def handle_manual_action(ws: WebSocket, session: GameSession, data: dict):
    """Execute a single manual action."""
    tool_name = data.get("tool", "view_inbox")
    args = data.get("args", {})

    if not session.agent.is_alive:
        await ws.send_json({"type": "error", "message": "Agent crashed (context budget = 0). Reset to play again."})
        return
    if session.agent.csat_stars >= session.win_csat:
        await ws.send_json({"type": "error", "message": "You already won! Reset for a new shift."})
        return
    if session.turn >= session.max_turns:
        await ws.send_json({"type": "error", "message": "Shift is over (max turns reached). Reset for a new shift."})
        return

    session.turn += 1

    # Execute the action
    result = session.tools.execute(tool_name, args)

    # Tick patience
    expired_ids = session.desk.tick_all_patience()
    if expired_ids:
        result = ToolResult(
            result.success,
            result.message + f"\n⚠ Ticket(s) expired: {', '.join(expired_ids)}"
        )

    # Log
    log_entry = {
        "turn": session.turn,
        "tool": tool_name,
        "args": args,
        "result": result.message,
        "success": result.success,
    }
    session.history.append(log_entry)
    session.game_log.append(log_entry)

    # Build state and send
    state = game_state_to_dict(session.agent, session.desk, session.turn, session.max_turns, session.win_csat)
    event = turn_event_to_dict(session.turn, f"{tool_name}({json.dumps(args)})", result.message, state)
    await ws.send_json(event)

    # Check game over
    if not session.agent.is_alive:
        await ws.send_json({"type": "game_over", "won": False, "reason": "Context budget exhausted — agent crashed!",
                            "state": state})
    elif session.agent.csat_stars >= session.win_csat:
        await ws.send_json({"type": "game_over", "won": True, "reason": "Target CSAT reached — shift complete!",
                            "state": state})
    elif session.turn >= session.max_turns:
        await ws.send_json({"type": "game_over", "won": False, "reason": "Shift ended — out of turns.",
                            "state": state})


# ---------------------------------------------------------------------------
# Auto mode handler
# ---------------------------------------------------------------------------

async def handle_start_auto(ws: WebSocket, session: GameSession, system_prompt: str, think_code: str):
    """Start the auto agent loop."""
    if session.auto_running:
        await ws.send_json({"type": "error", "message": "Auto mode already running."})
        return

    session.auto_running = True

    async def auto_loop():
        consecutive_errors = 0
        max_errors = 3

        while session.auto_running and session.agent.is_alive and session.turn < session.max_turns:
            if session.agent.csat_stars >= session.win_csat:
                break

            session.turn += 1

            # PERCEIVE
            observation = build_observation(session.agent, session.desk, session.tools)
            if session.turn == 1 or not session.history:
                briefing = SHIFT_BRIEFING.format(
                    win_csat=session.win_csat,
                    context_budget=session.agent.context_budget,
                    csat_stars=session.agent.csat_stars,
                    turn=session.turn,
                    max_turns=session.max_turns,
                    snippets=session.agent.snippets or "none",
                    current_ticket=session.agent.current_ticket_id or "none (in inbox)",
                    tools_description=session.tools.available_tools_description(),
                )
                observation = briefing + "\n\n" + observation

            # THINK (call LLM)
            try:
                thought = await think_llm(
                    session.agent, session.desk, session.history,
                    system_prompt=system_prompt,
                )
            except Exception as e:
                consecutive_errors += 1
                await ws.send_json({"type": "error", "message": f"Think error: {e}"})
                if consecutive_errors >= max_errors:
                    session.auto_running = False
                    await ws.send_json({"type": "error", "message": "Too many consecutive errors. Auto mode stopped."})
                    break
                continue

            consecutive_errors = 0

            # PARSE
            tool_name, args = parse_tool_call(thought)

            # ACT
            result = session.tools.execute(tool_name, args)

            # TICK patience
            expired_ids = session.desk.tick_all_patience()
            if expired_ids:
                result = ToolResult(
                    result.success,
                    result.message + f"\n⚠ Ticket(s) expired: {', '.join(expired_ids)}"
                )

            # LOG
            log_entry = {
                "turn": session.turn,
                "thought": thought,
                "tool": tool_name,
                "args": args,
                "result": result.message,
                "success": result.success,
            }
            session.history.append(log_entry)
            session.game_log.append(log_entry)

            # BROADCAST
            state = game_state_to_dict(session.agent, session.desk, session.turn, session.max_turns, session.win_csat)
            event = turn_event_to_dict(session.turn, f"{tool_name}({json.dumps(args)})", result.message, state)
            event["thought"] = thought
            try:
                await ws.send_json(event)
            except Exception:
                session.auto_running = False
                break

            # Check game over
            if not session.agent.is_alive:
                await ws.send_json({"type": "game_over", "won": False,
                                    "reason": "Context budget exhausted — agent crashed!", "state": state})
                break
            elif session.agent.csat_stars >= session.win_csat:
                await ws.send_json({"type": "game_over", "won": True,
                                    "reason": "Target CSAT reached — shift complete!", "state": state})
                break
            elif session.turn >= session.max_turns:
                await ws.send_json({"type": "game_over", "won": False,
                                    "reason": "Shift ended — out of turns.", "state": state})
                break

            await asyncio.sleep(0.8)

        session.auto_running = False

    session.auto_task = asyncio.create_task(auto_loop())


async def handle_stop_auto(ws: WebSocket, session: GameSession):
    """Stop the auto agent loop."""
    session.auto_running = False
    if session.auto_task and not session.auto_task.done():
        session.auto_task.cancel()
    await ws.send_json({"type": "auto_stopped"})


async def handle_reset(ws: WebSocket, session_id: str) -> GameSession:
    """Reset the game session."""
    old = sessions.get(session_id)
    if old and old.auto_task and not old.auto_task.done():
        old.auto_task.cancel()
        old.auto_running = False

    agent, desk = create_micro_shift()
    oracle = _make_oracle()
    tools = DeskTools(agent, desk, oracle)
    session = GameSession(agent=agent, desk=desk, tools=tools)
    sessions[session_id] = session

    state = game_state_to_dict(agent, desk, 0, session.max_turns, session.win_csat)
    await ws.send_json({"type": "reset_complete", "state": state})
    return session


# ---------------------------------------------------------------------------
# LLM think function for auto mode
# ---------------------------------------------------------------------------

async def think_llm(
    agent: SupportAgent,
    desk: SupportDesk,
    history: list[dict],
    system_prompt: str = "",
) -> str:
    """Call Gemini to generate the agent's next action."""
    if not gemini_api_key:
        raise RuntimeError("No Gemini API key configured. Set via UI or GEMINI_API_KEY env var.")

    from google import genai

    client = genai.Client(api_key=gemini_api_key)

    # Build conversation context
    context_parts = []
    if system_prompt:
        context_parts.append(system_prompt)

    # Include recent history (last 10 turns)
    recent = history[-10:]
    for h in recent:
        context_parts.append(f"Turn {h['turn']}: {h.get('tool', '?')}({h.get('args', {})}) → {h.get('result', '')[:200]}")

    # Current observation
    from support_desk_game.core.tools import DeskTools
    obs = build_observation(agent, desk, None)
    context_parts.append(f"\nCurrent state:\n{obs}")
    context_parts.append("\nWhat is your next action? Reply with TOOL: tool_name(args)")

    prompt = "\n\n".join(context_parts)

    # Call Gemini
    response = await asyncio.to_thread(
        client.models.generate_content,
        model="gemini-2.5-flash",
        contents=prompt,
        config={"system_instruction": SHIFT_BRIEFING.format(
            win_csat=3, context_budget=agent.context_budget,
            csat_stars=agent.csat_stars, turn=len(history) + 1,
            max_turns=30, snippets=agent.snippets or "none",
            current_ticket=agent.current_ticket_id or "none",
            tools_description="(see briefing above)",
        ), "temperature": 0.3},
    )
    return response.text


# ---------------------------------------------------------------------------
# Session cleanup
# ---------------------------------------------------------------------------

async def cleanup_sessions():
    """Remove inactive sessions (>1 hour)."""
    while True:
        await asyncio.sleep(300)
        now = time.time()
        stale = [sid for sid, s in sessions.items() if now - s.last_active > 3600]
        for sid in stale:
            s = sessions.pop(sid, None)
            if s and s.auto_task and not s.auto_task.done():
                s.auto_task.cancel()


@app.on_event("startup")
async def startup():
    asyncio.create_task(cleanup_sessions())


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
