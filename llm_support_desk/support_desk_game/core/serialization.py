"""
Serialization — JSON state for The Support Layer web frontend.

Equivalent to serialization.py in the spy game. Converts game state
to a JSON-friendly dict for the WebSocket frontend.
"""

from __future__ import annotations

from .support_agent import SupportAgent, MAX_CONTEXT_BUDGET
from .support_desk import SupportDesk, Ticket, TicketStatus


def ticket_to_dict(ticket: Ticket, is_current: bool = False) -> dict:
    """Serialize a ticket for the frontend."""
    base = {
        "id": ticket.id,
        "subject": ticket.subject,
        "priority": ticket.priority.value,
        "topic": ticket.topic.value,
        "status": ticket.status.value,
        "customer_name": ticket.customer.name,
        "customer_tone": ticket.customer.tone,
        "customer_plan": ticket.customer.plan,
        "patience": ticket.patience,
        "patience_remaining": ticket.patience_remaining,
        "difficulty": ticket.difficulty,
        "csat_reward": ticket.csat_reward,
        "is_adversarial": ticket.is_adversarial,
        "is_read": ticket.is_read,
    }

    # Only include message content if the ticket has been read (fog of war)
    if ticket.is_read or is_current:
        base["messages"] = [
            {"sender": m.sender, "content": m.content}
            for m in ticket.messages
        ]
    else:
        base["messages"] = []

    # Chain progress
    if ticket.chain_steps:
        base["chain_steps"] = ticket.chain_steps
        base["chain_progress"] = ticket.chain_progress
    else:
        base["chain_steps"] = None
        base["chain_progress"] = 0

    return base


def game_state_to_dict(
    agent: SupportAgent,
    desk: SupportDesk,
    turn: int,
    max_turns: int,
    win_csat: int = 3,
) -> dict:
    """
    Serialize the full game state to a dict for the frontend.
    """
    current_id = agent.current_ticket_id

    inbox = [
        ticket_to_dict(t, is_current=(t.id == current_id))
        for t in desk.inbox
    ]

    # Coworker info
    coworkers = {}
    for cid, cw in desk.coworkers.items():
        coworkers[cid] = {
            "name": cw.name,
            "role": cw.role,
            "personality": cw.personality,
            "greeting": cw.greeting,
            "consult_count": cw.consult_count,
        }

    # Macro info
    macros = {}
    for mid, m in desk.macros.items():
        macros[mid] = {
            "name": m.name,
            "description": m.description,
            "requires_authorization": m.requires_authorization,
            "authorized": m.authorized,
        }

    # KB article titles (not full content — agent must search to get content)
    kb_titles = {
        kid: {"title": article.title, "tags": article.tags}
        for kid, article in desk.knowledge_base.items()
    }

    return {
        "turn": turn,
        "max_turns": max_turns,
        "context_budget": agent.context_budget,
        "max_context_budget": MAX_CONTEXT_BUDGET,
        "csat_stars": agent.csat_stars,
        "win_csat": win_csat,
        "snippets": agent.snippets,
        "current_ticket_id": current_id,
        "resolved_tickets": agent.resolved_tickets,
        "escalated_tickets": agent.escalated_tickets,
        "shift_log": agent.shift_log[-5:],  # last 5 entries
        "inbox": inbox,
        "coworkers": coworkers,
        "macros": macros,
        "kb_titles": kb_titles,
        "is_alive": agent.is_alive,
        "has_won": agent.csat_stars >= win_csat,
        "break_room_used": desk.break_room_used,
    }


def turn_event_to_dict(
    turn: int,
    action: str,
    result: str,
    state_dict: dict,
) -> dict:
    """Wrap a turn event for WebSocket broadcast."""
    return {
        "type": "turn_update",
        "turn": turn,
        "action": action,
        "result": result,
        "state": state_dict,
    }
