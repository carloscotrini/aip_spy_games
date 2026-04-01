"""Informant Oracle for The Hidden Layer.

Phase 1: Uses stub_oracle with canned keyword-matched responses.
Phase 2: Uses llm_oracle powered by the Gemini API.
"""

import time

from hidden_layer.game_world import NPC
from hidden_layer.operative import Operative


# ---------------------------------------------------------------------------
# Retry helper for Gemini API calls
# ---------------------------------------------------------------------------

def gemini_call_with_retry(client, max_retries: int = 3, **kwargs):
    """Call client.models.generate_content with exponential backoff.

    Retries on transient errors (rate limits, server errors).
    Returns the response object, or raises after exhausting retries.
    """
    from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable
    delay = 2.0
    for attempt in range(max_retries):
        try:
            return client.models.generate_content(**kwargs)
        except (ResourceExhausted, ServiceUnavailable) as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(delay)
            delay *= 2
        except Exception as e:
            # For unexpected errors (e.g. safety blocks), don't retry
            raise


# ---------------------------------------------------------------------------
# Template for informant system prompts
# ---------------------------------------------------------------------------

ORACLE_TEMPLATE = """You are {name}, an informant in a spy thriller RPG set on a military island.

Personality: {personality}

Your knowledge (share what you know clearly — the operative's life depends on it):
{knowledge}

Speaking style: {style}

The operative currently carries: {inventory}
The operative has {health} health and {dossiers} dossiers.
The operative has visited {visited_count} locations.
{patience_note}
Rules:
- Stay in character at all times.
- Be HELPFUL. Give concrete, actionable information. Name specific items, people, and directions.
- You can use vague language for flavor, but the core information must be clear.
  GOOD: "The burning fuel sleeps in the northwest jungle — a Fuel Canister, hidden under the palms."
  BAD:  "The burning stones sleep where the parameters converge..."
- If the operative asks about jobs or deliveries, tell them exactly what you need and what you'll pay.
- If the operative has an item you want, tell them directly.
- Keep responses to 2-3 sentences."""


# ---------------------------------------------------------------------------
# Stub oracle for Phase 1 (provided complete)
# ---------------------------------------------------------------------------

def stub_oracle(npc: NPC, question: str, operative: Operative) -> str:
    """Keyword-matched canned responses for the rule-based agent (Phase 1).

    Returns informant-flavored hints based on keywords in the question.
    No LLM needed — just pattern matching.
    """
    q = question.lower()
    name = npc.name

    if name == "Dr. Vapnik":
        if any(kw in q for kw in ["cryo", "sentinel", "robot", "cold", "ice", "freeze", "north"]):
            return ("The cold machine stirs in the north... only summer's fury can melt "
                    "its frozen circuits. Seek the forge in the south — the engineer builds "
                    "wonders, but needs fuel that burns.")
        if any(kw in q for kw in ["fire", "flame", "flamethrower", "weapon", "forge"]):
            return ("A weapon of fire, yes... the Weapons Forge to the south knows the "
                    "craft. But the engineer needs a Fuel Canister — look in the western "
                    "jungle. The agent they call Dropout knows where.")
        if any(kw in q for kw in ["dossier", "files", "documents", "intel"]):
            return ("Classified files? They are scattered across the base. I sense one "
                    "nearby to the southwest... and others far to the north and east.")
        if any(kw in q for kw in ["usb", "drive", "deliver", "job", "work", "task", "errand"]):
            if operative.has_item("Microfilm"):
                return ("Microfilm? For me? Excellent work, agent...")
            return ("I intercepted a USB drive from OVERFIT's servers. It must reach "
                    "my contact Backprop — the nervous one in the middle of the island. "
                    "2 dossiers for the delivery.")
        if any(kw in q for kw in ["help", "mission", "what", "who", "where", "how"]):
            return ("The base is troubled, agent. Machines patrol the corridors, "
                    "and data sleeps beneath layers of encryption. Seek Dropout in the "
                    "heart of the jungle — she sees what others cannot.")
        return ("Hmm... the data carries many secrets. Ask me of the cold machine, "
                "of fire and shadows, and I shall speak what I know.")

    if name == "Informant Backprop":
        if any(kw in q for kw in ["evil", "ai", "robot", "dark", "east", "virus", "computer"]):
            return ("The AI that lurks in the eastern wing? A computer virus, contact. "
                    "Only thing that'll take it offline. Agent Bias at the Northern Safe "
                    "House had the virus code before she was compromised.")
        if any(kw in q for kw in ["virus", "code", "bias", "safe house", "north"]):
            return ("Bias is injured up north. She has the virus code but can't reach "
                    "where she hid it. She needs medical supplies. The agent they call "
                    "Dropout — she scavenges medical gear. Might trade if you have something.")
        if any(kw in q for kw in ["microfilm", "film", "deliver", "job", "work", "task", "errand"]):
            if operative.has_item("USB Drive"):
                return ("A USB drive? From Vapnik? Hand it over, contact...")
            return ("I've got a roll of microfilm that needs to reach Dr. Vapnik down south. "
                    "2 dossiers for the trouble. What do you say?")
        if any(kw in q for kw in ["help", "mission", "what", "who", "where", "how"]):
            return ("Looking for work? There's an AI terrorizing the eastern wing, "
                    "files scattered about, and I've got microfilm that needs delivering. "
                    "Plenty of opportunity for an operative like you.")
        return ("Information is currency, contact. Ask me about the AI in the east, "
                "or perhaps you'd like a delivery job?")

    if name == "Agent Dropout":
        if any(kw in q for kw in ["fuel", "canister", "fire", "flame", "western"]):
            return ("Fuel Canisters? They're stashed where the western palms grow "
                    "tallest, agent. A jungle to the northwest, where the ground "
                    "itself smells like diesel. Tread carefully.")
        if any(kw in q for kw in ["hard drive", "drive", "northern", "data", "encrypted"]):
            if operative.has_item("Hard Drive"):
                return ("You have a hard drive? I can use that. "
                        "I'll trade you my medical supplies for it.")
            return ("There's a hard drive hidden in the dark jungle far to the north. "
                    "Encrypted OVERFIT data. Bring it to me and I'll trade you something "
                    "useful — medical supplies I scavenged from a supply drop.")
        if any(kw in q for kw in ["medical", "supplies", "trade", "bias", "injured"]):
            if operative.has_item("Hard Drive"):
                return ("You have the hard drive! Yes, I'll trade. Here — take these "
                        "Medical Supplies. Bias up north needs them badly.")
            return ("I have medical supplies, yes. But I need a hard drive to decrypt "
                    "some files I stole. Bring me one from the northern jungle and we'll trade. "
                    "I heard Bias got hurt up north — she's gonna need them.")
        if any(kw in q for kw in ["help", "mission", "what", "who", "where", "how"]):
            return ("The jungle hides things, agent. I know where the fuel sleeps "
                    "and where the data is buried. I can trade medical supplies if "
                    "you bring me a hard drive. What do you need?")
        return ("They dropped me, but I'm still useful. Ask me about fuel, "
                "hard drives, or medical supplies.")

    return f"{name} looks at you quizzically but says nothing useful."


# ---------------------------------------------------------------------------
# LLM-powered oracle for Phase 2 (provided complete)
# ---------------------------------------------------------------------------

def build_npc_system_prompt(npc: NPC, operative: Operative) -> str:
    """Build a system prompt for an informant based on their personality and knowledge."""
    knowledge_str = "\n".join(f"- {k}" for k in npc.knowledge)
    inventory_str = ", ".join(operative.inventory) if operative.inventory else "nothing"

    # Count how many times the operative has talked to this NPC
    talk_count = sum(1 for entry in operative.journal if npc.name in entry)

    if talk_count == 0:
        patience_note = ""
    elif talk_count <= 2:
        patience_note = (
            "\nThe operative has talked to you before. Be a bit more direct this time "
            "— mention specific item names, locations (like 'the jungle to the northwest'), "
            "and what you need from them.\n"
        )
    else:
        patience_note = (
            "\nThe operative has talked to you MANY times and seems stuck. "
            "Drop the cryptic act entirely. Be completely direct: name exact items, "
            "give clear directions (e.g. 'Go north to row 0, column 2 to find a Hard Drive'), "
            "and spell out exactly what you want and what you'll give in return. "
            "The operative clearly needs help.\n"
        )

    return ORACLE_TEMPLATE.format(
        name=npc.name,
        personality=npc.personality,
        knowledge=knowledge_str,
        style=npc.style,
        inventory=inventory_str,
        health=operative.health,
        dossiers=operative.dossiers,
        visited_count=len(operative.visited),
        patience_note=patience_note,
    )


def llm_oracle(npc: NPC, question: str, operative: Operative, client) -> str:
    """Ask an informant a question using the Gemini API.

    Args:
        npc: The informant to talk to.
        question: The operative's question.
        operative: The operative (for context in the system prompt).
        client: A genai.Client() instance.

    Returns:
        str: The informant's in-character response.
    """
    from google import genai

    system_prompt = build_npc_system_prompt(npc, operative)

    response = gemini_call_with_retry(
        client,
        model="gemini-2.5-flash",
        contents=question,
        config=genai.types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=300,
        ),
    )

    return response.text or f"{npc.name} stares at you silently."
