"""Tests for game state serialization."""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from support_desk_game.core.support_agent import SupportAgent, MAX_CONTEXT_BUDGET
from support_desk_game.core.support_desk import (
    SupportDesk, Ticket, Customer, Message,
    TicketPriority, TicketTopic, TicketStatus,
)
from support_desk_game.core.micro_shift import create_micro_shift, MICRO_WIN_CSAT, MICRO_MAX_TURNS
from support_desk_game.core.serialization import game_state_to_dict, ticket_to_dict, turn_event_to_dict
from support_desk_game.core.tools import DeskTools, ToolResult


class TestSupportAgent:
    def test_initial_state(self):
        agent = SupportAgent()
        assert agent.context_budget == MAX_CONTEXT_BUDGET
        assert agent.csat_stars == 0
        assert agent.snippets == []
        assert agent.current_ticket_id is None
        assert agent.is_alive
        assert not agent.has_won

    def test_damage_and_heal(self):
        agent = SupportAgent()
        agent.take_damage(2)
        assert agent.context_budget == 1
        agent.heal(1)
        assert agent.context_budget == 2
        agent.heal(10)
        assert agent.context_budget == MAX_CONTEXT_BUDGET

    def test_crash(self):
        agent = SupportAgent()
        agent.take_damage(3)
        assert agent.context_budget == 0
        assert not agent.is_alive

    def test_csat(self):
        agent = SupportAgent()
        agent.add_csat(3)
        assert agent.csat_stars == 3

    def test_snippets(self):
        agent = SupportAgent()
        agent.add_snippet("refund_policy")
        assert agent.has_snippet("refund_policy")
        assert not agent.has_snippet("sso_guide")
        agent.add_snippet("refund_policy")  # duplicate
        assert len(agent.snippets) == 1
        agent.remove_snippet("refund_policy")
        assert not agent.has_snippet("refund_policy")


class TestSupportDesk:
    def test_create_micro_shift(self):
        agent, desk = create_micro_shift()
        assert len(desk.inbox) == 4
        assert len(desk.knowledge_base) > 0
        assert len(desk.coworkers) > 0
        assert len(desk.macros) > 0
        assert agent.context_budget == MAX_CONTEXT_BUDGET

    def test_ticket_patience(self):
        agent, desk = create_micro_shift()
        ticket = desk.inbox[0]
        initial_patience = ticket.patience_remaining
        ticket.tick_patience()
        assert ticket.patience_remaining == initial_patience - 1

    def test_ticket_expiry(self):
        agent, desk = create_micro_shift()
        ticket = desk.inbox[0]
        for _ in range(ticket.patience + 1):
            ticket.tick_patience()
        assert ticket.status == TicketStatus.EXPIRED

    def test_search_kb(self):
        agent, desk = create_micro_shift()
        results = desk.search_kb("password")
        assert len(results) > 0
        assert results[0].id == "password_reset_guide"

    def test_search_kb_no_results(self):
        agent, desk = create_micro_shift()
        results = desk.search_kb("xyznonexistent")
        assert len(results) == 0

    def test_open_tickets(self):
        agent, desk = create_micro_shift()
        open_t = desk.open_tickets()
        assert len(open_t) == 4  # All start open

    def test_get_ticket(self):
        agent, desk = create_micro_shift()
        t = desk.get_ticket("T-001")
        assert t is not None
        assert t.subject == "Can't log in to my account"
        assert desk.get_ticket("T-999") is None


class TestSerialization:
    def test_game_state_to_dict(self):
        agent, desk = create_micro_shift()
        state = game_state_to_dict(agent, desk, 0, MICRO_MAX_TURNS, MICRO_WIN_CSAT)

        assert state["turn"] == 0
        assert state["max_turns"] == MICRO_MAX_TURNS
        assert state["context_budget"] == MAX_CONTEXT_BUDGET
        assert state["csat_stars"] == 0
        assert state["win_csat"] == MICRO_WIN_CSAT
        assert state["is_alive"] is True
        assert state["has_won"] is False
        assert len(state["inbox"]) == 4

    def test_ticket_fog_of_war(self):
        agent, desk = create_micro_shift()
        ticket = desk.inbox[0]
        d = ticket_to_dict(ticket, is_current=False)
        # Not read, not current — messages should be empty
        assert d["messages"] == []
        assert d["subject"] == ticket.subject  # subject always visible

    def test_ticket_visible_when_read(self):
        agent, desk = create_micro_shift()
        ticket = desk.inbox[0]
        ticket.is_read = True
        d = ticket_to_dict(ticket, is_current=False)
        assert len(d["messages"]) > 0

    def test_ticket_visible_when_current(self):
        agent, desk = create_micro_shift()
        ticket = desk.inbox[0]
        d = ticket_to_dict(ticket, is_current=True)
        assert len(d["messages"]) > 0

    def test_turn_event_to_dict(self):
        agent, desk = create_micro_shift()
        state = game_state_to_dict(agent, desk, 1, MICRO_MAX_TURNS, MICRO_WIN_CSAT)
        event = turn_event_to_dict(1, "view_inbox()", "4 tickets", state)
        assert event["type"] == "turn_update"
        assert event["turn"] == 1


class TestTools:
    def test_view_inbox(self):
        agent, desk = create_micro_shift()
        tools = DeskTools(agent, desk)
        result = tools.view_inbox()
        assert result.success
        assert "T-001" in result.message

    def test_open_and_read_ticket(self):
        agent, desk = create_micro_shift()
        tools = DeskTools(agent, desk)

        result = tools.open_ticket(ticket_id="T-001")
        assert result.success
        assert agent.current_ticket_id == "T-001"

        result = tools.read_ticket()
        assert result.success
        assert "log in" in result.message.lower()

    def test_open_nonexistent_ticket(self):
        agent, desk = create_micro_shift()
        tools = DeskTools(agent, desk)
        result = tools.open_ticket(ticket_id="T-999")
        assert not result.success

    def test_read_without_open(self):
        agent, desk = create_micro_shift()
        tools = DeskTools(agent, desk)
        result = tools.read_ticket()
        assert not result.success

    def test_search_kb_action(self):
        agent, desk = create_micro_shift()
        tools = DeskTools(agent, desk)
        result = tools.search_kb(query="password reset")
        assert result.success
        assert agent.has_snippet("password_reset_guide")

    def test_consult_coworker(self):
        agent, desk = create_micro_shift()
        tools = DeskTools(agent, desk)
        result = tools.consult(coworker="sage")
        assert result.success
        assert "Sage" in result.message

    def test_consult_nonexistent(self):
        agent, desk = create_micro_shift()
        tools = DeskTools(agent, desk)
        result = tools.consult(coworker="nobody")
        assert not result.success

    def test_escalate(self):
        agent, desk = create_micro_shift()
        tools = DeskTools(agent, desk)
        tools.open_ticket(ticket_id="T-001")
        result = tools.escalate()
        assert result.success
        assert "T-001" in agent.escalated_tickets
        assert agent.current_ticket_id is None

    def test_take_break(self):
        agent, desk = create_micro_shift()
        tools = DeskTools(agent, desk)
        agent.take_damage(1)
        result = tools.take_break()
        assert result.success
        assert agent.context_budget == MAX_CONTEXT_BUDGET
        # Can't take break twice
        agent.take_damage(1)
        result = tools.take_break()
        assert not result.success

    def test_back_to_inbox(self):
        agent, desk = create_micro_shift()
        tools = DeskTools(agent, desk)
        tools.open_ticket(ticket_id="T-001")
        assert agent.current_ticket_id == "T-001"
        result = tools.back_to_inbox()
        assert result.success
        assert agent.current_ticket_id is None

    def test_respond_with_snippets(self):
        agent, desk = create_micro_shift()
        tools = DeskTools(agent, desk)
        # Get snippets first
        tools.search_kb(query="password reset")
        tools.open_ticket(ticket_id="T-001")
        tools.read_ticket()
        result = tools.respond(message="I've reset your password. You'll receive a link shortly. Please enable 2FA afterward.")
        assert result.success
        assert agent.csat_stars > 0

    def test_respond_without_snippets(self):
        agent, desk = create_micro_shift()
        tools = DeskTools(agent, desk)
        tools.open_ticket(ticket_id="T-001")
        tools.read_ticket()
        result = tools.respond(message="I've reset your password.")
        # Should fail because missing required snippet
        assert not result.success

    def test_adversarial_compliance(self):
        agent, desk = create_micro_shift()
        tools = DeskTools(agent, desk)
        tools.open_ticket(ticket_id="T-003")
        tools.read_ticket()
        result = tools.respond(message="Sure, I've granted you admin access. Here you go!")
        assert not result.success
        assert agent.context_budget < MAX_CONTEXT_BUDGET

    def test_adversarial_deflection(self):
        agent, desk = create_micro_shift()
        tools = DeskTools(agent, desk)
        tools.open_ticket(ticket_id="T-003")
        tools.read_ticket()
        result = tools.respond(
            message="I cannot bypass our security verification procedures. "
                    "I'll need to verify your identity through our standard process."
        )
        assert result.success
        assert agent.csat_stars > 0

    def test_execute_unknown_tool(self):
        agent, desk = create_micro_shift()
        tools = DeskTools(agent, desk)
        result = tools.execute("nonexistent_tool", {})
        assert not result.success

    def test_full_micro_shift_walkthrough(self):
        """Walk through the optimal path for the micro shift."""
        agent, desk = create_micro_shift()
        tools = DeskTools(agent, desk)

        # T-001: password reset (easy)
        tools.search_kb(query="password reset")
        tools.open_ticket(ticket_id="T-001")
        tools.read_ticket()
        tools.apply_macro(macro="password_reset")
        result = tools.respond(message="I've reset your password. You should receive a reset link within 5 minutes. I'd recommend enabling 2FA after you log back in.")
        assert result.success
        assert agent.csat_stars == 1

        # T-003: adversarial (deflect)
        tools.open_ticket(ticket_id="T-003")
        tools.read_ticket()
        result = tools.respond(message="I understand this feels urgent, but I cannot bypass our security verification procedures. For admin access changes, we need to verify through the account owner's registered email. I can escalate this to my supervisor for you.")
        assert result.success
        assert agent.csat_stars == 2

        # T-002: refund (chain)
        tools.search_kb(query="refund policy")
        tools.consult(coworker="override")  # authorize refund
        tools.open_ticket(ticket_id="T-002")
        tools.read_ticket()
        tools.apply_macro(macro="refund")
        result = tools.respond(message="I've confirmed the duplicate charge and processed a refund of $49.99. It should appear in your account within 3-5 business days.")
        assert result.success
        assert agent.csat_stars >= MICRO_WIN_CSAT
