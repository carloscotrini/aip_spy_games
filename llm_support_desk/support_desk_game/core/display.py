"""
Terminal display — The Support Layer.

Equivalent to display.py in the spy game. Renders game state to the terminal
for the interactive / notebook mode.
"""

from __future__ import annotations

from .support_agent import SupportAgent, MAX_CONTEXT_BUDGET
from .support_desk import SupportDesk, TicketStatus


def display_shift_state(agent: SupportAgent, desk: SupportDesk, turn: int, max_turns: int, win_csat: int = 3):
    """Print the current shift state to the terminal."""
    print("\n" + "=" * 60)
    print(f"  TURN {turn}/{max_turns}")
    print(f"  CSAT: {'★' * agent.csat_stars}{'☆' * (win_csat - agent.csat_stars)} ({agent.csat_stars}/{win_csat})")
    budget_bar = "●" * agent.context_budget + "○" * (MAX_CONTEXT_BUDGET - agent.context_budget)
    print(f"  Context Budget: {budget_bar} ({agent.context_budget}/{MAX_CONTEXT_BUDGET})")
    print(f"  Snippets: {', '.join(agent.snippets) if agent.snippets else 'none'}")
    print("=" * 60)

    if agent.current_ticket_id:
        ticket = desk.get_ticket(agent.current_ticket_id)
        if ticket:
            print(f"\n  📋 Working on: {ticket.id} — \"{ticket.subject}\"")
            print(f"     Customer: {ticket.customer.name} ({ticket.customer.tone})")
            patience_bar = "█" * ticket.patience_remaining + "░" * (ticket.patience - ticket.patience_remaining)
            print(f"     Patience: [{patience_bar}] {ticket.patience_remaining}/{ticket.patience}")
    else:
        print("\n  📥 INBOX")
        open_tickets = desk.open_tickets()
        for t in open_tickets:
            priority_icon = {"low": "🟢", "medium": "🟡", "high": "🟠", "urgent": "🔴"}.get(t.priority.value, "⚪")
            print(f"    {priority_icon} {t.id} | \"{t.subject}\" | patience: {t.patience_remaining}/{t.patience}")
        if not open_tickets:
            print("    (empty)")

    # Show resolved/escalated/expired summary
    resolved = [t for t in desk.inbox if t.status == TicketStatus.RESOLVED]
    escalated = [t for t in desk.inbox if t.status == TicketStatus.ESCALATED]
    expired = [t for t in desk.inbox if t.status == TicketStatus.EXPIRED]
    if resolved or escalated or expired:
        print(f"\n  Resolved: {len(resolved)} | Escalated: {len(escalated)} | Expired: {len(expired)}")
    print()


def display_turn(turn: int, observation: str, action: str, result: str):
    """Display a single turn for the agent loop."""
    print(f"\n--- Turn {turn} ---")
    print(f"  Action: {action}")
    print(f"  Result: {result}")
