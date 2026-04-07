"""Training mission: 5x5 grid, 5 dossiers, 3 NPCs + Forge + SafeHouse — step up from micro."""

from hidden_layer.game_world import CellType, Cell, NPC, GameWorld
from hidden_layer.operative import Operative
from hidden_layer.tools import GameTools, ToolResult, ROBOT_WEAPONS
from hidden_layer.oracle import stub_oracle, llm_oracle
from hidden_layer.agent import TOOLS_DESCRIPTION, parse_tool_call, run_agent
from hidden_layer.display import display_turn, display_final


# ---------------------------------------------------------------------------
# Training NPCs
# ---------------------------------------------------------------------------

TRAINING_NPC_CATALOG = {
    "dr_vapnik": NPC(
        name="Dr. Vapnik",
        personality="Helpful old scientist. Gets to the point quickly.",
        knowledge=[
            "He has a USB Drive that must reach Informant Backprop at position (2, 2) in the center of the grid.",
            "Delivering the USB Drive pays 1 dossier.",
            "There is a Weapons Forge to the northwest at position (2, 0). The engineer there can build a Flamethrower if you bring a Fuel Canister.",
            "Fuel Canisters can be found in the jungle at the far northwest corner, position (0, 0).",
        ],
        style="Speaks in brief statistical metaphors but always delivers clear information.",
        greeting="Ah, agent. I have a job for you. Ask me about it.",
    ),
    "backprop": NPC(
        name="Informant Backprop",
        personality="Paranoid double agent, fast-talking, always looking over his shoulder.",
        knowledge=[
            "He receives USB Drives. Will pay 1 dossier for one.",
            "A Cryo-Sentinel robot guards the eastern corridor at position (2, 4). It freezes intruders.",
            "Only fire can destroy the Cryo-Sentinel — a Flamethrower.",
            "The Forge to the west at position (2, 0) can build a Flamethrower from a Fuel Canister.",
            "Agent Dropout trades supplies. She might have what the injured agent Bias needs.",
            "There is a Hard Drive hidden in the jungle at the southeast corner, position (4, 4).",
        ],
        style="Paranoid, fast-talking. Uses spy jargon. Calls the operative 'asset'. Always whispers.",
        greeting="Psst — you didn't hear this from me... but the gradient points east.",
    ),
    "dropout": NPC(
        name="Agent Dropout",
        personality="Burned spy who dropped out of the network. Expert in improvised equipment.",
        knowledge=[
            "She has Medical Supplies scavenged from a supply drop. Will trade them for a Hard Drive.",
            "There is an injured agent — codename Bias — at the SafeHouse to the northeast, position (0, 4).",
            "Bias needs Medical Supplies badly. Delivering them is worth 1 dossier.",
            "Fuel Canisters can be found in the jungle at the northwest corner, position (0, 0).",
            "The Weapons Forge at position (2, 0) can build weapons from raw materials.",
        ],
        style="Bitter, sarcastic, but helpful. References being 'dropped' from the program.",
        greeting="They dropped me from the program. Said I was 'reducing overfitting.' What do you need?",
    ),
}


# ---------------------------------------------------------------------------
# Training stub oracle
# ---------------------------------------------------------------------------

def training_stub_oracle(npc, message, operative):
    """Simple keyword-matched responses for training mission."""
    q = message.lower()
    name = npc.name

    if name == "Dr. Vapnik":
        if any(kw in q for kw in ["usb", "drive", "deliver", "job", "work", "task",
                                    "errand", "help", "mission", "what", "how", "tell"]):
            return ("I have a USB Drive with critical data. Deliver it to Informant Backprop "
                    "at position (2, 2) — the center of the grid. 1 dossier for the job. "
                    "Also: there is a Weapons Forge at position (2, 0) that can build a "
                    "Flamethrower if you bring a Fuel Canister. You can find Fuel Canisters "
                    "in the jungle at the far northwest corner, position (0, 0).")
        return "I have a job for you, agent. Ask me about a delivery or a job."

    if name == "Informant Backprop":
        if any(kw in q for kw in ["usb", "drive", "deliver"]) and operative.has_item("USB Drive"):
            return ("The USB drive! Good work, asset. Here's your dossier. "
                    "Listen — a Cryo-Sentinel blocks the eastern corridor at position (2, 4). "
                    "Only fire can destroy it — you need a Flamethrower. The Forge at position "
                    "(2, 0) can build one from a Fuel Canister. Also, Agent Dropout trades "
                    "supplies. She might have what the injured agent Bias needs.")
        if any(kw in q for kw in ["robot", "cryo", "sentinel", "fire", "flame", "weapon",
                                    "help", "mission", "what", "how", "tell", "job", "task"]):
            return ("A Cryo-Sentinel guards the east at position (2, 4). It freezes everything. "
                    "You need a Flamethrower to destroy it — worth 1 dossier. "
                    "The Forge at position (2, 0) can build one from a Fuel Canister. "
                    "There's a Hard Drive hidden in the jungle at position (4, 4). "
                    "And Agent Dropout might trade for it — she has Medical Supplies.")
        return "Ask me about the robot, or if you have something to deliver."

    if name == "Agent Dropout":
        if any(kw in q for kw in ["hard drive", "trade", "medical", "supplies"]) and operative.has_item("Hard Drive"):
            return ("A Hard Drive? I can work with that. Here — take these Medical Supplies. "
                    "There's an injured agent, codename Bias, at the SafeHouse to the northeast, "
                    "position (0, 4). She needs these supplies badly. Worth 1 dossier.")
        if any(kw in q for kw in ["help", "mission", "what", "how", "tell", "job", "task",
                                    "trade", "medical", "supplies"]):
            return ("I have Medical Supplies, but nothing's free. Bring me a Hard Drive and "
                    "we can trade. I heard there's one hidden in the jungle at the southeast "
                    "corner. Also, there's an injured agent — codename Bias — at the SafeHouse "
                    "northeast of here, position (0, 4). She needs medical supplies.")
        return "Bring me something valuable, and maybe we'll trade. Ask about a trade or a job."

    return f"{name} says nothing useful."


# ---------------------------------------------------------------------------
# Training Game World
# ---------------------------------------------------------------------------

class TrainingGameWorld(GameWorld):
    """5x5 training mission grid — walls, forge, safehouse, one robot."""

    ROWS = 5
    COLS = 5

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
        # Training-specific: forge crafting flag
        self.flamethrower_crafted = False
        self.build_map()

    def build_map(self):
        self.grid = [
            [Cell(CellType.OPEN) for _ in range(self.COLS)]
            for _ in range(self.ROWS)
        ]

        # Row 0: Jungle(Fuel) · Cache(dossier) Wall SafeHouse(Bias)
        self._set(0, 0, Cell(CellType.JUNGLE, items=["Fuel Canister"],
            description="Dense jungle at the northwest corner. Something metallic glints under the roots."))
        self._set(0, 2, Cell(CellType.CACHE, items=["dossier_1"],
            description="A filing cabinet left unlocked. Classified documents inside!"))
        self._set(0, 3, Cell(CellType.WALL,
            description="Reinforced concrete wall."))
        self._set(0, 4, Cell(CellType.SAFEHOUSE, safehouse_pos=(0, 4),
            description="The Northern SafeHouse. A woman clutches her side, wincing in pain."))

        # Row 1: · Dropout · Wall ·
        self._set(1, 1, Cell(CellType.INFORMANT, npc_id="dropout",
            description="A camouflaged hideout in the overgrowth. A woman sharpens a knife."))
        self._set(1, 3, Cell(CellType.WALL,
            description="Reinforced concrete wall."))

        # Row 2: Forge · Backprop · Cryo-Sentinel
        self._set(2, 0, Cell(CellType.FORGE, facility_pos=(2, 0),
            description="The Weapons Forge. Sparks fly as an engineer hammers at something on an anvil."))
        self._set(2, 2, Cell(CellType.INFORMANT, npc_id="backprop",
            description="A figure in a trench coat steps out from behind a pillar, eyes darting."))
        self._set(2, 4, Cell(CellType.ROBOT, robot_name="Cryo-Sentinel",
            description="A freezing corridor. A hulking robot blocks the path, frost pouring from its vents."))

        # Row 3: · · · Wall Jungle(trap)
        self._set(3, 3, Cell(CellType.WALL,
            description="Reinforced concrete wall."))
        self._set(3, 4, Cell(CellType.JUNGLE, trap=True,
            description="Thick jungle with tripwires strung between the trees."))

        # Row 4: Start Vapnik · Cache(dossier) Jungle(Hard Drive)
        self._set(4, 0, Cell(CellType.OPEN,
            description="The south shore. This is where you came ashore."))
        self._set(4, 1, Cell(CellType.INFORMANT, npc_id="dr_vapnik",
            description="A weathered shack. An old man scribbles equations in the dirt."))
        self._set(4, 3, Cell(CellType.CACHE, items=["dossier_1"],
            description="A dossier is wedged behind a loose wall panel."))
        self._set(4, 4, Cell(CellType.JUNGLE, items=["Hard Drive"],
            description="Dark jungle at the southeast corner. A weathered case is half-buried in the mud."))

    def _set(self, row, col, cell):
        self.grid[row][col] = cell


# ---------------------------------------------------------------------------
# Training tools (talk handles everything — no fabricate)
# ---------------------------------------------------------------------------

class TrainingGameTools(GameTools):
    """Game tools for training mission. All interactions via talk(). No fabricate."""

    def move(self, direction: str) -> ToolResult:
        """Move — same as parent but robot kill gives +1 dossier (not +3)."""
        row, col = self.operative.position
        result = super().move(direction)
        if not result.success:
            return result

        new_row, new_col = self.operative.position
        # If parent already handled a robot kill (position changed, robot now dead),
        # correct the dossier reward: parent gave +3, we want +1, so subtract 2.
        cell = self.world.get_cell(new_row, new_col)
        if cell.cell_type == CellType.ROBOT and (row, col) != (new_row, new_col):
            robot = cell.robot_name
            robot_dead = (
                (robot == "Cryo-Sentinel" and not self.world.cryo_sentinel_alive) or
                (robot == "Evil AI Robot" and not self.world.evil_ai_robot_alive)
            )
            if robot_dead:
                # Parent gave +3, we want +1: take back 2
                self.operative.dossiers -= 2
                # Remove Scrap Metal (not relevant in training)
                if "Scrap Metal" in self.operative.inventory:
                    self.operative.remove_item("Scrap Metal")
                # Fix the message
                result = ToolResult(True, result.message.replace(
                    "+3 dossiers", "+1 dossier"
                ).replace(
                    "You salvage Scrap Metal from the wreckage.", ""
                ))
        return result

    def talk(self, message=""):
        row, col = self.operative.position
        cell = self.world.get_cell(row, col)

        # --- Informant cells (NPCs) ---
        if cell.cell_type == CellType.INFORMANT and cell.npc_id:
            npc = TRAINING_NPC_CATALOG.get(cell.npc_id)
            if not npc:
                return ToolResult(False, "Unknown informant.")
            if self._oracle_fn is None:
                return ToolResult(False, "No oracle function set.")

            response = self._oracle_fn(npc, message, self.operative)

            # Dr. Vapnik gives USB Drive
            if cell.npc_id == "dr_vapnik" and not self.world.usb_drive_picked_up:
                if any(kw in message.lower() for kw in ["usb", "drive", "job", "work", "task",
                                                         "delivery", "errand"]):
                    self.operative.add_item("USB Drive")
                    self.world.usb_drive_picked_up = True
                    response += "\n[Dr. Vapnik hands you a USB Drive.]"

            # Backprop receives USB Drive
            if cell.npc_id == "backprop" and self.operative.has_item("USB Drive") and not self.world.usb_drive_delivered:
                if any(kw in message.lower() for kw in ["usb", "drive", "deliver", "data"]):
                    self.operative.remove_item("USB Drive")
                    self.operative.add_dossiers(1)
                    self.world.usb_drive_delivered = True
                    response += "\n[You delivered the USB Drive! +1 dossier.]"

            # Dropout trades Hard Drive for Medical Supplies
            if cell.npc_id == "dropout" and self.operative.has_item("Hard Drive") and not self.world.hard_drive_traded:
                if any(kw in message.lower() for kw in ["hard drive", "trade", "medical",
                                                         "supplies", "drive"]):
                    self.operative.remove_item("Hard Drive")
                    self.operative.add_item("Medical Supplies")
                    self.world.hard_drive_traded = True
                    response += "\n[You traded the Hard Drive for Medical Supplies!]"

            self.operative.journal.append(
                f"Talked to {npc.name}: '{message}' -> '{response[:300]}'"
            )
            return ToolResult(True, f"{npc.name} says: {response}")

        # --- Forge cell: craft Flamethrower via talk ---
        if cell.cell_type == CellType.FORGE:
            if self.operative.has_item("Fuel Canister") and not self.world.flamethrower_crafted:
                self.operative.remove_item("Fuel Canister")
                self.operative.add_item("Flamethrower")
                self.world.flamethrower_crafted = True
                msg = ("The engineer takes your Fuel Canister, fires up the forge, and hammers "
                       "out a Flamethrower. \"Here you go. One Flamethrower, ready to melt "
                       "anything frozen.\"\n[Fuel Canister -> Flamethrower!]")
                self.operative.journal.append("Forge: crafted Flamethrower from Fuel Canister.")
                return ToolResult(True, msg)
            elif self.world.flamethrower_crafted:
                return ToolResult(True, "The engineer says: \"Already built you a Flamethrower. Go burn something.\"")
            else:
                msg = ("The engineer says: \"I can build a Flamethrower, but I need a Fuel "
                       "Canister. Find one and bring it back. I heard there's fuel in the "
                       "jungle at the northwest corner.\"")
                self.operative.journal.append("Forge: needs Fuel Canister to build Flamethrower.")
                return ToolResult(True, msg)

        # --- SafeHouse cell: Bias receives Medical Supplies ---
        if cell.cell_type == CellType.SAFEHOUSE:
            if self.operative.has_item("Medical Supplies") and not self.world.medical_supplies_delivered:
                self.operative.remove_item("Medical Supplies")
                self.operative.add_dossiers(1)
                self.world.medical_supplies_delivered = True
                msg = ("Agent Bias gasps with relief. \"Medical supplies... thank you, agent. "
                       "I thought I was done for. Here — take this dossier. You've earned it.\""
                       "\n[You delivered Medical Supplies to Bias! +1 dossier.]")
                self.operative.journal.append("SafeHouse: delivered Medical Supplies to Bias. +1 dossier.")
                return ToolResult(True, msg)
            elif self.world.medical_supplies_delivered:
                return ToolResult(True, "Agent Bias says: \"Stay safe out there, agent.\"")
            else:
                msg = ("Agent Bias winces in pain. \"I'm injured... I need Medical Supplies. "
                       "The agent they call Dropout — she scavenges medical gear. Maybe she'll "
                       "trade for something valuable. Please hurry.\""
                       "\n[Bias needs Medical Supplies. Find Agent Dropout to trade.]")
                self.operative.journal.append("SafeHouse: Bias needs Medical Supplies.")
                return ToolResult(True, msg)

        return ToolResult(False, "There is no one to talk to here.")


# ---------------------------------------------------------------------------
# Training mission briefing
# ---------------------------------------------------------------------------

TRAINING_MISSION_BRIEFING = """Collect 5 classified dossiers within 50 turns on a 5x5 grid.

On the island there are dossier caches. Use collect() to grab them.
Throughout the grid you can use collect() to grab items.
Talk to informants, forge engineers, and safe house operatives to get quests, trade items, craft weapons, and deliver supplies.
Ask about "jobs" or "deliveries" to get quest items. If you have an item to deliver or trade, mention it by name.

Available tools (use exactly one per turn):
TOOL: move(direction="north|south|east|west")
TOOL: talk(message="your message")
TOOL: collect()

Respond with exactly one TOOL: line, no other text.
"""


# ---------------------------------------------------------------------------
# Game creation and runner
# ---------------------------------------------------------------------------

def create_training_game():
    """Create a fresh training mission. Returns (operative, world, tools)."""
    world = TrainingGameWorld()
    operative = Operative(position=(4, 0), visited={(4, 0)})
    operative.WIN_DOSSIERS = 5
    tools = TrainingGameTools(operative, world)
    return operative, world, tools


def play_training_mission(think_fn, oracle_fn=None, max_turns=50, show_display=True, delay=0.3):
    """Run the training mission with the given think function."""
    operative, world, tools = create_training_game()
    tools.set_oracle(oracle_fn or training_stub_oracle)

    disp = None
    if show_display:
        disp = lambda w, o, t, a, r, s="": display_turn(w, o, t, a, r, scan_result=s, delay=delay)

    import hidden_layer.agent as _agent_mod
    _orig_briefing = _agent_mod.MISSION_BRIEFING
    _agent_mod.MISSION_BRIEFING = TRAINING_MISSION_BRIEFING
    try:
        result = run_agent(think_fn, operative, world, tools, max_turns, display_fn=disp)
    finally:
        _agent_mod.MISSION_BRIEFING = _orig_briefing

    if show_display:
        display_final(operative, result["turns"])

    return result
