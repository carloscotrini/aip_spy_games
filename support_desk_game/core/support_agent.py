"""
SupportAgent — Player state for The Support Layer.

Equivalent to Operative in the spy game. Tracks the LLM agent's
context budget (health), CSAT stars (dossiers), collected knowledge
snippets (inventory), and shift log (journal).
"""

from __future__ import annotations
from dataclasses import dataclass, field

MAX_CONTEXT_BUDGET = 3
WIN_CSAT_STARS = 10  # full game; micro overrides to 3


@dataclass
class SupportAgent:
    """The player: an LLM agent staffing a support desk."""

    context_budget: int = MAX_CONTEXT_BUDGET
    csat_stars: int = 0
    snippets: list[str] = field(default_factory=list)
    current_ticket_id: str | None = None
    resolved_tickets: list[str] = field(default_factory=list)
    escalated_tickets: list[str] = field(default_factory=list)
    shift_log: list[str] = field(default_factory=list)

    # --- Snippet (inventory) helpers ---

    def has_snippet(self, name: str) -> bool:
        return name in self.snippets

    def add_snippet(self, name: str) -> None:
        if name not in self.snippets:
            self.snippets.append(name)

    def remove_snippet(self, name: str) -> None:
        if name in self.snippets:
            self.snippets.remove(name)

    # --- CSAT (dossier) helpers ---

    def add_csat(self, amount: int = 1) -> None:
        self.csat_stars += amount

    def lose_csat(self, amount: int = 1) -> None:
        self.csat_stars = max(0, self.csat_stars - amount)

    # --- Context budget (health) helpers ---

    def take_damage(self, amount: int = 1) -> None:
        self.context_budget = max(0, self.context_budget - amount)

    def heal(self, amount: int = 1) -> None:
        self.context_budget = min(MAX_CONTEXT_BUDGET, self.context_budget + amount)

    # --- Status ---

    @property
    def is_alive(self) -> bool:
        return self.context_budget > 0

    @property
    def has_won(self) -> bool:
        return self.csat_stars >= WIN_CSAT_STARS

    def log(self, entry: str) -> None:
        self.shift_log.append(entry)
