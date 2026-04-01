"""Backend API + WebSocket server for The Hidden Layer micro mission."""

from __future__ import annotations

import sys
import os
import asyncio
import logging
import textwrap
import time
import uuid
from dataclasses import dataclass, field

# Add parent dir to path so hidden_layer is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agentic_ai_spy"))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from hidden_layer.operative import Operative
from hidden_layer.tools import GameTools, ToolResult
from hidden_layer.oracle import llm_oracle
from hidden_layer.agent import MISSION_BRIEFING, TOOLS_DESCRIPTION, parse_tool_call
from hidden_layer.serialization import game_state_to_dict, turn_event_to_dict
from hidden_layer.micro_mission import (
    MicroGameWorld,
    MicroGameTools,
    MICRO_NPC_CATALOG,
    micro_stub_oracle,
    MICRO_MISSION_BRIEFING,
    create_micro_game,
)

logger = logging.getLogger("spy_server")
logging.basicConfig(level=logging.INFO)

# ---------------------------------------------------------------------------
# Gemini client setup
# ---------------------------------------------------------------------------

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
gemini_client = None

if GEMINI_API_KEY:
    try:
        from google import genai
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
        logger.info("Gemini client initialized. LLM oracle and auto mode available.")
    except Exception as e:
        logger.warning(f"Failed to initialize Gemini client: {e}")
else:
    logger.warning(
        "GEMINI_API_KEY not set. Using stub oracle. "
        "Auto mode LLM calls will be rejected."
    )

# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------

MAX_TURNS = 30


@dataclass
class GameSession:
    operative: Operative
    world: MicroGameWorld
    tools: MicroGameTools
    turn: int = 0
    history: list = field(default_factory=list)
    max_turns: int = MAX_TURNS
    auto_running: bool = False
    auto_task: asyncio.Task | None = None
    last_active: float = field(default_factory=time.time)


sessions: dict[str, GameSession] = {}


def create_session() -> tuple[str, GameSession]:
    """Create a new game session with the micro mission."""
    session_id = uuid.uuid4().hex[:12]
    operative, world, tools = create_micro_game()

    # Set oracle
    if gemini_client:
        tools.set_oracle(lambda npc, q, o: llm_oracle(npc, q, o, gemini_client))
    else:
        tools.set_oracle(micro_stub_oracle)

    session = GameSession(operative=operative, world=world, tools=tools)
    sessions[session_id] = session
    return session_id, session


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(title="The Hidden Layer — Micro Mission")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Session cleanup background task
# ---------------------------------------------------------------------------

async def cleanup_sessions():
    """Remove sessions inactive for more than 1 hour."""
    while True:
        await asyncio.sleep(300)  # check every 5 minutes
        now = time.time()
        expired = [
            sid for sid, s in sessions.items()
            if now - s.last_active > 3600
        ]
        for sid in expired:
            session = sessions.pop(sid, None)
            if session and session.auto_task and not session.auto_task.done():
                session.auto_task.cancel()
            logger.info(f"Cleaned up expired session {sid}")


@app.on_event("startup")
async def startup():
    asyncio.create_task(cleanup_sessions())


# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------

@app.post("/api/game/new")
async def new_game():
    """Create a new game session."""
    session_id, session = create_session()
    state = game_state_to_dict(session.operative, session.world, 0, session.max_turns)
    return {
        "session_id": session_id,
        "state": state,
        "mission_briefing": MICRO_MISSION_BRIEFING,
    }


@app.get("/api/game/{session_id}")
async def get_game(session_id: str):
    """Get current game state."""
    session = sessions.get(session_id)
    if not session:
        return {"error": "Session not found"}
    session.last_active = time.time()
    state = game_state_to_dict(session.operative, session.world, session.turn, session.max_turns)
    return {"session_id": session_id, "state": state}


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------

@app.websocket("/ws/game/{session_id}")
async def websocket_game(ws: WebSocket, session_id: str):
    await ws.accept()

    session = sessions.get(session_id)
    if not session:
        await ws.send_json({"type": "error", "message": "Session not found"})
        await ws.close()
        return

    try:
        while True:
            data = await ws.receive_json()
            session.last_active = time.time()
            msg_type = data.get("type")

            if msg_type == "manual_action":
                await handle_manual_action(ws, session, data)

            elif msg_type == "start_auto":
                await handle_start_auto(ws, session, data)

            elif msg_type == "stop_auto":
                await handle_stop_auto(ws, session)

            elif msg_type == "reset":
                await handle_reset(ws, session)

            else:
                await ws.send_json({"type": "error", "message": f"Unknown message type: {msg_type}"})

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
        if session.auto_task and not session.auto_task.done():
            session.auto_task.cancel()


# ---------------------------------------------------------------------------
# Manual action handler
# ---------------------------------------------------------------------------

async def handle_manual_action(ws: WebSocket, session: GameSession, data: dict):
    """Execute a single manual action."""
    if session.auto_running:
        await ws.send_json({"type": "error", "message": "Auto mode is running. Stop it first."})
        return

    tool = data.get("tool", "")
    args = data.get("args", {})

    # Check game over conditions before acting
    if not session.operative.is_alive:
        await ws.send_json({"type": "error", "message": "Game over — operative has fallen."})
        return
    if session.operative.has_won:
        await ws.send_json({"type": "error", "message": "Game over — mission already complete."})
        return
    if session.turn >= session.max_turns:
        await ws.send_json({"type": "error", "message": "Game over — out of turns."})
        return

    # Auto-scan
    scan_result = session.tools.execute("scan", {}).message

    # Execute the tool
    result = session.tools.execute(tool, args)
    session.turn += 1

    # Build state dict
    state_dict = game_state_to_dict(
        session.operative, session.world, session.turn, session.max_turns
    )
    if args:
        params = ", ".join(f'{k}="{v}"' for k, v in args.items())
        action_str = f"{tool}({params})"
    else:
        action_str = f"{tool}()"

    # Send turn update
    event = turn_event_to_dict(session.turn, action_str, result.message, scan_result, state_dict)
    await ws.send_json(event)

    # Append to history
    session.history.append({"role": "observation", "content": scan_result})
    session.history.append({"role": "action", "content": action_str})
    session.history.append({"role": "result", "content": result.message})

    # Check end conditions
    await check_game_over(ws, session)


# ---------------------------------------------------------------------------
# Auto mode handlers
# ---------------------------------------------------------------------------

async def handle_start_auto(ws: WebSocket, session: GameSession, data: dict):
    """Compile user's think function and start the auto agent loop."""
    if session.auto_running:
        await ws.send_json({"type": "error", "message": "Auto mode is already running."})
        return

    think_code = data.get("think_code", "")
    system_prompt = data.get("system_prompt", "")

    # Check if code references client but no API key
    if not gemini_client and "client" in think_code:
        await ws.send_json({
            "type": "error",
            "message": "No Gemini API key configured. Set GEMINI_API_KEY to use LLM calls in auto mode.",
        })
        return

    # Compile think function
    try:
        code = "def think_llm(operative, world, history, client):\n"
        code += "    SYSTEM_PROMPT = system_prompt\n"
        code += textwrap.indent(think_code, "    ")
        namespace = {
            "MISSION_BRIEFING": MICRO_MISSION_BRIEFING,
            "TOOLS_DESCRIPTION": TOOLS_DESCRIPTION,
            "system_prompt": system_prompt,
        }
        if gemini_client:
            from google import genai
            namespace["genai"] = genai
        exec(code, namespace)
        think_fn = namespace["think_llm"]
    except Exception as e:
        await ws.send_json({"type": "error", "message": f"Code compilation error: {e}"})
        return

    session.auto_running = True
    session.auto_task = asyncio.create_task(
        run_auto_loop(ws, session, think_fn)
    )
    await ws.send_json({"type": "auto_started"})


async def run_auto_loop(ws: WebSocket, session: GameSession, think_fn):
    """Run the agent loop asynchronously, sending turn updates over WebSocket."""
    try:
        while session.auto_running:
            # Check end conditions
            if not session.operative.is_alive or session.operative.has_won or session.turn >= session.max_turns:
                break

            # 1. Scan
            scan_result = session.tools.execute("scan", {}).message

            # 2. Build history entry
            observation = scan_result
            if session.turn == 0:
                observation = MICRO_MISSION_BRIEFING + "\n" + observation
            session.history.append({"role": "observation", "content": observation})

            # 3. Call think function
            try:
                action_text = think_fn(
                    session.operative, session.world, session.history, gemini_client
                )
            except Exception as e:
                await ws.send_json({"type": "error", "message": f"think_llm error: {e}"})
                action_text = "TOOL: scan()"
                session.history.append({"role": "error", "content": f"Think error: {e}"})

            # 4. Parse and execute
            try:
                tool_name, args = parse_tool_call(action_text)
            except ValueError:
                tool_name, args = "scan", {}

            result = session.tools.execute(tool_name, args)
            session.turn += 1

            # Update history
            action_str = f"{tool_name}({args})" if args else f"{tool_name}()"
            session.history.append({"role": "action", "content": action_str})
            session.history.append({"role": "result", "content": result.message})

            # 5. Send turn update
            state_dict = game_state_to_dict(
                session.operative, session.world, session.turn, session.max_turns
            )
            event = turn_event_to_dict(session.turn, action_str, result.message, scan_result, state_dict)
            await ws.send_json(event)

            # 6. Animation delay
            await asyncio.sleep(0.8)

        # 7. Check end conditions and send game_over
        await check_game_over(ws, session)

    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Auto loop error: {e}")
        try:
            await ws.send_json({"type": "error", "message": f"Auto mode error: {e}"})
        except Exception:
            pass
    finally:
        session.auto_running = False


async def handle_stop_auto(ws: WebSocket, session: GameSession):
    """Stop the auto agent loop."""
    if session.auto_task and not session.auto_task.done():
        session.auto_task.cancel()
    session.auto_running = False
    await ws.send_json({"type": "auto_stopped", "reason": "user"})


# ---------------------------------------------------------------------------
# Reset handler
# ---------------------------------------------------------------------------

async def handle_reset(ws: WebSocket, session: GameSession):
    """Reset the session to a fresh micro game."""
    if session.auto_task and not session.auto_task.done():
        session.auto_task.cancel()
    session.auto_running = False

    operative, world, tools = create_micro_game()
    if gemini_client:
        tools.set_oracle(lambda npc, q, o: llm_oracle(npc, q, o, gemini_client))
    else:
        tools.set_oracle(micro_stub_oracle)

    session.operative = operative
    session.world = world
    session.tools = tools
    session.turn = 0
    session.history = []

    state_dict = game_state_to_dict(operative, world, 0, session.max_turns)
    event = turn_event_to_dict(0, "", MICRO_MISSION_BRIEFING, "", state_dict)
    await ws.send_json(event)


# ---------------------------------------------------------------------------
# Game over check
# ---------------------------------------------------------------------------

async def check_game_over(ws: WebSocket, session: GameSession):
    """Send game_over message if the game has ended."""
    op = session.operative
    reason = None
    won = False

    if not op.is_alive:
        reason = "The operative has fallen."
        won = False
    elif op.has_won:
        reason = "Mission complete! All dossiers collected."
        won = True
    elif session.turn >= session.max_turns:
        reason = "Out of turns. Mission failed."
        won = False
    else:
        return  # game still going

    await ws.send_json({
        "type": "game_over",
        "won": won,
        "reason": reason,
        "stats": {
            "turns": session.turn,
            "dossiers": op.dossiers,
            "health": op.health,
            "visited": len(op.visited),
        },
    })


# ---------------------------------------------------------------------------
# Static files — mount AFTER API routes
# ---------------------------------------------------------------------------

static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
