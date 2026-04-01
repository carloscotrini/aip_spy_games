"""Game world: map, cells, NPCs, items, and quest data for The Hidden Layer."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Cell types
# ---------------------------------------------------------------------------

class CellType(Enum):
    OPEN = "open"
    JUNGLE = "jungle"
    WALL = "wall"
    CACHE = "cache"
    INFORMANT = "informant"
    FORGE = "forge"
    LAB = "lab"
    SAFEHOUSE = "safehouse"
    ROBOT = "robot"
    HELICOPTER = "helicopter"

    @property
    def emoji(self) -> str:
        return {
            CellType.OPEN: "\u00b7",
            CellType.JUNGLE: "\U0001f334",        # 🌴
            CellType.WALL: "\U0001f9f1",           # 🧱
            CellType.CACHE: "\U0001f4c1",          # 📁
            CellType.INFORMANT: "\U0001f575\ufe0f", # 🕵️
            CellType.FORGE: "\u2692\ufe0f",         # ⚒️
            CellType.LAB: "\U0001f52c",             # 🔬
            CellType.SAFEHOUSE: "\U0001f3e0",       # 🏠
            CellType.ROBOT: "\U0001f916",           # 🤖
            CellType.HELICOPTER: "\U0001f681",      # 🚁
        }[self]

    @property
    def label(self) -> str:
        return {
            CellType.OPEN: "Open ground",
            CellType.JUNGLE: "Jungle",
            CellType.WALL: "Concrete wall (impassable)",
            CellType.CACHE: "Dossier cache",
            CellType.INFORMANT: "Informant",
            CellType.FORGE: "Weapons Forge",
            CellType.LAB: "Research Lab",
            CellType.SAFEHOUSE: "Safe House",
            CellType.ROBOT: "Robot",
            CellType.HELICOPTER: "Helicopter",
        }[self]


# ---------------------------------------------------------------------------
# Items
# ---------------------------------------------------------------------------

@dataclass
class Item:
    name: str
    description: str
    quest_item: bool = False


ITEM_CATALOG: dict[str, Item] = {
    # Quest materials
    "Fuel Canister": Item("Fuel Canister", "A canister of high-octane fuel.", quest_item=True),
    "Hard Drive": Item("Hard Drive", "An encrypted hard drive from OVERFIT's servers.", quest_item=True),
    "Medical Supplies": Item("Medical Supplies", "A field medic kit with bandages and antibiotics.", quest_item=True),
    "Virus Code": Item("Virus Code", "Source code for a computer virus targeting OVERFIT's AI.", quest_item=True),
    "USB Drive": Item("USB Drive", "A USB drive with intercepted OVERFIT data.", quest_item=True),
    "Microfilm": Item("Microfilm", "A roll of microfilm with stolen intelligence.", quest_item=True),
    "Radio Codebook": Item("Radio Codebook", "An encrypted codebook for re-establishing comms.", quest_item=True),
    # Weapons
    "Flamethrower": Item("Flamethrower", "A portable flamethrower. Effective against cryo systems.", quest_item=True),
    "Computer Virus": Item("Computer Virus", "A compiled virus on a USB stick. Lethal to AI systems.", quest_item=True),
    # Loot
    "Scrap Metal": Item("Scrap Metal", "Salvaged robot parts. Might be worth something at the lab."),
}


# ---------------------------------------------------------------------------
# NPCs (Informants)
# ---------------------------------------------------------------------------

@dataclass
class NPC:
    name: str
    personality: str
    knowledge: list[str]
    style: str
    greeting: str


NPC_CATALOG: dict[str, NPC] = {
    "dr_vapnik": NPC(
        name="Dr. Vapnik",
        personality="Cryptic, speaks in statistical metaphors. Old, disillusioned, once designed OVERFIT's core algorithms.",
        knowledge=[
            "The Cryo-Sentinel guards the northern server room (around row 2). It freezes intruders solid.",
            "Only fire can defeat the Cryo-Sentinel — 'summer's fury melts winter's grip'.",
            "The Weapons Forge to the south can build a flamethrower, but needs a Fuel Canister.",
            "There is a dossier cache nearby to the southwest.",
            "Agent Dropout in the center of the island knows where to find materials.",
            "He has a USB Drive that needs to reach Informant Backprop.",
        ],
        style="Speaks in statistical metaphors. Uses phrases like 'data point', 'global minimum', 'converge'. Never gives direct coordinates.",
        greeting="Ah, another data point walks in... Tell me, agent — do you seek the global minimum, or will you settle for a local one?",
    ),
    "backprop": NPC(
        name="Informant Backprop",
        personality="Paranoid double agent, fast-talking, always looking over his shoulder. Passes information backward through the network.",
        knowledge=[
            "The Evil AI Robot lurks in the eastern wing (around row 4, eastern side). It controls all cameras and locks.",
            "Only a computer virus can take down the Evil AI Robot.",
            "Agent Bias at the Northern Safe House had the virus code before she was compromised.",
            "Bias needs medical supplies — she's injured and can't retrieve what she hid.",
            "The agent they call Dropout scavenges medical gear. She might trade.",
            "He has a Microfilm that needs to reach Dr. Vapnik. Will pay 2 dossiers.",
        ],
        style="Paranoid, fast-talking. Uses spy jargon. Calls the operative 'asset' or 'contact'. Always whispers. Never gives direct coordinates.",
        greeting="Psst — you didn't hear this from me, and I didn't hear it from my source... but the gradient points east.",
    ),
    "dropout": NPC(
        name="Agent Dropout",
        personality="Burned spy who 'dropped out' of the network. Lives off-grid in the jungle. Expert in improvised equipment.",
        knowledge=[
            "Fuel Canisters can be found in the jungle to the northwest, where the western palms grow tallest (the jungle at row 2, column 0).",
            "A Hard Drive is hidden in the dark jungle far to the north (the jungle at row 0, column 2).",
            "She has Medical Supplies scavenged from a supply drop. Will trade for a Hard Drive.",
            "She heard Agent Bias got hurt at the Northern Safe House and needs medical supplies.",
            "The Weapons Forge and the Research Lab can both build powerful weapons from raw materials.",
        ],
        style="Bitter, sarcastic, but helpful. References being 'dropped' from the program. Uses nature metaphors mixed with tech jargon. Never gives direct coordinates.",
        greeting="They dropped me from the program. Said I was 'reducing overfitting.' Jokes on them — I'm the only one still standing.",
    ),
}


# ---------------------------------------------------------------------------
# Facilities (Forge and Lab)
# ---------------------------------------------------------------------------

@dataclass
class ForgeInfo:
    name: str
    description: str
    sells: dict[str, int]               # item_name -> dossier cost
    crafts: dict[str, tuple[str, int]]   # result_item -> (required_item, dossier_cost)
    buys: dict[str, int]                 # item_name -> dossiers earned


FORGE_CATALOG: dict[tuple[int, int], ForgeInfo] = {
    (6, 2): ForgeInfo(
        name="Weapons Forge",
        description="A makeshift workshop. A burly engineer wipes grease from his hands.",
        sells={},
        crafts={"Flamethrower": ("Fuel Canister", 1)},
        buys={},
    ),
}

LAB_CATALOG: dict[tuple[int, int], ForgeInfo] = {
    (4, 1): ForgeInfo(
        name="Research Lab",
        description="A cluttered lab full of screens and wires. A wild-haired scientist spins in his chair.",
        sells={},
        crafts={"Computer Virus": ("Virus Code", 1)},
        buys={"Scrap Metal": 1},
    ),
}

# Unified catalog for tool lookups
FACILITY_CATALOG: dict[tuple[int, int], ForgeInfo] = {**FORGE_CATALOG, **LAB_CATALOG}


# ---------------------------------------------------------------------------
# Safe Houses
# ---------------------------------------------------------------------------

@dataclass
class SafeHouseInfo:
    name: str
    description: str


SAFEHOUSE_CATALOG: dict[tuple[int, int], SafeHouseInfo] = {
    (7, 4): SafeHouseInfo(
        name="Southern Safe House",
        description="A hidden basement beneath a ruined building. A handler sits by a radio, looking tense.",
    ),
    (2, 5): SafeHouseInfo(
        name="Northern Safe House",
        description="A concealed room behind a false wall. A woman clutches her side, wincing.",
    ),
}


# ---------------------------------------------------------------------------
# Cells
# ---------------------------------------------------------------------------

@dataclass
class Cell:
    cell_type: CellType
    items: list[str] = field(default_factory=list)
    npc_id: Optional[str] = None
    robot_name: Optional[str] = None
    trap: bool = False
    facility_pos: Optional[tuple[int, int]] = None
    safehouse_pos: Optional[tuple[int, int]] = None
    description: str = ""

    @property
    def npc(self) -> Optional[NPC]:
        if self.npc_id:
            return NPC_CATALOG.get(self.npc_id)
        return None


# ---------------------------------------------------------------------------
# Game World
# ---------------------------------------------------------------------------

class GameWorld:
    """8x8 military base grid on Isla Perdida."""

    ROWS = 8
    COLS = 8

    def __init__(self):
        self.grid: list[list[Cell]] = []
        # Delivery quest flags
        self.usb_drive_picked_up = False
        self.usb_drive_delivered = False
        self.microfilm_picked_up = False
        self.microfilm_delivered = False
        self.codebook_picked_up = False
        self.codebook_delivered = False
        # Trade / craft chain flags
        self.hard_drive_traded = False
        self.medical_supplies_delivered = False
        self.virus_code_received = False
        # Robot flags
        self.cryo_sentinel_alive = True
        self.evil_ai_robot_alive = True
        self.build_map()

    def build_map(self):
        """Construct the 8x8 grid."""
        self.grid = [
            [Cell(CellType.OPEN) for _ in range(self.COLS)]
            for _ in range(self.ROWS)
        ]

        # Row 0: 🚁 · 🌴 · · 🌴! · 📁
        self._set(0, 0, Cell(CellType.HELICOPTER, description="A helicopter sits on the landing pad, rotors still. The northwest corner of the base."))
        self._set(0, 2, Cell(CellType.JUNGLE, items=["Hard Drive"], description="Dark jungle. A weathered case is half-buried in the mud."))
        self._set(0, 5, Cell(CellType.JUNGLE, trap=True, description="Thick jungle with tripwires strung between the trees."))
        self._set(0, 7, Cell(CellType.CACHE, items=["dossier_1"], description="An unlocked filing cabinet behind a collapsed wall."))

        # Row 1: · · · 🧱 · · · ·
        self._set(1, 3, Cell(CellType.WALL, description="Reinforced concrete wall."))

        # Row 2: 🌴 🤖 · 🧱 · 🏠 · 🌴
        self._set(2, 0, Cell(CellType.JUNGLE, items=["Fuel Canister"], description="Dense jungle. The western palms tower overhead. Something metallic glints under the roots."))
        self._set(2, 1, Cell(CellType.ROBOT, robot_name="Cryo-Sentinel", description="A freezing corridor. Ice coats the walls. A hulking robot blocks the path, frost pouring from its vents."))
        self._set(2, 3, Cell(CellType.WALL, description="Reinforced concrete wall."))
        self._set(2, 5, Cell(CellType.SAFEHOUSE, safehouse_pos=(2, 5), description="The Northern Safe House. Agent Bias is here, injured and cut off from HQ."))
        self._set(2, 7, Cell(CellType.JUNGLE, description="A quiet stretch of jungle. Insects buzz overhead."))

        # Row 3: · · · · 🕵️ · · ·
        self._set(3, 4, Cell(CellType.INFORMANT, npc_id="dropout", description="A camouflaged hideout in the overgrowth. A woman sharpens a knife."))

        # Row 4: · 🔬 · 🧱 · · 🤖 ·
        self._set(4, 1, Cell(CellType.LAB, facility_pos=(4, 1), description="The Research Lab glows with screens and blinking LEDs."))
        self._set(4, 3, Cell(CellType.WALL, description="Reinforced concrete wall."))
        self._set(4, 6, Cell(CellType.ROBOT, robot_name="Evil AI Robot", description="Total darkness. Screens flicker. A synthetic voice echoes from the shadows."))

        # Row 5: 📁 · · 🕵️ · 🌴 · ·
        self._set(5, 0, Cell(CellType.CACHE, items=["dossier_1"], description="A dossier is wedged behind a loose wall panel."))
        self._set(5, 3, Cell(CellType.INFORMANT, npc_id="backprop", description="A figure in a trench coat steps out from behind a pillar, eyes darting."))
        self._set(5, 5, Cell(CellType.JUNGLE, description="Dense jungle. Nothing but mosquitoes."))

        # Row 6: · · ⚒️ · · · 📁 ·
        self._set(6, 2, Cell(CellType.FORGE, facility_pos=(6, 2), description="The Weapons Forge. Sparks fly as an engineer hammers at something on an anvil."))
        self._set(6, 6, Cell(CellType.CACHE, items=["dossier_1"], description="Scattered documents on the floor of an abandoned guard post. Someone forgot to shred these."))

        # Row 7: 🦸 🕵️ · · 🏠 · · 🌴
        self._set(7, 0, Cell(CellType.OPEN, description="The south shore. You can hear the waves. This is where you came ashore."))
        self._set(7, 1, Cell(CellType.INFORMANT, npc_id="dr_vapnik", description="A weathered shack beneath a palm tree. An old man sits on a crate, scribbling equations in the dirt."))
        self._set(7, 4, Cell(CellType.SAFEHOUSE, safehouse_pos=(7, 4), description="The Southern Safe House. A handler sits by a radio, looking tense."))
        self._set(7, 7, Cell(CellType.JUNGLE, description="Jungle thins out near the shore. The sound of waves is close."))

    def _set(self, row: int, col: int, cell: Cell):
        self.grid[row][col] = cell

    def get_cell(self, row: int, col: int) -> Cell:
        if 0 <= row < self.ROWS and 0 <= col < self.COLS:
            return self.grid[row][col]
        return Cell(CellType.WALL, description="The edge of the island.")

    def is_passable(self, row: int, col: int) -> bool:
        if not (0 <= row < self.ROWS and 0 <= col < self.COLS):
            return False
        return self.grid[row][col].cell_type != CellType.WALL

    def get_adjacent(self, row: int, col: int) -> dict[str, Optional[Cell]]:
        """Return adjacent cells keyed by direction."""
        directions = {
            "north": (row - 1, col),
            "south": (row + 1, col),
            "east": (row, col + 1),
            "west": (row, col - 1),
        }
        result = {}
        for direction, (r, c) in directions.items():
            if 0 <= r < self.ROWS and 0 <= c < self.COLS:
                result[direction] = self.grid[r][c]
            else:
                result[direction] = None  # out of bounds
        return result

    def get_visible_description(self, row: int, col: int) -> str:
        """Return a text description of what the operative can see from (row, col)."""
        lines = []
        current = self.get_cell(row, col)
        lines.append(f"You are at position ({row}, {col}).")
        if current.description:
            lines.append(f"Current location: {current.description}")

        adjacent = self.get_adjacent(row, col)
        for direction, cell in adjacent.items():
            if cell is None:
                lines.append(f"  {direction.capitalize()}: Edge of the island (impassable).")
            else:
                lines.append(f"  {direction.capitalize()}: {cell.cell_type.label} {cell.cell_type.emoji}")
        return "\n".join(lines)
