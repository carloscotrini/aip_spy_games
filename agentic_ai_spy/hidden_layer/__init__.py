"""The Hidden Layer: An Agentic AI Infiltration Exercise."""

from hidden_layer.game_world import (
    CellType,
    Item,
    NPC,
    Cell,
    GameWorld,
    NPC_CATALOG,
    FACILITY_CATALOG,
    ITEM_CATALOG,
)
from hidden_layer.operative import Operative
from hidden_layer.tools import ToolResult, GameTools
from hidden_layer.oracle import stub_oracle, llm_oracle, ORACLE_TEMPLATE, gemini_call_with_retry
from hidden_layer.agent import (
    MISSION_BRIEFING,
    TOOLS_DESCRIPTION,
    parse_tool_call,
    run_agent,
)
from hidden_layer.display import render_grid, display_turn, display_final
from hidden_layer.main import create_game, play_with_llm

try:
    from hidden_layer.interactive import play_interactive
except ImportError:
    pass  # ipywidgets / IPython not available outside notebooks
