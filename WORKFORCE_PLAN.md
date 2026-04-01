# Workforce Plan: The Hidden Layer — Micro Mission Web App

## Overview

Scope: **Micro Mission only** (3x3 grid, 3 dossiers, 30 turns, 2 NPCs, 1 robot).
Training (5x5) and Full (8x8) missions will be added later as separate work.

7 issues, 3 agents, 4 dependency tiers.

```
Tier 0 (no deps — start immediately, in parallel):
  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
  │ ISSUE-1      │  │ ISSUE-2      │  │ ISSUE-3      │
  │ Game State   │  │ CRT Theme    │  │ Project       │
  │ Serializer   │  │ CSS          │  │ Scaffold      │
  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
         │                 │                 │
Tier 1 (needs Tier 0):    │                 │
  ┌──────┴───────┐         │                 │
  │ ISSUE-4      │         │                 │
  │ Backend API  ├─────────┘                 │
  │ + WebSocket  │                           │
  └──────┬───────┘                           │
         │                                   │
Tier 2 (needs backend API contract):         │
  ┌──────┴───────┐  ┌───────────────┐        │
  │ ISSUE-5      │  │ ISSUE-6       │        │
  │ Game         │  │ Code Editor   │        │
  │ Renderer     │  │ + Auto Mode   │        │
  └──────┬───────┘  └──────┬────────┘        │
         │                 │                 │
Tier 3 (everything wired):                   │
  ┌──────┴─────────────────┴─────────────────┤
  │ ISSUE-7                                  │
  │ Integration, Polish & Manual Testing     │
  └──────────────────────────────────────────┘
```

---

## Micro Mission Reference

**Grid**: 3x3. **Start**: (2,0). **Goal**: 3 dossiers. **Turns**: 30. **Health**: 3.

```
    0         1         2
0   🌴(FT)    ·         📁
1   ·         🕵️Drop    ·
2   🟢Start   🕵️Vapnik  🤖Cryo
```

**Cells**:
- (0,0) Jungle — contains Flamethrower
- (0,1) Open
- (0,2) Cache — contains 1 dossier
- (1,0) Open
- (1,1) Informant — Agent Dropout
- (1,2) Open
- (2,0) Open — start position
- (2,1) Informant — Dr. Vapnik
- (2,2) Robot — Cryo-Sentinel (weakness: Flamethrower, +1 dossier)

**NPCs**:
- Dr. Vapnik (2,1): Gives USB Drive quest. Deliver to Dropout for +1 dossier.
- Agent Dropout (1,1): Receives USB Drive. Tells about Cryo-Sentinel weakness and Flamethrower location.

**Dossier sources**: Cache (1) + USB delivery (1) + Cryo-Sentinel kill (1) = 3 total.

**Key difference from full game**: MicroGameWorld subclasses GameWorld (ROWS=3, COLS=3). MicroGameTools subclasses GameTools with patched talk() that uses MICRO_NPC_CATALOG. The micro mission has its own MICRO_MISSION_BRIEFING and micro_stub_oracle.

---

## ISSUE-1: Game State Serialization Layer

**Labels**: `backend`, `tier-0`
**Depends on**: —
**Blocks**: ISSUE-4

### Description

Add JSON serialization to the existing game engine so game state can be sent over WebSocket. Pure Python — no web code. Must work for any grid size (3x3 micro or 8x8 full).

### Agent Prompt

```
You are working on "The Hidden Layer", an educational spy game. The game engine
lives in `agentic_ai_spy/hidden_layer/` with these key files:
- operative.py — Operative dataclass: health, dossiers, inventory, position,
  visited (set of tuples), journal (list of strings), MAX_HEALTH, WIN_DOSSIERS
- game_world.py — GameWorld: ROWS/COLS attributes, grid (list[list[Cell]]),
  CellType enum (.value, .emoji, .label), Cell dataclass (.cell_type, .items,
  .npc_id, .robot_name, .description, .npc property returns NPC or None),
  quest flags (usb_drive_picked_up, cryo_sentinel_alive, etc.)
- tools.py — GameTools with execute(tool_name, args) -> ToolResult(success, message)

The micro mission uses a 3x3 grid (MicroGameWorld with ROWS=3, COLS=3).
The full mission uses 8x8. Your code must work for ANY grid size by reading
world.ROWS and world.COLS.

Create a new file: `agentic_ai_spy/hidden_layer/serialization.py`

Implement these functions:

1. `cell_to_dict(cell, position, operative, world) -> dict`
   - Compute visibility: a cell is "visible" if its position is in
     operative.visited OR is adjacent (N/S/E/W) to any visited cell.
     Adjacent means within the grid bounds (0..world.ROWS-1, 0..world.COLS-1).
   - If visible:
     {
       "type": cell.cell_type.value,   # "jungle", "cache", "informant", etc.
       "emoji": cell.cell_type.emoji,
       "label": cell.cell_type.label,
       "description": cell.description,
       "has_items": bool(cell.items),
       "npc_name": cell.npc.name if cell.npc else None,
       "robot_name": cell.robot_name,
       "visible": True
     }
   - If NOT visible (fog of war):
     {
       "type": "unknown", "emoji": "░", "label": "", "description": "",
       "has_items": False, "npc_name": None, "robot_name": None,
       "visible": False
     }

2. `game_state_to_dict(operative, world, turn, max_turns) -> dict`
   {
     "turn": turn,
     "max_turns": max_turns,
     "position": [row, col],
     "health": operative.health,
     "max_health": operative.MAX_HEALTH,
     "dossiers": operative.dossiers,
     "win_dossiers": operative.WIN_DOSSIERS,
     "inventory": list(operative.inventory),
     "visited": [[r,c] for r,c in operative.visited],
     "journal": operative.journal[-5:],
     "grid": [[cell_to_dict(...) for each col] for each row],
     "is_alive": operative.is_alive,
     "has_won": operative.has_won,
     "cryo_alive": world.cryo_sentinel_alive,
     "evil_ai_alive": world.evil_ai_robot_alive,
     "rows": world.ROWS,
     "cols": world.COLS,
   }

3. `turn_event_to_dict(turn, action, result, scan, state_dict) -> dict`
   {
     "type": "turn_update",
     "turn": turn,
     "action": action,
     "result": result,
     "scan": scan,
     "state": state_dict
   }

Write tests in `tests/test_serialization.py`:
- Fresh micro game (position (2,0), 3 health, 0 dossiers, 3x3 grid)
- Fog of war: cell (0,2) should be redacted from start position (2,0)
- Cell (2,1) should be visible (adjacent to start)
- Journal truncated to last 5
- Grid dimensions match world.ROWS x world.COLS
```

### Acceptance Criteria
- [ ] `serialization.py` with all 3 functions
- [ ] Works for any grid size (reads world.ROWS/COLS)
- [ ] Fog of war redaction correct
- [ ] Tests pass

---

## ISSUE-2: CRT Terminal Theme (CSS)

**Labels**: `frontend`, `tier-0`
**Depends on**: —
**Blocks**: ISSUE-5, ISSUE-6, ISSUE-7

### Description

Extract the spy-themed CRT terminal CSS from `brochure.html` and `display.py` into a standalone stylesheet. The grid CSS must work for a 3x3 map (micro) — use CSS custom properties for grid dimensions.

### Agent Prompt

```
You are building a CRT-terminal-themed CSS stylesheet for "The Hidden Layer",
a spy game web app. The game starts with a 3x3 micro mission (may grow to 8x8
later). Design the grid to work at any size.

Two design sources exist in the repo:

1. `agentic_ai_spy/brochure.html` — styled marketing page:
   - CSS variables: --green (#00ff41), --amber (#ff8c00), --red (#ff2222),
     --bg (#020a03)
   - Scanline overlay (body::after with repeating-linear-gradient)
   - CRT vignette (body::before with radial-gradient)
   - Fonts: 'Press Start 2P' (headings), 'Share Tech Mono' (body)
   - Animations: flicker, blink, glowPulse

2. `agentic_ai_spy/hidden_layer/display.py` — game UI inline styles:
   - Tile backgrounds: OPEN=#2a3a2a, JUNGLE=#1a3a1a, WALL=#4a4a4a,
     CACHE=#2a3a2a, INFORMANT=#2a3a30, FORGE=#4a3a2a, LAB=#2a2a4a,
     SAFEHOUSE=#3a3a2a, ROBOT=#4a1a1a, HELICOPTER=#2a4a4a
   - Agent cell: border 2px solid #00ff41, box-shadow 0 0 8px #00ff41 inset
   - Fog cell: bg #0a0a0a, color #222
   - Visited open: bg #223322
   - Health hearts: green #00ff41, empty #333
   - Dossier bar: gradient #006600 → #00ff41, glow at 100%
   - Turn bar: green <60%, amber <80%, red >=80%
   - Result colors: green (success), red (damage), grey (neutral)
   - Panel bg: #0a1a0a, border: #1a3a1a

Create `web/static/style.css` with these sections:

1. **CSS Variables** — all colors, --cell-size: 56px (larger for 3x3),
   --grid-cols: 3 (JS will update via inline style for different missions)
2. **Base** — body, @import Google Fonts (Share Tech Mono + Press Start 2P)
3. **CRT Effects** — scanlines (body::after), vignette (body::before), flicker
4. **Layout** — CSS grid: game area (map+stats) | controls | editor | action log.
   Single column, stacking vertically. Max-width 700px, centered.
5. **Game Map** — .game-grid as CSS grid (grid-template-columns:
   repeat(var(--grid-cols), var(--cell-size))).
   .cell (base), .cell--open, .cell--jungle, .cell--wall, .cell--cache,
   .cell--informant, .cell--forge, .cell--lab, .cell--safehouse,
   .cell--robot, .cell--helicopter — each with correct bg color.
   .cell--agent (green glow border+shadow), .cell--fog (#0a0a0a),
   .cell--visited (#223322 for open cells).
   .cell--reveal (animation: fadeIn 300ms)
6. **Stats Panel** — .health-bar, .dossier-bar (inner div width transitions),
   .turn-bar, .inventory (.item-slot)
7. **Action Log** — .action-log (max-height 200px, overflow-y auto, scroll-snap),
   .log-entry, .result--success (green), .result--damage (red), .result--neutral
8. **Controls** — .dpad (CSS grid 3x3 of 56px buttons), .btn (base with
   hover glow), .btn--primary, .btn--success, .btn--warning, .btn--danger,
   .input-field (dark bg, green text, green border on focus), .controls-row
9. **Code Editor** — .editor-panel (collapsible via .editor-panel--collapsed),
   .prompt-textarea, .code-textarea (both monospace, dark bg, green text,
   min-height 100px), .editor-header (shows function signature, non-editable look)
10. **Game Over** — .game-over-overlay (fixed, centered, backdrop blur),
    .game-over--victory (green glow), .game-over--defeat (red glow),
    .game-over--timeout (amber glow)
11. **Responsive** — below 600px: reduce cell size to 48px, font sizes down
12. **Animations** — @keyframes fadeIn, bar transitions (width 0.5s ease),
    .spinner (rotating dots for "LLM thinking...")

Cell size 56px for the 3x3 grid makes the map ~168px wide — pair with stats
panel on the right for a ~450px game area. Font sizes: 11-16px.
All buttons: hover glow effect (box-shadow 0 0 6px var(--green)).

Do NOT create any HTML or JS files — only the CSS.
```

### Acceptance Criteria
- [ ] `web/static/style.css` exists with all 12 sections
- [ ] CSS variables for all colors + --cell-size + --grid-cols
- [ ] CRT scanline + vignette effects
- [ ] Grid works for 3x3 (and will work for larger via --grid-cols)
- [ ] Cell type classes match CellType.value names
- [ ] Responsive breakpoint at 600px

---

## ISSUE-3: Project Scaffold & File Structure

**Labels**: `infra`, `tier-0`
**Depends on**: —
**Blocks**: ISSUE-4

### Description

Create the web app directory structure, requirements.txt, HTML skeleton, and copy assets. Also extract the micro mission world code from the notebook into a proper Python module.

### Agent Prompt

```
Set up the web app project for "The Hidden Layer" micro mission.

1. Create directory structure:
   web/
   ├── server.py              # placeholder: `# TODO: implement`
   ├── requirements.txt
   ├── static/
   │   ├── index.html         # HTML skeleton
   │   ├── style.css          # placeholder: `/* TODO */`
   │   ├── game.js            # placeholder: `// TODO`
   │   └── assets/            # copy from agentic_ai_spy/assets/

2. requirements.txt:
   fastapi>=0.115
   uvicorn[standard]>=0.30
   websockets>=12.0
   google-genai>=1.0

3. Extract micro mission code into a proper module.
   Create: `agentic_ai_spy/hidden_layer/micro_mission.py`

   This file should contain the code currently defined inline in the notebook
   `the_hidden_layer_micro_mission.ipynb` (Cell 2). Specifically:
   - MICRO_NPC_CATALOG dict (2 NPCs: dr_vapnik, dropout)
   - micro_stub_oracle() function
   - MicroGameWorld class (subclass of GameWorld, ROWS=3, COLS=3)
   - MicroGameTools class (subclass of GameTools, patched talk())
   - MICRO_MISSION_BRIEFING string
   - create_micro_game() function → returns (operative, world, tools)
   - play_micro_mission() function

   Import from existing modules:
     from hidden_layer.game_world import CellType, Cell, NPC, GameWorld
     from hidden_layer.operative import Operative
     from hidden_layer.tools import GameTools, ToolResult
     etc.

   NOTE: Remove the NPC portrait HTML embedding (_npc_portrait_html) from
   MicroGameTools — the web app handles portraits in the frontend.
   The patched talk() should still use MICRO_NPC_CATALOG for NPC lookups
   and handle USB Drive give/receive logic, but return plain text results
   (no HTML tags).

4. index.html skeleton — valid HTML5:
   - <title>THE HIDDEN LAYER — Micro Mission</title>
   - Meta viewport
   - Link to style.css
   - Google Fonts preconnect + link (Share Tech Mono, Press Start 2P)
   - Sections with IDs:
     #game-area, #game-map, #stats-panel, #health-bar, #dossier-bar,
     #turn-bar, #inventory, #scan-panel, #action-log,
     #controls-area, #editor-area, #game-over-overlay
   - Title bar: "🕵️ THE HIDDEN LAYER — MICRO MISSION" + [Manual] [Auto] [Reset]
   - Script tag: <script src="game.js" defer></script>
   - Footer: "BMAI FS26 — ETH Zürich"

5. Copy agentic_ai_spy/assets/* into web/static/assets/

6. In server.py placeholder, add a comment:
   # Add parent dir to path so hidden_layer is importable
   # import sys; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

This is scaffolding only — no game logic in server.py, no rendering in game.js.
```

### Acceptance Criteria
- [ ] Directory structure created
- [ ] `requirements.txt` with correct packages
- [ ] `micro_mission.py` extracted and importable
- [ ] `index.html` has all section IDs
- [ ] Assets copied
- [ ] Placeholder files exist

---

## ISSUE-4: Backend API & WebSocket Server

**Labels**: `backend`, `tier-1`
**Depends on**: ISSUE-1 (serialization), ISSUE-3 (scaffold + micro_mission.py)
**Blocks**: ISSUE-5, ISSUE-6, ISSUE-7

### Description

Implement the FastAPI server for the micro mission. Only the micro mission — no mission selection UI needed.

### Agent Prompt

```
You are implementing the backend for "The Hidden Layer" micro mission web app.

AVAILABLE CODE (import and use, do NOT modify):
- hidden_layer.operative: Operative
- hidden_layer.tools: GameTools, ToolResult
- hidden_layer.oracle: llm_oracle
- hidden_layer.agent: MISSION_BRIEFING, TOOLS_DESCRIPTION, parse_tool_call
- hidden_layer.serialization: game_state_to_dict, turn_event_to_dict
- hidden_layer.micro_mission: (MicroGameWorld, MicroGameTools,
  MICRO_NPC_CATALOG, micro_stub_oracle, MICRO_MISSION_BRIEFING,
  create_micro_game)

Write: `web/server.py`

The micro mission specifics:
- 3x3 grid, start (2,0), 3 dossiers to win, 30 turns max
- 2 NPCs (Dr. Vapnik, Agent Dropout) using MICRO_NPC_CATALOG
- 1 robot (Cryo-Sentinel, killed by Flamethrower)
- MicroGameTools has patched talk() for micro NPCs
- create_micro_game() returns (operative, world, tools) ready to play
- micro_stub_oracle is the fallback when no Gemini API key is set

REQUIREMENTS:

1. **Path setup**: At top of file:
   import sys, os
   sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agentic_ai_spy"))

2. **Session management**:
   - In-memory dict: sessions: dict[str, GameSession]
   - @dataclass GameSession: operative, world, tools, turn (int), history (list),
     max_turns (int), auto_running (bool), auto_task (asyncio.Task | None),
     last_active (float)
   - Session created via create_micro_game()
   - tools.set_oracle(micro_stub_oracle) by default,
     or tools.set_oracle(lambda npc, q, o: llm_oracle(npc, q, o, gemini_client))
     if GEMINI_API_KEY is set
   - Cleanup sessions inactive > 1 hour (background task on startup)

3. **REST endpoints**:
   - POST /api/game/new → creates session, returns:
     {"session_id": str, "state": game_state_to_dict(op, world, 0, 30),
      "mission_briefing": MICRO_MISSION_BRIEFING}
   - GET /api/game/{session_id} → current state

4. **WebSocket** /ws/game/{session_id}:

   Client → Server:

   a) {"type": "manual_action", "tool": "move", "args": {"direction": "north"}}
      Execute:
      - If session.auto_running, reject with error.
      - Auto-scan: scan_result = tools.execute("scan", {}).message
      - Execute tool: result = tools.execute(tool, args)
      - Increment session.turn
      - Build state dict, send turn_event_to_dict(...)
      - Check win/lose/timeout → send game_over if triggered
      - Append to session.history (observation, action, result)

   b) {"type": "start_auto", "system_prompt": "...", "think_code": "..."}
      - Compile think_code into think_llm function:
        code = "def think_llm(operative, world, history, client):\n"
        code += textwrap.indent(think_code, "    ")
        namespace = {"MISSION_BRIEFING": MICRO_MISSION_BRIEFING,
                     "TOOLS_DESCRIPTION": TOOLS_DESCRIPTION}
        exec(code, namespace)
        think_fn = namespace["think_llm"]
      - Create asyncio task that runs the agent loop:
        For each turn until game over or stopped:
          1. scan
          2. Build history entry (prepend MICRO_MISSION_BRIEFING on turn 0)
          3. Call think_fn(operative, world, history, gemini_client)
          4. parse_tool_call → execute tool
          5. Send turn_update via WebSocket
          6. await asyncio.sleep(0.8) for animation
          7. Check end conditions
        On completion: send game_over
      - Send {"type": "auto_started"}
      - If no GEMINI_API_KEY and think_code references "client":
        send error "No Gemini API key configured"

   c) {"type": "stop_auto"}
      Cancel auto_task, send {"type": "auto_stopped", "reason": "user"}

   d) {"type": "reset"}
      Reinitialize session with create_micro_game(), reset turn/history,
      send initial state as turn_update with turn 0.

   Server → Client message types:
   - turn_update (from turn_event_to_dict)
   - game_over: {"type":"game_over","won":bool,"reason":str,
     "stats":{"turns":N,"dossiers":N,"health":N,"visited":N}}
   - error: {"type":"error","message":str}
   - auto_started: {"type":"auto_started"}
   - auto_stopped: {"type":"auto_stopped","reason":str}

5. **Static files**: Mount web/static at / with html=True.

6. **Gemini client**: Read GEMINI_API_KEY from env. If set, create
   genai.Client(). If not, log warning, use stub oracle, and reject
   auto mode LLM calls with a clear error message.

7. **Error handling**: Wrap all exec() and think_fn calls in try/except.
   Send {"type":"error","message":str(e)} on failure. Never crash session.

8. **CORS**: Allow all origins.

9. **Main block**: if __name__ == "__main__": uvicorn.run("server:app",
   host="0.0.0.0", port=8000, reload=True)

Write the complete server.py file.
```

### Acceptance Criteria
- [ ] POST /api/game/new returns valid micro game state (3x3 grid)
- [ ] WebSocket manual_action works for move/talk/collect
- [ ] start_auto compiles think_code and streams turns
- [ ] stop_auto cancels the loop
- [ ] reset reinitializes to fresh micro game
- [ ] Static files served
- [ ] Works without GEMINI_API_KEY (stub oracle, clear error on auto)
- [ ] Graceful error handling for bad think_code

---

## ISSUE-5: Frontend Game Renderer

**Labels**: `frontend`, `tier-2`
**Depends on**: ISSUE-2 (CSS classes), ISSUE-4 (JSON shapes)
**Blocks**: ISSUE-7

### Description

JavaScript that renders the 3x3 game map, stats panels, and action log from game state JSON.

### Agent Prompt

```
You are implementing the game renderer for "The Hidden Layer" micro mission
web app. The CSS classes are defined in style.css (ISSUE-2). The backend sends
game state JSON over WebSocket (ISSUE-4).

Write the RENDERING section of `web/static/game.js`.

GAME STATE JSON (from server, for the micro mission):
{
  "type": "turn_update",
  "turn": 3,
  "action": "move(direction=\"north\")",
  "result": "Moved north to (1,0).",
  "scan": "You are at (1,0). North: Jungle. East: Informant...",
  "state": {
    "turn": 3,
    "max_turns": 30,
    "position": [1, 0],
    "health": 3,
    "max_health": 3,
    "dossiers": 0,
    "win_dossiers": 3,
    "inventory": [],
    "visited": [[2,0],[2,1],[1,0]],
    "journal": [],
    "grid": [
      [{"type":"jungle","emoji":"🌴","visible":true,...}, {"type":"open","emoji":"·","visible":true,...}, {"type":"unknown","emoji":"░","visible":false,...}],
      [{"type":"open","emoji":"·","visible":true,...}, {"type":"informant","emoji":"🕵️","visible":true,"npc_name":"Agent Dropout",...}, {"type":"unknown","emoji":"░","visible":false,...}],
      [{"type":"open","emoji":"·","visible":true,...}, {"type":"informant","emoji":"🕵️","visible":true,"npc_name":"Dr. Vapnik",...}, {"type":"unknown","emoji":"░","visible":false,...}]
    ],
    "is_alive": true,
    "has_won": false,
    "cryo_alive": true,
    "evil_ai_alive": false,
    "rows": 3,
    "cols": 3
  }
}

Implement these functions:

1. `renderGrid(state)` — Build/update a grid in #game-map.
   - Read state.rows and state.cols to determine grid size.
   - Set CSS custom property --grid-cols on the grid element.
   - Each cell is a <div> with class "cell cell--{type}".
   - If cell.visible is false: class "cell cell--fog", textContent "░"
   - If cell position matches state.position: add "cell--agent", show "🕴️"
   - Otherwise show cell.emoji
   - Track previously visible cells; newly revealed ones get "cell--reveal"
     class (removed after 300ms via setTimeout).

2. `renderHealth(state)` — Update #health-bar.
   Green hearts "❤️" × health + grey "🖤" × (max_health - health).

3. `renderDossierBar(state)` — Update #dossier-bar.
   Progress bar inner div: width = (dossiers/win_dossiers*100)%.
   Add .dossier-bar--complete class when dossiers >= win_dossiers.
   Show text "N/M" next to bar.

4. `renderTurnBar(state)` — Update #turn-bar.
   Progress bar. Color class: .turn-bar--ok (<60%), .turn-bar--warn (<80%),
   .turn-bar--danger (>=80%). Text: "Turn N/M".

5. `renderInventory(state)` — Update #inventory.
   Item icon map: {"USB Drive":"💾", "Flamethrower":"🔥", "Scrap Metal":"⚙️",
     "Microfilm":"📷", "Fuel Canister":"⛽", "Hard Drive":"💿",
     "Medical Supplies":"🩹", "Virus Code":"💻", "Computer Virus":"🐛",
     "Radio Codebook":"📗"}
   Each item: <span class="item-slot">{icon} {name}</span>.
   Empty: show italic "Empty".

6. `renderActionLog(action, result)` — Append to #action-log.
   Action icons: move→"🧭", talk→"💬", collect→"✋", fabricate→"🔧".
   Result color class: .result--success if contains
   "dossier|collected|delivered|built|destroy|reward|mission complete",
   .result--damage if "damage|hurt|fail|cannot|retreat|tripwire|neutralized",
   .result--neutral otherwise.
   Max 20 entries (remove oldest). Auto-scroll to bottom.

7. `renderScan(scanText)` — Update #scan-panel textContent.

8. `renderGameOver(data)` — Show #game-over-overlay.
   data.won → .game-over--victory, !data.won && reason has "fallen" →
   .game-over--defeat, else .game-over--timeout.
   Show stats: turns, dossiers, health, visited count.
   "Play Again" button that triggers reset.

9. `updateUI(message)` — Dispatcher:
   - "turn_update": renderGrid, renderHealth, renderDossierBar, renderTurnBar,
     renderInventory, renderActionLog, renderScan
   - "game_over": renderGameOver
   - "error": append error to action log with .result--damage styling

Use DOM manipulation only (createElement, classList, textContent) — NO innerHTML.
Use the CSS classes from style.css.

Expose: window.GameRenderer = { updateUI, renderGameOver }
At the END of the file, leave a comment: // CONTROLS module follows (ISSUE-6)
```

### Acceptance Criteria
- [ ] 3x3 grid renders with correct cell types and fog of war
- [ ] Agent position highlighted
- [ ] Health, dossiers, turn bars update correctly for 3/3/30 limits
- [ ] Inventory shows icons
- [ ] Action log scrolls, max 20, color-coded
- [ ] Game over overlay with all 3 variants
- [ ] Grid size driven by state.rows/cols (not hardcoded)
- [ ] No innerHTML (XSS safe)

---

## ISSUE-6: Code Editor Panel & Auto/Manual Controls

**Labels**: `frontend`, `tier-2`
**Depends on**: ISSUE-2 (CSS), ISSUE-4 (WebSocket protocol)
**Blocks**: ISSUE-7

### Description

WebSocket client, manual controls (d-pad, talk, collect), code editor textareas, and auto/manual mode switching.

### Agent Prompt

```
You are implementing the controls and WebSocket client for "The Hidden Layer"
micro mission web app.

Append to `web/static/game.js` (after the renderer from ISSUE-5).
The renderer exposes window.GameRenderer.updateUI(message).

Implement:

1. **WebSocket client**:
   - connectGame(sessionId): connect to ws://{location.host}/ws/game/{sessionId}
   - On message: JSON.parse, call GameRenderer.updateUI(msg)
     Also: if msg.type === "auto_started", set autoRunning = true, updateControlState()
     If msg.type === "auto_stopped", set autoRunning = false, updateControlState()
     If msg.type === "game_over", set gameOver = true, updateControlState()
   - On close: show "Disconnected" in action log
   - sendMessage(obj): ws.send(JSON.stringify(obj))
   - sendAction(tool, args): sendMessage({type:"manual_action", tool, args})
   - startAuto(systemPrompt, thinkCode):
     sendMessage({type:"start_auto", system_prompt: systemPrompt, think_code: thinkCode})
   - stopAuto(): sendMessage({type:"stop_auto"})
   - resetGame(): sendMessage({type:"reset"}); clear action log; gameOver=false

2. **Manual controls** (in #controls-area):
   - D-pad: buttons #dpad-north, #dpad-south, #dpad-east, #dpad-west
     → sendAction("move", {direction: "..."})
   - Keyboard: ArrowUp/W=north, ArrowDown/S=south, ArrowLeft/A=west,
     ArrowRight/D=east. Only when no textarea is focused.
   - #btn-collect → sendAction("collect", {})
   - #talk-input (text) + #talk-send (button) → sendAction("talk", {message: val})
     Enter key in input also submits. Clear input after send.
   - #fabricate-input + #fabricate-send → sendAction("fabricate", {item: val})
     Enter submits. Clear after send.
     NOTE: Micro mission has no forge, but keep the UI for forward compatibility.

3. **Code editor** (#editor-area):
   - #system-prompt <textarea>: placeholder = example micro mission prompt:
     "You are a spy on a 3x3 grid. Collect 3 dossiers in 30 turns.\n\n
     Tools:\n  TOOL: move(direction=\"north|south|east|west\")\n
     TOOL: talk(message=\"hello\")\n  TOOL: collect()\n\n
     Respond with exactly one TOOL: line."
   - Read-only header showing: def think_llm(operative, world, history, client):
   - #think-code <textarea>: placeholder = example think function body:
     "transcript = []\nfor h in history[-20:]:\n    if h[\"role\"] == \"observation\":\n        transcript.append(f\"SCAN: {h['content']}\")\n    elif h[\"role\"] == \"action\":\n        transcript.append(f\"ACTION: {h['content']}\")\n    elif h[\"role\"] == \"result\":\n        transcript.append(f\"RESULT: {h['content']}\")\n\nuser_msg = \"\\n\".join(transcript) + \"\\n\\nWhat do you do next?\"\n\nresponse = client.models.generate_content(\n    model=\"gemini-2.5-flash\",\n    contents=user_msg,\n    config=genai.types.GenerateContentConfig(\n        system_instruction=SYSTEM_PROMPT,\n        max_output_tokens=200,\n    ),\n)\nreturn response.text"
   - Tab key in both textareas: prevent default, insert 4 spaces.
   - On input: save to localStorage("spy_system_prompt") and
     localStorage("spy_think_code").
   - On load: restore from localStorage if present.

4. **Mode switching**:
   - State: let mode = "manual", autoRunning = false, gameOver = false
   - #btn-manual: set mode="manual", show controls, collapse editor
   - #btn-auto: set mode="auto", show editor, show #btn-run/#btn-stop
   - #btn-run: reads textareas, calls startAuto(). Only enabled when
     mode==="auto" && !autoRunning && !gameOver
   - #btn-stop: calls stopAuto(). Only enabled when autoRunning.
   - #btn-reset: calls resetGame().
   - updateControlState(): disable d-pad/collect/talk/fabricate when
     autoRunning or gameOver. Toggle button visibility/enabled states.

5. **Initialization** (DOMContentLoaded):
   - fetch("/api/game/new", {method:"POST"}).then(r => r.json())
   - Store sessionId. Call connectGame(sessionId).
   - Render initial state via GameRenderer.updateUI({type:"turn_update",
     turn:0, action:"", result: resp.mission_briefing, scan:"",
     state: resp.state})
   - Restore editor content from localStorage.

Expose: window.GameControls = { connectGame, sendAction, startAuto, stopAuto }
```

### Acceptance Criteria
- [ ] WebSocket connects and receives updates
- [ ] D-pad + WASD/arrow keys work (not when in textarea)
- [ ] Talk and fabricate inputs submit on Enter
- [ ] Tab inserts spaces in textareas
- [ ] Mode toggle manual ↔ auto
- [ ] Run/Stop control auto mode
- [ ] localStorage persistence for editor content
- [ ] Controls disabled during auto/game over

---

## ISSUE-7: Integration, HTML Assembly & Polish

**Labels**: `integration`, `tier-3`
**Depends on**: ISSUE-2, ISSUE-4, ISSUE-5, ISSUE-6
**Blocks**: —

### Description

Wire all pieces into the final index.html, test end-to-end, and polish.

### Agent Prompt

```
Final integration for "The Hidden Layer" micro mission web app.

All pieces exist:
- web/server.py (ISSUE-4) — FastAPI backend for micro mission
- web/static/style.css (ISSUE-2) — CRT theme
- web/static/game.js (ISSUE-5 + ISSUE-6) — renderer + controls

Your job:

1. **Finalize index.html** with the actual HTML structure:

   ┌─────────────────────────────────────────────────┐
   │ 🕵️ THE HIDDEN LAYER — MICRO  [Manual][Auto][Reset]│
   ├───────────────────┬─────────────────────────────┤
   │                   │ Turn ████░░ 3/30            │
   │  #game-map        │ Health ❤️❤️❤️                │
   │  (3×3 grid)       │ Dossiers ░░░░░░ 0/3        │
   │                   │ Inventory: Empty            │
   │                   │ ────────────────            │
   │                   │ 📡 Scan result...           │
   ├────────┬──────────┴─────────────────────────────┤
   │  D-pad │ Talk: [________________] [💬 Send]     │
   │ ↑←·→   │ Fabricate: [__________] [🔧 Build]    │
   │  ↓     │                                       │
   │[✋Collect]│ [▶ Run Agent] [⏹ Stop]             │
   ├────────┴────────────────────────────────────────┤
   │ 📝 AGENT CODE                       [▼ collapse]│
   │ System Prompt:                                  │
   │ ┌──────────────────────────────────────────────┐│
   │ │ <textarea id="system-prompt">                ││
   │ └──────────────────────────────────────────────┘│
   │ def think_llm(operative, world, history, client):│
   │ ┌──────────────────────────────────────────────┐│
   │ │ <textarea id="think-code">                   ││
   │ └──────────────────────────────────────────────┘│
   ├─────────────────────────────────────────────────┤
   │ Action Log (scrollable)                         │
   │ > Mission briefing...                           │
   └─────────────────────────────────────────────────┘
   ┌─────────────────────────────────────────────────┐
   │ (hidden) #game-over-overlay                     │
   └─────────────────────────────────────────────────┘

   Required element IDs (game.js expects these):
   #game-map, #stats-panel, #health-bar, #dossier-bar, #turn-bar,
   #inventory, #scan-panel, #action-log, #controls-area,
   #system-prompt, #think-code, #editor-area,
   #btn-run, #btn-stop, #btn-manual, #btn-auto, #btn-reset,
   #btn-collect, #talk-input, #talk-send,
   #fabricate-input, #fabricate-send,
   #dpad-north, #dpad-south, #dpad-east, #dpad-west,
   #game-over-overlay

2. **Integration fixes** — read server.py, style.css, and game.js.
   Fix any mismatches in element IDs, CSS class names, or JSON field names.
   Make small targeted fixes in those files if needed (don't rewrite).

3. **Polish**:
   - Mission briefing panel: on first load, show a dismissible panel
     at the top of the action log with the micro mission objective:
     "Collect 3 dossiers. Talk to informants. Destroy the robot. 30 turns."
   - "LLM thinking..." spinner text in action log during auto mode turns
   - Smooth transitions on progress bars (CSS handles this)
   - Logical tab order: d-pad → collect → talk → fabricate → editor
   - NPC portrait images: when an NPC is in the current cell and the player
     talks to them, show their portrait (from /assets/) in the action log
     result. Use the mapping: dr_vapnik→dr_vapnik.jpg,
     dropout→agent_dropout.jpg, cryo_sentinel→cryo_sentinel.png

4. **README section**: Add to the project README.md:
   ## Web App (Micro Mission)
   ```
   cd web
   pip install -r requirements.txt
   export GEMINI_API_KEY=your-key   # optional: enables LLM-powered NPCs
   python server.py
   # Open http://localhost:8000
   ```
   Without GEMINI_API_KEY, manual mode works with keyword-matched NPC responses.
   Auto mode requires the API key for LLM calls.

Test end-to-end:
a) Page loads → 3x3 grid with fog of war
b) Move north → map updates
c) Talk to Vapnik → get USB Drive
d) Navigate to Dropout, deliver USB → +1 dossier
e) Collect cache → +1 dossier
f) Get Flamethrower, kill Cryo → +1 dossier → game over (victory)
g) Auto mode with example think code
h) Reset → fresh game
i) Refresh → editor content restored
```

### Acceptance Criteria
- [ ] index.html has all required element IDs
- [ ] 3x3 micro mission renders and plays correctly
- [ ] Manual mode: move, talk, collect all work
- [ ] Auto mode: streams turns, stoppable
- [ ] Game over overlay (victory when 3 dossiers collected)
- [ ] NPC portraits shown in action log
- [ ] Mission briefing on first load
- [ ] README updated

---

## Dependency Summary

| Issue | Title | Tier | Depends On | Blocks |
|-------|-------|------|------------|--------|
| 1 | Game State Serialization | 0 | — | 4 |
| 2 | CRT Terminal Theme CSS | 0 | — | 5, 6, 7 |
| 3 | Project Scaffold + micro_mission.py | 0 | — | 4 |
| 4 | Backend API + WebSocket | 1 | 1, 3 | 5, 6, 7 |
| 5 | Frontend Game Renderer | 2 | 2, 4 | 7 |
| 6 | Code Editor + Controls | 2 | 2, 4 | 7 |
| 7 | Integration & Polish | 3 | 2, 4, 5, 6 | — |

## Parallelism Schedule

```
Time →
Agent A: [ISSUE-1: Serialization] ──→ [ISSUE-4: Backend] ──→ [ISSUE-7: Integration]
Agent B: [ISSUE-2: CSS Theme]     ──→ [ISSUE-5: Renderer] ─↗
Agent C: [ISSUE-3: Scaffold]      ──→ [ISSUE-6: Controls] ─↗
```

3 agents, 4 tiers, maximum parallelism.

## Future Work (not in scope)

- ISSUE-8: Training mission (5x5) — add TrainingGameWorld, mission selector dropdown
- ISSUE-9: Full mission (8x8) — add full GameWorld, all 3 NPCs, 2 robots
- ISSUE-10: Debrief integration — port the notebook's debrief/coaching system to the web UI
- ISSUE-11: Leaderboard — track best runs across students (turns, dossiers, health)
