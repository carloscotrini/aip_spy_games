"""Tests for the game state serialization layer."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "agentic_ai_spy"))

from hidden_layer.operative import Operative
from hidden_layer.game_world import GameWorld, CellType, Cell, NPC
from hidden_layer.serialization import cell_to_dict, game_state_to_dict, turn_event_to_dict


class MicroGameWorld(GameWorld):
    """Minimal 3x3 game world for testing (mirrors micro mission)."""

    ROWS = 3
    COLS = 3

    def __init__(self):
        self.grid = [[Cell(cell_type=CellType.OPEN) for _ in range(self.COLS)] for _ in range(self.ROWS)]
        # Set up a few interesting cells
        self.grid[0][0] = Cell(cell_type=CellType.JUNGLE, items=["Flamethrower"], description="Dense jungle.")
        self.grid[0][2] = Cell(cell_type=CellType.CACHE, items=["dossier_1"], description="Filing cabinet.")
        self.grid[1][1] = Cell(cell_type=CellType.INFORMANT, npc_id="dropout", description="Camouflaged hideout.")
        self.grid[2][0] = Cell(cell_type=CellType.OPEN, description="South shore. Start.")
        self.grid[2][1] = Cell(cell_type=CellType.INFORMANT, npc_id="dr_vapnik", description="Weathered shack.")
        self.grid[2][2] = Cell(cell_type=CellType.ROBOT, robot_name="Cryo-Sentinel", description="Freezing corridor.")
        # Quest flags
        self.usb_drive_picked_up = False
        self.usb_drive_delivered = False
        self.microfilm_picked_up = False
        self.microfilm_delivered = False
        self.codebook_picked_up = False
        self.codebook_delivered = False
        self.hard_drive_traded = False
        self.medical_supplies_delivered = False
        self.virus_code_received = False
        self.cryo_sentinel_alive = True
        self.evil_ai_robot_alive = False


def make_fresh_micro_game():
    """Create a fresh micro game state for testing."""
    operative = Operative(position=(2, 0), visited={(2, 0)})
    operative.WIN_DOSSIERS = 3
    world = MicroGameWorld()
    return operative, world


class TestCellToDict:
    """Tests for cell_to_dict."""

    def test_visible_cell_at_start_position(self):
        """Start cell (2,0) should be visible since it's in visited."""
        op, world = make_fresh_micro_game()
        cell = world.get_cell(2, 0)
        result = cell_to_dict(cell, (2, 0), op, world)

        assert result["visible"] is True
        assert result["type"] == CellType.OPEN.value
        assert result["emoji"] == CellType.OPEN.emoji
        assert result["label"] == CellType.OPEN.label
        assert result["description"] == "South shore. Start."
        assert result["has_items"] is False
        assert result["npc_name"] is None
        assert result["robot_name"] is None

    def test_adjacent_cell_is_visible(self):
        """Cell (2,1) is adjacent to visited (2,0), so it should be visible."""
        op, world = make_fresh_micro_game()
        cell = world.get_cell(2, 1)
        result = cell_to_dict(cell, (2, 1), op, world)

        assert result["visible"] is True
        assert result["type"] == CellType.INFORMANT.value
        assert result["npc_name"] is not None  # Dr. Vapnik

    def test_fog_of_war_far_cell(self):
        """Cell (0,2) should be fog-of-war from start position (2,0)."""
        op, world = make_fresh_micro_game()
        cell = world.get_cell(0, 2)
        result = cell_to_dict(cell, (0, 2), op, world)

        assert result["visible"] is False
        assert result["type"] == "unknown"
        assert result["emoji"] == "░"
        assert result["label"] == ""
        assert result["description"] == ""
        assert result["has_items"] is False
        assert result["npc_name"] is None
        assert result["robot_name"] is None

    def test_cell_with_items(self):
        """Visible cell with items should report has_items=True."""
        op, world = make_fresh_micro_game()
        # Visit (1,0) so (0,0) becomes adjacent-visible
        op.visited.add((1, 0))
        cell = world.get_cell(0, 0)
        result = cell_to_dict(cell, (0, 0), op, world)

        assert result["visible"] is True
        assert result["has_items"] is True
        assert result["type"] == CellType.JUNGLE.value

    def test_cell_with_robot(self):
        """Visible robot cell should report robot_name."""
        op, world = make_fresh_micro_game()
        # Visit (2,2) neighbor
        op.visited.add((1, 2))
        cell = world.get_cell(2, 2)
        result = cell_to_dict(cell, (2, 2), op, world)

        assert result["visible"] is True
        assert result["robot_name"] == "Cryo-Sentinel"


class TestGameStateToDict:
    """Tests for game_state_to_dict."""

    def test_fresh_micro_game_state(self):
        """Fresh micro game should have correct initial state."""
        op, world = make_fresh_micro_game()
        state = game_state_to_dict(op, world, 0, 30)

        assert state["turn"] == 0
        assert state["max_turns"] == 30
        assert state["position"] == [2, 0]
        assert state["health"] == 3
        assert state["max_health"] == Operative.MAX_HEALTH
        assert state["dossiers"] == 0
        assert state["win_dossiers"] == 3
        assert state["inventory"] == []
        assert state["is_alive"] is True
        assert state["has_won"] is False
        assert state["cryo_alive"] is True
        assert state["evil_ai_alive"] is False
        assert state["rows"] == 3
        assert state["cols"] == 3

    def test_grid_dimensions(self):
        """Grid should match world.ROWS x world.COLS."""
        op, world = make_fresh_micro_game()
        state = game_state_to_dict(op, world, 0, 30)

        assert len(state["grid"]) == world.ROWS
        for row in state["grid"]:
            assert len(row) == world.COLS

    def test_journal_truncated_to_last_5(self):
        """Journal should be truncated to the last 5 entries."""
        op, world = make_fresh_micro_game()
        op.journal = [f"entry_{i}" for i in range(10)]
        state = game_state_to_dict(op, world, 5, 30)

        assert len(state["journal"]) == 5
        assert state["journal"] == ["entry_5", "entry_6", "entry_7", "entry_8", "entry_9"]

    def test_journal_short_not_padded(self):
        """Journal with fewer than 5 entries should not be padded."""
        op, world = make_fresh_micro_game()
        op.journal = ["a", "b"]
        state = game_state_to_dict(op, world, 0, 30)

        assert state["journal"] == ["a", "b"]

    def test_visited_serialized_as_lists(self):
        """Visited set should be serialized as list of [r,c] pairs."""
        op, world = make_fresh_micro_game()
        state = game_state_to_dict(op, world, 0, 30)

        assert len(state["visited"]) == 1
        assert state["visited"][0] == [2, 0]

    def test_inventory_serialized(self):
        """Inventory should be a list."""
        op, world = make_fresh_micro_game()
        op.inventory = ["USB Drive", "Flamethrower"]
        state = game_state_to_dict(op, world, 1, 30)

        assert state["inventory"] == ["USB Drive", "Flamethrower"]

    def test_fog_of_war_in_grid(self):
        """Cell (0,2) should be fog in fresh micro game."""
        op, world = make_fresh_micro_game()
        state = game_state_to_dict(op, world, 0, 30)

        cell_0_2 = state["grid"][0][2]
        assert cell_0_2["visible"] is False
        assert cell_0_2["type"] == "unknown"

    def test_adjacent_visible_in_grid(self):
        """Cell (2,1) should be visible (adjacent to start)."""
        op, world = make_fresh_micro_game()
        state = game_state_to_dict(op, world, 0, 30)

        cell_2_1 = state["grid"][2][1]
        assert cell_2_1["visible"] is True


class TestTurnEventToDict:
    """Tests for turn_event_to_dict."""

    def test_turn_event_structure(self):
        """Turn event should have all expected fields."""
        state_dict = {"turn": 1, "position": [1, 0]}
        result = turn_event_to_dict(1, "move(direction=\"north\")", "Moved north.", "Scan result.", state_dict)

        assert result["type"] == "turn_update"
        assert result["turn"] == 1
        assert result["action"] == "move(direction=\"north\")"
        assert result["result"] == "Moved north."
        assert result["scan"] == "Scan result."
        assert result["state"] is state_dict
