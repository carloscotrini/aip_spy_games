"""Agent loop and think function for The Hidden Layer.

Students implement think_llm() — an LLM-powered decision function.

Everything else is provided.
"""

import json
import re
from datetime import datetime
from typing import Callable, Optional

from hidden_layer.operative import Operative
from hidden_layer.game_world import GameWorld
from hidden_layer.tools import GameTools, ToolResult


# ---------------------------------------------------------------------------
# Mission briefing (background knowledge for the LLM)
# ---------------------------------------------------------------------------

MISSION_BRIEFING = """CLASSIFIED — MISSION BRIEFING — AGENT LAMBDA

OBJECTIVE: Infiltrate the OVERFIT Corporation base on Isla Perdida and extract
10 classified dossiers. The mission is complete once you have all 10.

THE BASE (8x8 grid):
- Dossier caches (📁): Contain 1 dossier each. Use collect() to grab them.
- Jungle (🌴): May contain useful items (collect them!) or traps (lose 1 health).
- Concrete walls (🧱): Impassable. Navigate around them.
- Informants (🕵️): Talk to them using talk(). They offer jobs, trades, and intel.
  Ask about "jobs", "deliveries", or "tasks" to trigger quest item handoffs.
  If you have an item to deliver, mention it by name (e.g. "I have a USB drive").
  If you want to trade, mention "trade" and the item you have.
- Weapons Forge (⚒️): Talk to the engineer to learn what's available.
  Use fabricate(item="name") to craft. Crafting costs materials + dossiers.
- Research Lab (🔬): Same as forge — talk first, then fabricate.
  The lab also buys certain salvaged items for dossiers.
- Safe Houses (🏠): Talk to the operator — they may give you delivery errands
  worth dossiers.
- Robots (🤖): Powerful enemies guarding high-value dossiers. Moving into a
  robot cell with the correct weapon destroys it instantly (+3 dossiers).
  Moving in WITHOUT the correct weapon deals 1 damage and bounces you back.
  Talk to informants to learn each robot's weakness before approaching.

HOW TO EARN DOSSIERS:
1. Collect dossier caches scattered across the map (1 each)
2. Complete delivery errands for informants and safe house operators (2 each)
3. Destroy robots by entering their cell with the correct weapon (3 each)
4. Sell salvaged robot parts at the Research Lab (1 each)

KEY TACTICS:
- Talk to EVERY informant you meet — they reveal quests, item locations, and
  robot weaknesses. One conversation can unlock an entire quest chain.
- When an informant mentions an item or location, GO THERE next.
- If someone asks you to bring something, leave and go find it — don't keep
  asking the same person.
- Items on the ground won't announce themselves. If you enter a jungle or cache
  cell and see a description mentioning objects, use collect().
- Once you've collected from a cell, it's empty. Don't return to it.
- The map is 8x8 (rows 0-7, columns 0-7). Explore widely — don't stay in one area.
"""


# ---------------------------------------------------------------------------
# Tool descriptions
# ---------------------------------------------------------------------------

TOOLS_DESCRIPTION = """Available tools (use exactly one per turn):

TOOL: move(direction="north|south|east|west")
  Move one step in a cardinal direction. Triggers cell events on arrival.
  Concrete walls are impassable. Moving into jungle may trigger a trap.
  WARNING: Moving into a robot cell without the correct weapon deals 1 damage
  and bounces you back. Make sure you have the right weapon first.

TOOL: talk(message="your message here")
  Talk to an informant, safe house operator, or facility engineer in your current cell.
  Informants give hints and quest items. Ask about "jobs" or "deliveries" to get quests.
  If you have an item to deliver, mention it by name.
  Facility engineers tell you what they can build.

TOOL: collect()
  Pick up items in your current cell (dossier caches, quest materials).

TOOL: fabricate(item="item name")
  Craft a weapon at the current facility. Requires the right materials + dossiers.
  Talk to the facility engineer first to learn what can be built."""


# ---------------------------------------------------------------------------
# Tool call parser (provided complete)
# ---------------------------------------------------------------------------

def parse_tool_call(text: str) -> tuple[str, dict]:
    """Parse an LLM response to extract a tool call.

    Expected format: TOOL: tool_name(arg1="val1", arg2="val2")
    Falls back to scan() if parsing fails.

    Args:
        text: The raw text from the think function.

    Returns:
        Tuple of (tool_name, args_dict).
    """
    # Try to find TOOL: pattern
    match = re.search(r'TOOL:\s*(\w+)\((.*?)\)', text, re.DOTALL)
    if not match:
        # Fallback: look for just a tool name
        simple = re.search(r'TOOL:\s*(\w+)', text)
        if simple:
            return simple.group(1), {}
        raise ValueError(f"No TOOL: call found in LLM response. Got: {text[:300]!r}")

    tool_name = match.group(1)
    args_str = match.group(2).strip()

    if not args_str:
        return tool_name, {}

    # Parse keyword arguments: key="value" or key='value'
    args = {}
    for kv_match in re.finditer(r'(\w+)\s*=\s*["\']([^"\']*)["\']', args_str):
        args[kv_match.group(1)] = kv_match.group(2)

    return tool_name, args


# ---------------------------------------------------------------------------
# Agent loop (provided complete)
# ---------------------------------------------------------------------------

def run_agent(
    think_fn: Callable,
    operative: Operative,
    world: GameWorld,
    tools: GameTools,
    max_turns: int = 100,
    display_fn: Optional[Callable] = None,
) -> dict:
    """Run the agent loop: perceive -> think -> act.

    Args:
        think_fn: Function(operative, world, history) -> str that returns a TOOL: call.
        operative: The operative instance.
        world: The game world.
        tools: The game tools.
        max_turns: Maximum turns before the game ends.
        display_fn: Optional function(world, operative, turn, action, result) for visualization.

    Returns:
        dict with keys: won, turns, dossiers, health, log_file.
    """
    history: list[dict[str, str]] = []
    game_log: list[dict] = []

    for turn in range(max_turns):
        # Check end conditions
        if not operative.is_alive:
            game_log.append({
                "turn": turn, "event": "GAME OVER", "reason": "The operative has fallen.",
                "position": list(operative.position), "health": operative.health,
                "dossiers": operative.dossiers, "inventory": list(operative.inventory),
            })
            if display_fn:
                display_fn(world, operative, turn, "---", "GAME OVER: The operative has fallen.", "")
            break
        if operative.has_won:
            game_log.append({
                "turn": turn, "event": "MISSION COMPLETE", "reason": "Collected enough dossiers!",
                "position": list(operative.position), "health": operative.health,
                "dossiers": operative.dossiers, "inventory": list(operative.inventory),
            })
            if display_fn:
                display_fn(world, operative, turn, "---", "MISSION COMPLETE: Enough dossiers collected!", "")
            break

        # PERCEIVE: auto-scan each turn (not agent-callable, shown in display panel)
        scan_result = tools.execute("scan", {}).message

        # On the first turn, prepend the mission briefing.
        observation = scan_result
        if turn == 0:
            observation = MISSION_BRIEFING + "\n" + observation

        # Build context for the think function
        history.append({"role": "observation", "content": observation})

        # THINK: agent decides an action
        think_error = None
        try:
            action_text = think_fn(operative, world, history)
        except Exception as e:
            action_text = "TOOL: scan()"
            think_error = str(e)
            history.append({"role": "error", "content": f"Think function error: {e}"})
            # Print error so students notice immediately
            if turn < 3:
                print(f"\n⚠️  think_fn crashed: {e}")
                print("    Fix your think_llm() function. The agent is stuck!\n")

        # Parse the action
        try:
            tool_name, args = parse_tool_call(action_text)
        except ValueError as e:
            tool_name, args = "scan", {}
            history.append({"role": "error", "content": f"Parse error: {e}"})
            if turn < 3:
                print(f"\n⚠️  Could not parse tool call: {e}\n")

        # ACT: execute the chosen tool
        result = tools.execute(tool_name, args)

        # Update history
        history.append({"role": "action", "content": f"{tool_name}({args})"})
        history.append({"role": "result", "content": result.message})

        # Log this turn
        log_entry = {
            "turn": turn,
            "position": list(operative.position),
            "health": operative.health,
            "dossiers": operative.dossiers,
            "inventory": list(operative.inventory),
            "observation": observation,
            "action": f"{tool_name}({args})",
            "result": result.message,
            "success": result.success,
        }
        if think_error:
            log_entry["think_error"] = think_error
        game_log.append(log_entry)

        # Display
        if display_fn:
            display_fn(world, operative, turn, f"{tool_name}({args})", result.message, scan_result)

    # Save game log
    log_file = _save_game_log(game_log, operative)

    return {
        "won": operative.has_won,
        "turns": turn + 1 if 'turn' in dir() else 0,
        "dossiers": operative.dossiers,
        "health": operative.health,
        "log_file": log_file,
    }


def _save_game_log(game_log: list[dict], operative: Operative) -> str:
    """Save the game log to a JSON file and return the file path."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    outcome = "mission_complete" if operative.has_won else "mission_failed"
    log_file = f"game_log_{outcome}_{timestamp}.json"

    log_data = {
        "outcome": outcome,
        "final_dossiers": operative.dossiers,
        "final_health": operative.health,
        "final_inventory": list(operative.inventory),
        "total_turns": len([e for e in game_log if "action" in e]),
        "journal": list(operative.journal),
        "turns": game_log,
    }

    with open(log_file, "w") as f:
        json.dump(log_data, f, indent=2)

    return log_file


# ---------------------------------------------------------------------------
# LLM-powered think function (students implement this)
# ---------------------------------------------------------------------------

def think_llm(operative: Operative, world: GameWorld, history: list[dict], client) -> str:
    """Decide the next action using an LLM.

    TODO: Implement this function.

    Steps:
    1. Build a system message that includes:
       - The agent's role (you are a spy operative, goal is 10 dossiers)
       - The TOOLS_DESCRIPTION (so the LLM knows what tools are available)
       - Instructions to respond with exactly one TOOL: call

    2. Build a user message that includes:
       - Current operative status (use operative.status_text())
       - Recent history (last ~10 entries from the history list)
       - Current cell description
       - The operative's journal entries (key past informant conversations)

    3. Call client.models.generate_content() with:
       - model="gemini-2.5-flash"
       - contents=<your user message>
       - config=genai.types.GenerateContentConfig(
             system_instruction=<your system message>,
             max_output_tokens=500,
         )

    4. Return response.text

    Args:
        operative: Current operative state.
        world: The game world.
        history: Conversation history from the game loop.
        client: A genai.Client() instance.

    Returns:
        str: The LLM's response containing a TOOL: call.
    """
    # ========================
    # YOUR CODE HERE
    # ========================
    raise NotImplementedError("TODO: Implement think_llm")
