"""Micro mission: 3x3 grid, 3 dossiers, 2 NPCs — extracted from the notebook."""

from hidden_layer.game_world import CellType, Cell, NPC, GameWorld
from hidden_layer.operative import Operative
from hidden_layer.tools import GameTools, ToolResult
from hidden_layer.oracle import stub_oracle, llm_oracle
from hidden_layer.agent import TOOLS_DESCRIPTION, parse_tool_call, run_agent
from hidden_layer.display import display_turn, display_final


# ---------------------------------------------------------------------------
# Micro NPCs
# ---------------------------------------------------------------------------

MICRO_NPC_CATALOG = {
    "dr_vapnik": NPC(
        name="Dr. Vapnik",
        personality="Helpful old scientist. Gets to the point quickly.",
        knowledge=[
            "He has a USB Drive that must reach Agent Dropout at position (1, 1) in the center of the base.",
            "Delivering the USB Drive pays 1 dossier.",
        ],
        style="Speaks in brief statistical metaphors but always delivers clear information.",
        greeting="Ah, agent. I have a job for you. Ask me about it.",
    ),
    "dropout": NPC(
        name="Agent Dropout",
        personality="Bitter but helpful burned spy. Very direct.",
        knowledge=[
            "She receives USB Drives. Will pay 1 dossier for one.",
            "The Cryo-Sentinel robot at position (2, 2) freezes intruders.",
            "A Flamethrower can destroy the Cryo-Sentinel. Worth 1 dossier.",
            "There is a Flamethrower hidden in the jungle at the northwest corner, position (0, 0).",
        ],
        style="Direct and blunt. No riddles, no metaphors. Tells you exactly what you need.",
        greeting="You again? Fine. What do you need?",
    ),
}


# ---------------------------------------------------------------------------
# Micro stub oracle
# ---------------------------------------------------------------------------

def micro_stub_oracle(npc, message, operative):
    """Simple keyword-matched responses for micro mission."""
    q = message.lower()
    name = npc.name

    if name == "Dr. Vapnik":
        if any(kw in q for kw in ["usb", "drive", "deliver", "job", "work", "task",
                                    "errand", "help", "mission", "what", "how", "tell"]):
            return ("I have a USB Drive with critical data. Deliver it to Agent Dropout "
                    "at position (1, 1) \u2014 the center of the base. 1 dossier for the job.")
        return "I have a job for you, agent. Ask me about a delivery or a job."

    if name == "Agent Dropout":
        if any(kw in q for kw in ["usb", "drive", "deliver"]) and operative.has_item("USB Drive"):
            return "The USB drive! Good. Here's your dossier."
        if any(kw in q for kw in ["robot", "cryo", "sentinel", "fire", "flame", "weapon",
                                    "help", "mission", "what", "how", "tell", "job", "task"]):
            return ("There's a Cryo-Sentinel robot at position (2, 2). It freezes everything. "
                    "Move into it with a Flamethrower to destroy it \u2014 worth 1 dossier. "
                    "There's a Flamethrower in the jungle at the northwest corner, position (0, 0).")
        return "Ask me about the robot or if you have something to deliver."

    return f"{name} says nothing useful."


# ---------------------------------------------------------------------------
# Micro Game World
# ---------------------------------------------------------------------------

class MicroGameWorld(GameWorld):
    """3x3 micro mission grid -- no walls, open terrain."""

    ROWS = 3
    COLS = 3

    def __init__(self):
        self.grid = []
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
        self.build_map()

    def build_map(self):
        self.grid = [
            [Cell(CellType.OPEN) for _ in range(self.COLS)]
            for _ in range(self.ROWS)
        ]

        # Row 0: jungle(flamethrower) · cache(dossier)
        self._set(0, 0, Cell(CellType.JUNGLE, items=["Flamethrower"],
            description="Dense jungle at the northwest corner. A Flamethrower is stashed under the roots!"))
        self._set(0, 2, Cell(CellType.CACHE, items=["dossier_1"],
            description="A filing cabinet left unlocked. Classified documents inside!"))

        # Row 1: · informant(dropout) ·
        self._set(1, 1, Cell(CellType.INFORMANT, npc_id="dropout",
            description="A camouflaged hideout. A woman sharpens a knife."))

        # Row 2: spawn informant(vapnik) robot(cryo)
        self._set(2, 0, Cell(CellType.OPEN,
            description="The south shore. This is where you came ashore."))
        self._set(2, 1, Cell(CellType.INFORMANT, npc_id="dr_vapnik",
            description="A weathered shack. An old man scribbles equations in the dirt."))
        self._set(2, 2, Cell(CellType.ROBOT, robot_name="Cryo-Sentinel",
            description="A freezing corridor. A hulking robot blocks the path, frost pouring from its vents."))

    def _set(self, row, col, cell):
        self.grid[row][col] = cell


# ---------------------------------------------------------------------------
# Micro tools (patched for micro NPCs, plain text only)
# ---------------------------------------------------------------------------

class MicroGameTools(GameTools):
    """Game tools patched for micro mission NPCs. Returns plain text (no HTML)."""

    def talk(self, message=""):
        row, col = self.operative.position
        cell = self.world.get_cell(row, col)

        if cell.cell_type == CellType.INFORMANT and cell.npc_id:
            npc = MICRO_NPC_CATALOG.get(cell.npc_id)
            if not npc:
                return ToolResult(False, "Unknown informant.")
            if self._oracle_fn is None:
                return ToolResult(False, "No oracle function set.")

            response = self._oracle_fn(npc, message, self.operative)

            # Dr. Vapnik gives USB Drive
            if cell.npc_id == "dr_vapnik" and not self.world.usb_drive_picked_up:
                if any(kw in message.lower() for kw in ["usb", "drive", "job", "work", "task", "delivery", "errand"]):
                    self.operative.add_item("USB Drive")
                    self.world.usb_drive_picked_up = True
                    response += "\n[Dr. Vapnik hands you a USB Drive.]"

            # Dropout receives USB Drive
            if cell.npc_id == "dropout" and self.operative.has_item("USB Drive") and not self.world.usb_drive_delivered:
                if any(kw in message.lower() for kw in ["usb", "drive", "deliver", "data"]):
                    self.operative.remove_item("USB Drive")
                    self.operative.add_dossiers(1)
                    self.world.usb_drive_delivered = True
                    response += "\n[You delivered the USB Drive! +1 dossier.]"

            self.operative.journal.append(
                f"Talked to {npc.name}: '{message}' \u2192 '{response[:300]}'"
            )

            return ToolResult(True, f"{npc.name} says: {response}")

        return ToolResult(False, "There is no one to talk to here.")


# ---------------------------------------------------------------------------
# Micro mission briefing
# ---------------------------------------------------------------------------

MICRO_MISSION_BRIEFING = """CLASSIFIED \u2014 MICRO MISSION BRIEFING \u2014 AGENT LAMBDA

OBJECTIVE: Extract 3 classified dossiers from a tiny OVERFIT outpost (3x3 grid).

THE BASE:
- Dossier caches (\U0001f4c1): Use collect() to grab them. Worth 1 dossier each.
- Jungle (\U0001f334): May contain useful items. Use collect() to search.
- Informants (\U0001f575\ufe0f): Talk using talk(). Ask about "jobs" or "deliveries" to get
  quest items. If you have an item to deliver, mention it by name.
- Robot (\U0001f916): Move into it with the correct weapon to destroy it (+1 dossier).
  Moving in WITHOUT the weapon deals 1 damage and bounces you back.

HOW TO EARN DOSSIERS:
1. Collect the dossier cache (1 dossier)
2. Complete the delivery errand (1 dossier) \u2014 ask informants about "jobs"
3. Destroy the robot by moving into it with the right weapon (1 dossier)

KEY TACTICS:
- Talk to EVERY informant. They tell you exactly what to do.
- When told to deliver something, go to the destination and mention the item.
- When told about a weapon location, go get it, then move into the robot cell.
- Don't revisit cells you've already collected from.
"""


# ---------------------------------------------------------------------------
# Game creation and runner
# ---------------------------------------------------------------------------

def create_micro_game():
    """Create a fresh micro mission. Returns (operative, world, tools)."""
    world = MicroGameWorld()
    operative = Operative(position=(2, 0), visited={(2, 0)})
    operative.WIN_DOSSIERS = 3
    tools = MicroGameTools(operative, world)
    return operative, world, tools


def play_micro_mission(think_fn, oracle_fn=None, max_turns=30, show_display=True, delay=0.3):
    """Run the micro mission with the given think function."""
    operative, world, tools = create_micro_game()
    tools.set_oracle(oracle_fn or micro_stub_oracle)

    disp = None
    if show_display:
        disp = lambda w, o, t, a, r, s="": display_turn(w, o, t, a, r, scan_result=s, delay=delay)

    import hidden_layer.agent as _agent_mod
    _orig_briefing = _agent_mod.MISSION_BRIEFING
    _agent_mod.MISSION_BRIEFING = MICRO_MISSION_BRIEFING
    try:
        result = run_agent(think_fn, operative, world, tools, max_turns, display_fn=disp)
    finally:
        _agent_mod.MISSION_BRIEFING = _orig_briefing

    if show_display:
        display_final(operative, result["turns"])

    return result
