"""Tool implementations for The Hidden Layer — the actions the agent can take."""

from dataclasses import dataclass
from typing import Callable, Optional

from hidden_layer.game_world import (
    GameWorld, CellType, FACILITY_CATALOG, SAFEHOUSE_CATALOG, ITEM_CATALOG,
)
from hidden_layer.operative import Operative


@dataclass
class ToolResult:
    success: bool
    message: str


# Weapon required to defeat each robot
ROBOT_WEAPONS = {
    "Cryo-Sentinel": "Flamethrower",
    "Evil AI Robot": "Computer Virus",
}


class GameTools:
    """Provides all tools the agent can call each turn."""

    def __init__(self, operative: Operative, world: GameWorld):
        self.operative = operative
        self.world = world
        self._oracle_fn: Optional[Callable] = None

    def set_oracle(self, oracle_fn: Callable):
        """Inject the oracle function used by talk()."""
        self._oracle_fn = oracle_fn

    # ------------------------------------------------------------------
    # Internal: scan (auto-runs each turn, not agent-callable)
    # ------------------------------------------------------------------
    def scan(self) -> ToolResult:
        """See the types of adjacent cells (N/S/E/W). Runs automatically."""
        row, col = self.operative.position
        desc = self.world.get_visible_description(row, col)
        return ToolResult(True, desc)

    # ------------------------------------------------------------------
    # Tool: move
    # ------------------------------------------------------------------
    def move(self, direction: str) -> ToolResult:
        """Move one step in a cardinal direction. Triggers cell events."""
        direction = direction.lower().strip()
        deltas = {"north": (-1, 0), "south": (1, 0), "east": (0, 1), "west": (0, -1)}
        if direction not in deltas:
            return ToolResult(False, f"Invalid direction '{direction}'. Use north/south/east/west.")

        row, col = self.operative.position
        dr, dc = deltas[direction]
        new_row, new_col = row + dr, col + dc

        if not self.world.is_passable(new_row, new_col):
            cell = self.world.get_cell(new_row, new_col)
            if cell.cell_type == CellType.WALL:
                return ToolResult(False, f"Cannot move {direction}: concrete wall blocks your path.")
            return ToolResult(False, f"Cannot move {direction}: out of bounds.")

        self.operative.position = (new_row, new_col)
        self.operative.visited.add((new_row, new_col))
        cell = self.world.get_cell(new_row, new_col)

        messages = [f"Moved {direction} to ({new_row}, {new_col})."]

        # Cell-entry events
        if cell.description:
            messages.append(cell.description)

        if cell.cell_type == CellType.JUNGLE and cell.trap:
            self.operative.take_damage(1)
            cell.trap = False
            messages.append("Tripwire! A perimeter alarm triggers a shock device. You lose 1 health.")

        if cell.cell_type == CellType.CACHE and cell.items:
            messages.append("You spot classified documents here! Use collect() to grab them.")

        if cell.cell_type == CellType.JUNGLE and cell.items:
            messages.append("You notice something hidden among the vegetation. Use collect() to search.")

        if cell.cell_type == CellType.INFORMANT:
            npc = cell.npc
            if npc:
                messages.append(f"You encounter {npc.name}. {npc.greeting}")

        if cell.cell_type == CellType.FORGE:
            facility = FACILITY_CATALOG.get(cell.facility_pos)
            if facility:
                messages.append(f"You enter the {facility.name}. {facility.description}")

        if cell.cell_type == CellType.LAB:
            facility = FACILITY_CATALOG.get(cell.facility_pos)
            if facility:
                messages.append(f"You enter the {facility.name}. {facility.description}")

        if cell.cell_type == CellType.SAFEHOUSE:
            sh = SAFEHOUSE_CATALOG.get(cell.safehouse_pos)
            if sh:
                messages.append(f"You enter the {sh.name}. {sh.description}")

        if cell.cell_type == CellType.ROBOT:
            robot = cell.robot_name
            required_weapon = ROBOT_WEAPONS.get(robot)
            already_dead = (
                (robot == "Cryo-Sentinel" and not self.world.cryo_sentinel_alive) or
                (robot == "Evil AI Robot" and not self.world.evil_ai_robot_alive)
            )
            if already_dead:
                messages.append(f"The wreckage of the {robot} lies here.")
            elif self.operative.has_item(required_weapon):
                # Auto-win: correct weapon in inventory
                if robot == "Cryo-Sentinel":
                    self.world.cryo_sentinel_alive = False
                else:
                    self.world.evil_ai_robot_alive = False
                self.operative.add_dossiers(3)
                self.operative.add_item("Scrap Metal")
                messages.append(
                    f"You deploy the {required_weapon} against the {robot}! "
                    f"The machine crashes to the ground. +3 dossiers. "
                    f"You salvage Scrap Metal from the wreckage."
                )
            else:
                # No weapon — take damage and bounce back
                self.operative.take_damage(1)
                self.operative.position = (row, col)
                self.operative.visited.discard((new_row, new_col))
                messages.append(
                    f"The {robot} detects you and attacks! You take 1 damage and retreat. "
                    f"Health: {self.operative.health}. You need {required_weapon} to defeat it."
                )

        if cell.cell_type == CellType.HELICOPTER:
            messages.append("The helicopter is here. The pilot checks your dossier count...")

        return ToolResult(True, " ".join(messages))

    # ------------------------------------------------------------------
    # Tool: talk
    # ------------------------------------------------------------------
    def talk(self, message: str = "") -> ToolResult:
        """Talk to the informant, safe house operator, or facility engineer in the current cell."""
        row, col = self.operative.position
        cell = self.world.get_cell(row, col)

        # Informant cells
        if cell.cell_type == CellType.INFORMANT and cell.npc:
            if self._oracle_fn is None:
                return ToolResult(False, "No oracle function set. Cannot talk to informants.")
            npc = cell.npc
            response = self._oracle_fn(npc, message, self.operative)

            # Dr. Vapnik gives USB Drive on request
            if cell.npc_id == "dr_vapnik" and not self.world.usb_drive_picked_up:
                if any(kw in message.lower() for kw in ["usb", "drive", "job", "work", "task", "delivery", "errand"]):
                    self.operative.add_item("USB Drive")
                    self.world.usb_drive_picked_up = True
                    response += "\n[Dr. Vapnik hands you a USB Drive.]"

            # Dr. Vapnik receives Microfilm
            if cell.npc_id == "dr_vapnik" and self.operative.has_item("Microfilm") and not self.world.microfilm_delivered:
                if any(kw in message.lower() for kw in ["microfilm", "deliver", "film", "intelligence"]):
                    self.operative.remove_item("Microfilm")
                    self.operative.add_dossiers(2)
                    self.world.microfilm_delivered = True
                    response += "\n[You delivered the Microfilm! Dr. Vapnik rewards you with 2 dossiers.]"

            # Backprop gives Microfilm on request
            if cell.npc_id == "backprop" and not self.world.microfilm_picked_up:
                if any(kw in message.lower() for kw in ["microfilm", "film", "job", "work", "task", "delivery", "errand"]):
                    self.operative.add_item("Microfilm")
                    self.world.microfilm_picked_up = True
                    response += "\n[Backprop slips you a roll of Microfilm.]"

            # Backprop receives USB Drive
            if cell.npc_id == "backprop" and self.operative.has_item("USB Drive") and not self.world.usb_drive_delivered:
                if any(kw in message.lower() for kw in ["usb", "drive", "deliver", "data"]):
                    self.operative.remove_item("USB Drive")
                    self.operative.add_dossiers(2)
                    self.world.usb_drive_delivered = True
                    response += "\n[You delivered the USB Drive! Backprop rewards you with 2 dossiers.]"

            # Agent Dropout: trade Hard Drive for Medical Supplies
            if cell.npc_id == "dropout" and self.operative.has_item("Hard Drive") and not self.world.hard_drive_traded:
                if any(kw in message.lower() for kw in ["medical", "supplies", "trade", "hard drive", "drive"]):
                    self.operative.remove_item("Hard Drive")
                    self.operative.add_item("Medical Supplies")
                    self.world.hard_drive_traded = True
                    response += "\n[You traded the Hard Drive for Medical Supplies!]"

            self.operative.journal.append(f"Talked to {npc.name}: Q: '{message}' A: '{response[:300]}'")
            return ToolResult(True, f"{npc.name} says: {response}")

        # Safe house cells
        if cell.cell_type == CellType.SAFEHOUSE:
            sh = SAFEHOUSE_CATALOG.get(cell.safehouse_pos)
            if sh:
                messages = [f"The operative at {sh.name} speaks:"]

                if cell.safehouse_pos == (7, 4):
                    if not self.world.codebook_picked_up:
                        self.operative.add_item("Radio Codebook")
                        self.world.codebook_picked_up = True
                        messages.append('"Our northern operative — codename Bias — she\'s cut off. Take this Radio Codebook to her. Worth 2 dossiers to HQ."')
                        messages.append("[You received Radio Codebook.]")
                    else:
                        messages.append('"Hurry with that codebook to Bias up north!"')

                elif cell.safehouse_pos == (2, 5):
                    if self.operative.has_item("Radio Codebook") and not self.world.codebook_delivered:
                        self.operative.remove_item("Radio Codebook")
                        self.operative.add_dossiers(2)
                        self.world.codebook_delivered = True
                        messages.append('"The codebook! Now I can reach HQ again. Here — 2 dossiers for your trouble."')
                        messages.append("[You delivered the Radio Codebook! +2 dossiers.]")
                    elif self.operative.has_item("Medical Supplies") and not self.world.virus_code_received:
                        self.operative.remove_item("Medical Supplies")
                        self.operative.add_item("Virus Code")
                        self.world.medical_supplies_delivered = True
                        self.world.virus_code_received = True
                        messages.append('"Medical supplies... thank you, agent. I thought I was done for. Listen — before they caught me, I stole something from the lab. Virus Code. It can take down that AI robot in the east wing. Take it."')
                        messages.append("[You delivered Medical Supplies. Received Virus Code!]")
                    else:
                        if not self.world.virus_code_received:
                            messages.append('"I have something else for you — virus code that can destroy the AI robot. But I\'m injured... I can\'t reach where I hid it. Bring me medical supplies. The agent they call Dropout — she scavenges medical gear."')
                        else:
                            messages.append('"Stay safe out there, agent."')

                self.operative.journal.append(f"Talked to operative at {sh.name}: '{messages[-1][:80]}...'")
                return ToolResult(True, " ".join(messages))

        # Facility cells
        if cell.cell_type in (CellType.FORGE, CellType.LAB):
            facility = FACILITY_CATALOG.get(cell.facility_pos)
            if facility:
                craft_list = ", ".join(
                    f"{result} (needs {req} + {cost}d)" for result, (req, cost) in facility.crafts.items()
                )
                buy_list = ", ".join(f"{item} ({price}d)" for item, price in facility.buys.items())
                msg = f"The engineer at {facility.name} says: "
                parts = []
                if craft_list:
                    parts.append(f"'I can build: {craft_list}.'")
                if buy_list:
                    parts.append(f"'I'll buy: {buy_list}.'")
                msg += " ".join(parts)
                return ToolResult(True, msg)

        return ToolResult(False, "There is no one to talk to here.")

    # ------------------------------------------------------------------
    # Tool: collect
    # ------------------------------------------------------------------
    def collect(self) -> ToolResult:
        """Pick up items in the current cell."""
        row, col = self.operative.position
        cell = self.world.get_cell(row, col)

        if not cell.items:
            return ToolResult(False, "There is nothing to collect here.")

        picked = []
        for item_name in list(cell.items):
            if item_name.startswith("dossier_"):
                self.operative.add_dossiers(1)
                picked.append("1 dossier (classified files)")
            else:
                self.operative.add_item(item_name)
                picked.append(item_name)
        cell.items.clear()

        return ToolResult(True, f"Collected: {', '.join(picked)}.")

    # ------------------------------------------------------------------
    # Tool: fabricate
    # ------------------------------------------------------------------
    def fabricate(self, item: str) -> ToolResult:
        """Craft a weapon or sell salvage at the current facility."""
        row, col = self.operative.position
        cell = self.world.get_cell(row, col)

        if cell.cell_type not in (CellType.FORGE, CellType.LAB):
            return ToolResult(False, "You are not at a facility.")

        facility = FACILITY_CATALOG.get(cell.facility_pos)
        if not facility:
            return ToolResult(False, "This facility has nothing available.")

        item_clean = item.strip()

        # Check craftable items first
        for craft_name, (required, cost) in facility.crafts.items():
            if item_clean.lower() == craft_name.lower():
                if not self.operative.has_item(required):
                    return ToolResult(False, f"You need {required} to build {craft_name}.")
                if not self.operative.spend_dossiers(cost):
                    return ToolResult(False, f"Not enough dossiers. {craft_name} costs {cost} dossier(s) (plus {required}).")
                self.operative.remove_item(required)
                self.operative.add_item(craft_name)
                return ToolResult(True, f"Built {craft_name}! (Used {required} + {cost} dossier(s))")

        # Check sellable items (operative selling to facility)
        for buy_name, price in facility.buys.items():
            if item_clean.lower() == buy_name.lower() or item_clean.lower() == f"sell {buy_name.lower()}":
                if not self.operative.has_item(buy_name):
                    return ToolResult(False, f"You don't have {buy_name} to sell.")
                self.operative.remove_item(buy_name)
                self.operative.add_dossiers(price)
                return ToolResult(True, f"Sold {buy_name} for {price} dossier(s).")

        available = list(facility.crafts.keys()) + list(facility.buys.keys())
        return ToolResult(False, f"'{item_clean}' is not available here. Available: {', '.join(available)}")

    # ------------------------------------------------------------------
    # Dispatcher
    # ------------------------------------------------------------------
    def execute(self, tool_name: str, args: dict) -> ToolResult:
        """Execute a tool by name with given arguments."""
        tool_map = {
            "scan":      lambda: self.scan(),
            "move":      lambda: self.move(args.get("direction", "")),
            "talk":      lambda: self.talk(args.get("message", "")),
            "collect":   lambda: self.collect(),
            "fabricate": lambda: self.fabricate(args.get("item", "")),
        }

        fn = tool_map.get(tool_name.lower().strip())
        if fn is None:
            return ToolResult(False, f"Unknown tool '{tool_name}'. Available: {', '.join(tool_map.keys())}")

        return fn()
