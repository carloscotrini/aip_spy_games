# The Hidden Layer — Agentic AI Spy Game

Educational spy-themed game for teaching AI agents and LLM-powered decision-making (BMAI FS26 at ETH Zurich).
Current focus: **Micro Mission** (3x3 grid, web-based).

## Architecture

```
aip_spy_games/
├── agentic_ai_spy/
│   ├── hidden_layer/           # Core game engine (pure Python, no DB)
│   │   ├── operative.py        # Player state: health, dossiers, inventory, position, visited, journal
│   │   ├── game_world.py       # World grid, cells, NPCs, items, quest flags, CellType enum
│   │   ├── micro_mission.py    # Micro mission config: 3x3 grid, MicroGameWorld, MicroGameTools
│   │   ├── tools.py            # Game actions: move, talk, collect, fabricate
│   │   ├── oracle.py           # NPC dialogue: stub oracle + Gemini LLM oracle
│   │   ├── agent.py            # Agent loop, think_llm interface, parse_tool_call
│   │   ├── serialization.py    # JSON serialization for web frontend (fog-of-war)
│   │   ├── display.py          # Terminal display
│   │   └── interactive.py, main.py
│   ├── *.ipynb                 # Jupyter notebooks (micro/training/full missions)
│   └── assets/                 # NPC portraits
├── web/
│   ├── server.py               # FastAPI + WebSocket backend, session management, agent loop
│   ├── requirements.txt        # FastAPI, uvicorn, websockets, google-genai
│   └── static/
│       ├── index.html          # HTML skeleton
│       ├── game.js             # Renderer, controls, WebSocket client, localStorage
│       ├── style.css           # CRT terminal theme
│       └── assets/             # NPC portraits
├── tests/
│   └── test_serialization.py   # pytest unit tests
├── WORKFORCE_PLAN.md           # 7-issue development spec with dependency tiers
└── README.md
```

## Data Model (all in-memory, no database)

### Operative (player state) — `operative.py`
- `health: int` (0–3), `dossiers: int`, `inventory: list[str]`
- `position: tuple[int, int]`, `visited: set[tuple[int, int]]`
- `journal: list[str]` (action log)
- Win condition: `dossiers >= WIN_DOSSIERS` (10 full, 3 micro)

### GameWorld — `game_world.py`
- `grid: list[list[Cell]]` — each Cell has: `cell_type` (CellType enum), `items`, `npc_id`, `robot_name`, `trap`, `description`
- CellType enum: OPEN, JUNGLE, WALL, CACHE, INFORMANT, FORGE, LAB, SAFEHOUSE, ROBOT, HELICOPTER
- Quest flags: `usb_drive_picked_up/delivered`, `microfilm_picked_up/delivered`, `codebook_picked_up/delivered`, `hard_drive_traded`, `medical_supplies_delivered`, `virus_code_received`, `cryo_sentinel_alive`, `evil_ai_robot_alive`
- NPC_CATALOG: `dr_vapnik`, `backprop`, `dropout` — each with personality, knowledge, style, greeting
- ITEM_CATALOG: quest items (USB Drive, Microfilm, Fuel Canister, etc.) + weapons (Flamethrower, Computer Virus)

### MicroGameWorld — `micro_mission.py`
3x3 grid, 30 turns, WIN_DOSSIERS=3, start at (2,0):
```
    0           1           2
0   Jungle(FT)  Open        Cache(dossier)
1   Open        Dropout     Open
2   Start       Vapnik      Cryo-Sentinel
```
Dossier sources: cache(0,2) +1, USB delivery quest +1, Cryo kill +1 = 3

### Serialization — `serialization.py`
`game_state_to_dict()` returns: turn, position, health, dossiers, inventory, visited, journal (last 5), grid (with fog-of-war), is_alive, has_won, cryo_alive, evil_ai_alive, rows, cols.

## Web Server — `web/server.py`

- FastAPI app with WebSocket for real-time game updates
- In-memory `sessions` dict storing `GameSession` dataclass per session
- `GameSession`: operative, world (MicroGameWorld), tools, turn counter, history, gemini_client
- Manual mode: REST-like commands via WebSocket (move, talk, collect, fabricate)
- Auto mode: receives `system_prompt` + `think_code` from frontend, runs agent loop (scan → think_llm → parse → execute → broadcast)
- Gemini API: key from env `GEMINI_API_KEY` or provided via UI; stub oracle fallback if no key

## Key Conventions

- **Branching**: `vk/{issue-number}-{short-description}` off `main`
- **Testing**: `pytest tests/` from project root
- **Running**: `cd web && python server.py` → http://localhost:8000
- **Dependencies**: `web/requirements.txt` (FastAPI, uvicorn, websockets, google-genai)
- **No traditional DB**: all state is in-memory Python dataclasses, serialized to JSON for the frontend
