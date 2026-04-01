"""Game state serialization for the web frontend."""

from hidden_layer.game_world import GameWorld, Cell
from hidden_layer.operative import Operative


def cell_to_dict(cell: Cell, position: tuple[int, int], operative: Operative, world: GameWorld) -> dict:
    """Serialize a cell, applying fog-of-war based on operative visibility."""
    row, col = position

    # A cell is visible if visited or adjacent (N/S/E/W) to any visited cell
    visible = False
    if position in operative.visited:
        visible = True
    else:
        for vr, vc in operative.visited:
            if abs(vr - row) + abs(vc - col) == 1 and 0 <= row < world.ROWS and 0 <= col < world.COLS:
                visible = True
                break

    if visible:
        return {
            "type": cell.cell_type.value,
            "emoji": cell.cell_type.emoji,
            "label": cell.cell_type.label,
            "description": cell.description,
            "has_items": bool(cell.items),
            "npc_name": cell.npc.name if cell.npc else None,
            "robot_name": cell.robot_name,
            "visible": True,
        }
    else:
        return {
            "type": "unknown",
            "emoji": "░",
            "label": "",
            "description": "",
            "has_items": False,
            "npc_name": None,
            "robot_name": None,
            "visible": False,
        }


def game_state_to_dict(operative: Operative, world: GameWorld, turn: int, max_turns: int) -> dict:
    """Serialize full game state for the frontend."""
    grid = []
    for r in range(world.ROWS):
        row = []
        for c in range(world.COLS):
            cell = world.get_cell(r, c)
            row.append(cell_to_dict(cell, (r, c), operative, world))
        grid.append(row)

    return {
        "turn": turn,
        "max_turns": max_turns,
        "position": list(operative.position),
        "health": operative.health,
        "max_health": operative.MAX_HEALTH,
        "dossiers": operative.dossiers,
        "win_dossiers": operative.WIN_DOSSIERS,
        "inventory": list(operative.inventory),
        "visited": [[r, c] for r, c in operative.visited],
        "journal": operative.journal[-5:],
        "grid": grid,
        "is_alive": operative.is_alive,
        "has_won": operative.has_won,
        "cryo_alive": world.cryo_sentinel_alive,
        "evil_ai_alive": world.evil_ai_robot_alive,
        "rows": world.ROWS,
        "cols": world.COLS,
    }


def turn_event_to_dict(turn: int, action: str, result: str, scan: str, state_dict: dict) -> dict:
    """Serialize a single turn event for WebSocket broadcast."""
    return {
        "type": "turn_update",
        "turn": turn,
        "action": action,
        "result": result,
        "scan": scan,
        "state": state_dict,
    }
