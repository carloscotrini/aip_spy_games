"""Operative state management for The Hidden Layer."""

from dataclasses import dataclass, field


@dataclass
class Operative:
    """The player character — Agent Lambda."""

    health: int = 3
    dossiers: int = 0
    inventory: list[str] = field(default_factory=list)
    position: tuple[int, int] = (7, 0)
    visited: set[tuple[int, int]] = field(default_factory=lambda: {(7, 0)})
    journal: list[str] = field(default_factory=list)

    MAX_HEALTH = 3
    WIN_DOSSIERS = 10

    def has_item(self, name: str) -> bool:
        return name in self.inventory

    def add_item(self, name: str) -> None:
        self.inventory.append(name)

    def remove_item(self, name: str) -> bool:
        if name in self.inventory:
            self.inventory.remove(name)
            return True
        return False

    def add_dossiers(self, amount: int) -> None:
        self.dossiers += amount

    def spend_dossiers(self, amount: int) -> bool:
        if self.dossiers >= amount:
            self.dossiers -= amount
            return True
        return False

    def take_damage(self, amount: int) -> None:
        self.health = max(0, self.health - amount)

    def heal(self, amount: int) -> None:
        self.health = min(self.MAX_HEALTH, self.health + amount)

    @property
    def is_alive(self) -> bool:
        return self.health > 0

    @property
    def has_won(self) -> bool:
        return self.dossiers >= self.WIN_DOSSIERS and self.is_alive

    def status_text(self) -> str:
        inv = ", ".join(self.inventory) if self.inventory else "empty"
        return (
            f"Health: {self.health}/{self.MAX_HEALTH} | "
            f"Dossiers: {self.dossiers} | "
            f"Position: {self.position} | "
            f"Inventory: [{inv}] | "
            f"Visited: {len(self.visited)} cells"
        )
