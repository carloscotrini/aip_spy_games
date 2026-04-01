"""Game runner for The Hidden Layer — convenience functions to wire everything together."""

from typing import Callable, Optional

from hidden_layer.game_world import GameWorld
from hidden_layer.operative import Operative
from hidden_layer.tools import GameTools
from hidden_layer.agent import run_agent
from hidden_layer.display import display_turn, display_final


def create_game() -> tuple[Operative, GameWorld, GameTools]:
    """Create a fresh game instance.

    Returns:
        Tuple of (operative, world, tools) ready to play.
    """
    world = GameWorld()
    operative = Operative()
    tools = GameTools(operative, world)
    return operative, world, tools


def play_with_llm(
    think_fn: Callable,
    oracle_fn: Callable,
    max_turns: int = 100,
    show_display: bool = True,
    delay: float = 0.0,
) -> dict:
    """Run a game using an LLM-powered think function.

    Args:
        think_fn: Your LLM think function(operative, world, history) -> str.
        oracle_fn: Your oracle function(npc, question, operative) -> str.
        max_turns: Maximum number of turns.
        show_display: Whether to show the visual display.
        delay: Seconds to pause between turns (for visualization).

    Returns:
        dict with keys: won, turns, dossiers, health.
    """
    operative, world, tools = create_game()
    tools.set_oracle(oracle_fn)

    disp = None
    if show_display:
        disp = lambda w, o, t, a, r: display_turn(w, o, t, a, r, delay=delay)

    result = run_agent(think_fn, operative, world, tools, max_turns, display_fn=disp)

    if show_display:
        display_final(operative, result["turns"])

    return result
