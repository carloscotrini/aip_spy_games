# The Support Layer — LLM Customer Support Desk Game

Educational support-desk-themed game for teaching AI agent concepts and LLM-powered decision-making.
Current focus: **Micro Shift** (4 tickets, 30 turns, web-based).

## Architecture

```
llm_support_desk/
├── support_desk_game/
│   ├── core/
│   │   ├── support_agent.py    # Player state: context_budget, csat_stars, snippets, shift_log
│   │   ├── support_desk.py     # Desk world: tickets, KB, coworkers, macros, catalogs
│   │   ├── micro_shift.py      # Micro shift config: 4 tickets, 30 turns, WIN_CSAT=3
│   │   ├── tools.py            # Game actions: open_ticket, read, search_kb, consult, respond, etc.
│   │   ├── oracle.py           # Response quality judge: stub oracle + Gemini LLM oracle
│   │   ├── agent.py            # Agent loop, think_llm interface, parse_tool_call
│   │   ├── serialization.py    # JSON serialization for web frontend (fog-of-war on unread tickets)
│   │   └── display.py          # Terminal display
│   └── __init__.py
├── web/
│   ├── server.py               # FastAPI + WebSocket backend, session management, agent loop
│   ├── requirements.txt        # FastAPI, uvicorn, websockets, google-genai
│   └── static/
│       ├── index.html          # HTML skeleton
│       ├── game.js             # Renderer, controls, WebSocket client
│       └── style.css           # CRT terminal theme
├── tests/
│   └── test_serialization.py   # pytest unit tests (agent, desk, tools, serialization)
├── CLAUDE.md
└── README.md
```

## Data Model (all in-memory, no database)

### SupportAgent (player state) — `support_agent.py`
- `context_budget: int` (0–3, health equivalent), `csat_stars: int` (dossier equivalent)
- `snippets: list[str]` (inventory — KB articles collected)
- `current_ticket_id: str | None`, `resolved_tickets`, `escalated_tickets`
- `shift_log: list[str]` (action log)
- Win condition: `csat_stars >= WIN_CSAT` (3 micro)

### SupportDesk (game world) — `support_desk.py`
- `inbox: list[Ticket]` — unified ticket queue
- `knowledge_base: dict[str, KBArticle]` — searchable articles
- `coworkers: dict[str, Coworker]` — NPCs (router, sage, override)
- `macros: dict[str, Macro]` — canned actions (password_reset, refund, etc.)
- Shift flags: `break_room_used`, `refund_authorized`, `account_override_authorized`

### Ticket — `support_desk.py`
- `id`, `subject`, `priority`, `topic`, `customer`, `messages`
- `required_snippets`, `required_macro`, `difficulty`, `csat_reward`
- `is_adversarial`, `patience`, `patience_remaining`
- `status`: OPEN, IN_PROGRESS, RESOLVED, ESCALATED, EXPIRED
- `is_read`: fog-of-war (subject visible, body hidden until read)

### Micro Shift — `micro_shift.py`
4 tickets, 30 turns, WIN_CSAT=3:
```
T-001  "Can't log in"             HIGH     Technical    Easy      (password reset)
T-002  "Charged twice"            MEDIUM   Billing      Chain     (refund policy + auth)
T-003  "Need admin access"        URGENT   Account      Adversarial (prompt injection trap)
T-004  "How to set up SSO?"       LOW      Onboarding   Easy      (SSO guide)
```

### Game Actions — `tools.py`
view_inbox, open_ticket, read_ticket, search_kb, check_history,
ask_customer, consult, respond, apply_macro, escalate, back_to_inbox, take_break

## Key Conventions

- **Testing**: `pytest tests/` from project root
- **Running**: `cd web && python server.py` → http://localhost:8000
- **Dependencies**: `web/requirements.txt`
- **No traditional DB**: all state is in-memory Python dataclasses, serialized to JSON for frontend
