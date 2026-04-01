# Workforce Plan: The Hidden Layer Web App

## Overview

7 issues, 4 parallelism lanes, ~3 dependency tiers. Each issue is scoped so one agent can complete it independently given its inputs.

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

## ISSUE-1: Game State Serialization Layer

**Labels**: `backend`, `tier-0`
**Depends on**: nothing
**Blocked by**: nothing
**Blocks**: ISSUE-4

### Description

Add JSON serialization to the existing game engine so game state can be sent over WebSocket. This is a pure Python task — no web code.

### Agent Prompt

```
You are working on "The Hidden Layer", an educational spy game. The game engine
lives in `agentic_ai_spy/hidden_layer/` with these key files:
- operative.py (Operative dataclass — health, dossiers, inventory, position, visited, journal)
- game_world.py (GameWorld — 8x8 grid of Cell objects, CellType enum, NPC/item catalogs, quest flags)
- tools.py (GameTools — execute tool actions, return ToolResult)
- agent.py (run_agent loop, MISSION_BRIEFING, TOOLS_DESCRIPTION, parse_tool_call)

Create a new file: `agentic_ai_spy/hidden_layer/serialization.py`

Implement these functions:

1. `cell_to_dict(cell: Cell, position: tuple[int,int], operative: Operative) -> dict`
   Returns:
   {
     "type": cell.cell_type.value,       # e.g. "jungle", "cache", "informant"
     "emoji": cell.cell_type.emoji,
     "label": cell.cell_type.label,
     "description": cell.description,
     "has_items": bool(cell.items),       # don't leak item names
     "npc_name": cell.npc.name if cell.npc else None,
     "robot_name": cell.robot_name,
     "visible": True/False,              # based on operative.visited + adjacent
   }

2. `game_state_to_dict(operative: Operative, world: GameWorld, turn: int, max_turns: int) -> dict`
   Returns the full state needed by the frontend:
   {
     "turn": int,
     "max_turns": int,
     "position": [row, col],
     "health": int,
     "max_health": int,
     "dossiers": int,
     "win_dossiers": int,
     "inventory": [...],
     "visited": [[r,c], ...],
     "journal": [...],       # last 5 entries only
     "grid": [[cell_dict, ...], ...],   # 8x8 array
     "is_alive": bool,
     "has_won": bool,
     "cryo_alive": bool,
     "evil_ai_alive": bool,
   }

3. `turn_event_to_dict(turn: int, action: str, result: str, scan: str, state: dict) -> dict`
   Wraps a single turn's data for WebSocket:
   {
     "type": "turn_update",
     "turn": int,
     "action": str,
     "result": str,
     "scan": str,
     "state": state_dict,
   }

Visibility rule: a cell is "visible" if it's in operative.visited OR is
adjacent (N/S/E/W) to any visited cell. Unvisited, non-adjacent cells should
have type/emoji/description redacted (set to "unknown"/"░"/"").

Write unit tests in `tests/test_serialization.py` that verify:
- A fresh game serializes correctly (position 7,0; 3 health; 0 dossiers)
- Fog of war: cells far from start are redacted
- After moving north, newly visible cells appear
- Journal is truncated to last 5
```

### Acceptance Criteria
- [ ] `serialization.py` exists with all 3 functions
- [ ] All fields documented above are present in output
- [ ] Fog of war redaction works correctly
- [ ] Tests pass

---

## ISSUE-2: CRT Terminal Theme (CSS)

**Labels**: `frontend`, `tier-0`
**Depends on**: nothing
**Blocks**: ISSUE-5, ISSUE-6, ISSUE-7

### Description

Extract and expand the spy-themed CRT terminal CSS from `brochure.html` and `display.py` into a standalone stylesheet for the web app.

### Agent Prompt

```
You are building a CRT-terminal-themed CSS stylesheet for "The Hidden Layer",
a spy game web app. Two sources of design exist in the repo:

1. `agentic_ai_spy/brochure.html` — a styled marketing page with:
   - CSS variables: --green (#00ff41), --amber (#ff8c00), --red (#ff2222), --bg (#020a03)
   - Scanline overlay (body::after with repeating-linear-gradient)
   - CRT vignette (body::before with radial-gradient)
   - Fonts: 'Press Start 2P' (headings), 'Share Tech Mono' (body)
   - Animations: flicker, blink, glowPulse, stampAppear
   - Classified stamp styling

2. `agentic_ai_spy/hidden_layer/display.py` — game UI styles:
   - Tile colors: OPEN=#2a3a2a, JUNGLE=#1a3a1a, WALL=#4a4a4a, CACHE=#2a3a2a,
     INFORMANT=#2a3a30, FORGE=#4a3a2a, LAB=#2a2a4a, SAFEHOUSE=#3a3a2a,
     ROBOT=#4a1a1a, HELICOPTER=#2a4a4a
   - Agent highlight: border 2px solid #00ff41, box-shadow 0 0 8px #00ff41 inset
   - Fog-of-war unknown cell: bg #0a0a0a, color #222
   - Visited-but-empty: bg #223322
   - Health: green hearts (#00ff41), empty hearts (#333)
   - Dossier bar: gradient #006600 → #00ff41
   - Turn bar: green < 60%, amber < 80%, red >= 80%
   - Result colors: green (success), red (damage), grey (neutral)
   - Panel backgrounds: #0a1a0a with #1a3a1a borders

Create `web/static/style.css` with these sections:

1. **CSS Variables** — all colors, sizes as custom properties
2. **Base** — body, fonts (Google Fonts import for Share Tech Mono + Press Start 2P)
3. **CRT Effects** — scanlines, vignette, flicker animation
4. **Layout** — main 3-panel grid (map+stats | controls | code editor)
5. **Game Map** — .game-grid table, .cell, .cell--open, .cell--jungle, etc.,
   .cell--agent (highlight), .cell--fog (unknown), .cell--visited
6. **Stats Panel** — .health-bar, .dossier-bar, .turn-bar, .inventory
7. **Action Log** — .action-log, .result--success, .result--damage, .result--neutral
8. **Controls** — .dpad (CSS grid 3x3), .btn-primary, .btn-success, .btn-warning,
   .input-field, .talk-row, .fabricate-row
9. **Code Editor** — .editor-panel, .prompt-textarea, .code-textarea,
   .editor-header (fixed function signature display)
10. **Game Over** — .game-over-overlay with victory/defeat/timeout variants
11. **Responsive** — stack panels vertically below 900px width
12. **Animations** — smooth transitions for health/dossier bars, cell reveals

The stylesheet should be self-contained (no JS needed for styling).
Cell size: 48px × 48px. Max game panel width: 480px. Font sizes: 11-16px range.
All interactive elements should have hover/active states with glow effects.

Do NOT create any HTML or JS files — only the CSS.
```

### Acceptance Criteria
- [ ] `web/static/style.css` exists
- [ ] All 12 sections present
- [ ] CSS variables for every color
- [ ] CRT scanline + vignette effects
- [ ] Responsive layout breakpoint at 900px
- [ ] Cell type classes match game engine CellType values

---

## ISSUE-3: Project Scaffold & File Structure

**Labels**: `infra`, `tier-0`
**Depends on**: nothing
**Blocks**: ISSUE-4

### Description

Create the project directory structure, `requirements.txt`, `index.html` skeleton, and copy assets.

### Agent Prompt

```
Set up the web app project structure for "The Hidden Layer" spy game.

1. Create directory structure:
   web/
   ├── server.py          # placeholder: `# TODO: implement`
   ├── requirements.txt
   ├── static/
   │   ├── index.html     # HTML skeleton (no game logic yet)
   │   ├── style.css      # placeholder: `/* TODO: implement */`
   │   ├── game.js        # placeholder: `// TODO: implement`
   │   └── assets/        # copy from agentic_ai_spy/assets/

2. requirements.txt contents:
   fastapi>=0.115
   uvicorn[standard]>=0.30
   websockets>=12.0
   google-genai>=1.0

3. index.html skeleton — a valid HTML5 document with:
   - Title: "THE HIDDEN LAYER"
   - Meta viewport for mobile
   - Link to style.css
   - Google Fonts preconnect + link (Share Tech Mono, Press Start 2P)
   - Three main sections (empty divs with IDs):
     - #game-area (will hold map + stats + action log)
     - #controls-area (will hold d-pad, talk, fabricate, run/stop buttons)
     - #editor-area (will hold system prompt + code textareas)
   - Script tag loading game.js (defer)
   - A title bar div with "🕵️ THE HIDDEN LAYER" and mode toggle buttons
     [Manual] [Auto] [Reset]
   - Footer: "BMAI FS26 — ETH Zürich"

4. Copy all files from agentic_ai_spy/assets/ into web/static/assets/

5. Ensure the hidden_layer Python package is importable from web/server.py
   by adding a symlink or updating sys.path comment in server.py placeholder.

This is scaffolding only — no game logic, no WebSocket code, no rendering code.
```

### Acceptance Criteria
- [ ] Directory structure created
- [ ] `requirements.txt` with correct packages
- [ ] `index.html` has all section IDs and font links
- [ ] Assets copied
- [ ] Placeholder files exist for server.py, style.css, game.js

---

## ISSUE-4: Backend API & WebSocket Server

**Labels**: `backend`, `tier-1`
**Depends on**: ISSUE-1 (serialization), ISSUE-3 (scaffold)
**Blocks**: ISSUE-5, ISSUE-6, ISSUE-7

### Description

Implement the FastAPI server with REST + WebSocket endpoints that wrap the game engine.

### Agent Prompt

```
You are implementing the backend for "The Hidden Layer" web app.

AVAILABLE CODE (already exists — import and use, do NOT modify):
- hidden_layer.game_world: GameWorld, CellType, NPC_CATALOG, FACILITY_CATALOG
- hidden_layer.operative: Operative
- hidden_layer.tools: GameTools, ToolResult
- hidden_layer.oracle: stub_oracle, llm_oracle
- hidden_layer.agent: MISSION_BRIEFING, TOOLS_DESCRIPTION, parse_tool_call
- hidden_layer.serialization: game_state_to_dict, turn_event_to_dict

NEW CODE (you write):
- web/server.py: FastAPI application

REQUIREMENTS:

1. **Session management**:
   - In-memory dict: `sessions: dict[str, GameSession]`
   - GameSession dataclass holding: operative, world, tools, turn, history,
     max_turns, auto_running (bool), auto_task (asyncio.Task | None)
   - Session cleanup after 1 hour of inactivity (use a background task)

2. **REST endpoints**:
   - `POST /api/game/new` → creates session, returns:
     {"session_id": "...", "state": game_state_to_dict(...)}
   - `POST /api/game/new?mode=micro` → creates the 3x3 micro mission variant
   - `GET /api/game/{session_id}` → returns current state

3. **WebSocket endpoint** `GET /ws/game/{session_id}`:

   Client → Server messages:

   a) Manual action:
      {"type": "manual_action", "tool": "move", "args": {"direction": "north"}}
      Server executes the tool, sends back turn_update.

   b) Start auto mode:
      {"type": "start_auto", "system_prompt": "...", "think_code": "..."}
      Server compiles think_code into a callable via:
        namespace = {
            "MISSION_BRIEFING": MISSION_BRIEFING,
            "TOOLS_DESCRIPTION": TOOLS_DESCRIPTION,
        }
        exec(think_code_wrapped, namespace)
        think_fn = namespace["think_llm"]
      where think_code_wrapped prepends:
        "def think_llm(operative, world, history, client):\n"
        + indent(think_code, "    ")
      Then runs the agent loop asynchronously, sending turn_update after each turn
      with a 0.5s delay between turns (for animation).

   c) Stop auto mode:
      {"type": "stop_auto"}
      Cancels the running auto task.

   d) Reset game:
      {"type": "reset"}
      Reinitializes the session with a fresh game.

   Server → Client messages:

   a) turn_update: turn_event_to_dict(...)
   b) game_over:
      {"type": "game_over", "won": bool, "reason": str, "stats": {...}}
   c) error:
      {"type": "error", "message": str}
   d) auto_started: {"type": "auto_started"}
   e) auto_stopped: {"type": "auto_stopped", "reason": str}

4. **Static file serving**:
   Mount `web/static` at `/` using StaticFiles with html=True.

5. **Gemini client**:
   Initialize `genai.Client()` once at startup if GEMINI_API_KEY env var is set.
   If not set, use stub_oracle for NPC dialogue and return an error if auto mode
   tries to call the LLM.

6. **Auto-scan**: Each turn (manual or auto), execute tools.scan() first and
   include the scan result in the turn_update.

7. **Error handling**: Wrap think_code compilation and execution in try/except.
   Send {"type": "error", "message": "..."} on failure. Don't crash the session.

8. **CORS**: Allow all origins (workshop setting).

Write the complete server.py. Include a `if __name__ == "__main__"` block that
runs uvicorn on port 8000.
```

### Acceptance Criteria
- [ ] `POST /api/game/new` returns valid session + state JSON
- [ ] WebSocket accepts manual_action and returns turn_update
- [ ] WebSocket accepts start_auto with think_code, runs loop, streams updates
- [ ] stop_auto cancels the loop
- [ ] reset reinitializes the game
- [ ] Static files served at `/`
- [ ] Graceful error handling for bad think_code
- [ ] Works without GEMINI_API_KEY (falls back to stub_oracle)

---

## ISSUE-5: Frontend Game Renderer

**Labels**: `frontend`, `tier-2`
**Depends on**: ISSUE-2 (CSS), ISSUE-4 (backend API contract — specifically the JSON shapes)
**Blocks**: ISSUE-7

### Description

Implement the JavaScript game map renderer, stats panels, and action log. Consumes game state JSON from WebSocket and renders the UI.

### Agent Prompt

```
You are implementing the game renderer for "The Hidden Layer" web app.
The CSS classes are defined in style.css (ISSUE-2). The backend sends game state
JSON over WebSocket (ISSUE-4).

Create/update `web/static/game.js` — specifically the RENDERING module.

GAME STATE JSON shape (received from server):
{
  "type": "turn_update",
  "turn": 5,
  "action": "move(direction=\"north\")",
  "result": "Moved north to (6,0). Dense jungle...",
  "scan": "You are at (6,0). North: Jungle. East: Open...",
  "state": {
    "turn": 5,
    "max_turns": 100,
    "position": [6, 0],
    "health": 3,
    "max_health": 3,
    "dossiers": 1,
    "win_dossiers": 10,
    "inventory": ["USB Drive"],
    "visited": [[7,0],[7,1],[6,0]],
    "journal": ["Talked to Dr. Vapnik: ..."],
    "grid": [
      [{"type":"helicopter","emoji":"🚁","visible":false}, ...],  // row 0
      ...
    ],
    "is_alive": true,
    "has_won": false,
    "cryo_alive": true,
    "evil_ai_alive": true
  }
}

Implement these functions:

1. `renderGrid(state)` — Build/update an 8x8 HTML table in #game-map.
   - Each cell is a <td> with class "cell cell--{type}" (e.g. cell--jungle)
   - If cell.visible is false: class "cell cell--fog", show "░"
   - If cell position matches state.position: add class "cell--agent", show "🕴️"
   - Otherwise show cell.emoji
   - Visited cells that are OPEN type get class "cell--visited"
   - Animate newly revealed cells (add "cell--reveal" class, remove after 300ms)

2. `renderHealth(state)` — Update #health-bar with heart icons.
   Green hearts (❤️) for current health, grey hearts (🖤) for missing.

3. `renderDossierBar(state)` — Update #dossier-bar with a progress bar.
   Width = (dossiers / win_dossiers * 100)%. Glow effect at 100%.

4. `renderTurnBar(state)` — Update #turn-bar with progress + color.
   Green < 60%, amber < 80%, red >= 80%. Show "Turn X/Y".

5. `renderInventory(state)` — Update #inventory with item slots.
   Item icons map: USB Drive→💾, Microfilm→📷, Fuel Canister→⛽,
   Hard Drive→💿, Medical Supplies→🩹, Virus Code→💻,
   Flamethrower→🔥, Computer Virus→🐛, Scrap Metal→⚙️,
   Radio Codebook→📗, Field Rations→🥫, Med Kit→🩺

6. `renderActionLog(action, result)` — Append to #action-log (scrollable div).
   Show action with icon (🧭 move, 💬 talk, ✋ collect, 🔧 fabricate).
   Color result: green if contains success keywords, red if damage keywords,
   grey otherwise. Keep max 20 entries, auto-scroll to bottom.

7. `renderScan(scanText)` — Update #scan-panel with current scan text.

8. `renderGameOver(data)` — Show overlay with victory/defeat/timeout.
   data: {"type":"game_over", "won": bool, "reason": str,
          "stats": {"turns": N, "dossiers": N, "health": N, "visited": N}}

9. `updateUI(message)` — Master dispatcher. Calls the right render functions
   based on message.type ("turn_update", "game_over", "error").

All rendering should use DOM manipulation (createElement/classList/textContent),
not innerHTML, for security. Use the CSS classes from style.css — do NOT add
inline styles.

Export: window.GameRenderer = { renderGrid, updateUI, renderGameOver }
```

### Acceptance Criteria
- [ ] 8x8 grid renders correctly with fog of war
- [ ] Agent position highlighted with glow
- [ ] Health, dossiers, turn bars update dynamically
- [ ] Inventory shows correct icons
- [ ] Action log scrolls, color-codes results
- [ ] Game over overlay displays for all 3 outcomes
- [ ] No innerHTML usage (XSS safe)

---

## ISSUE-6: Code Editor Panel & Auto/Manual Mode Switching

**Labels**: `frontend`, `tier-2`
**Depends on**: ISSUE-2 (CSS), ISSUE-4 (backend WebSocket protocol)
**Blocks**: ISSUE-7

### Description

Implement the code editor UI (system prompt + think function body), manual control buttons, and the WebSocket client that ties everything together.

### Agent Prompt

```
You are implementing the interactive controls and WebSocket client for
"The Hidden Layer" web app.

Create/update `web/static/game.js` — specifically the CONTROLS + WEBSOCKET modules.
The renderer (ISSUE-5) provides window.GameRenderer.updateUI(message).

Implement:

1. **WebSocket client**:
   - `connectGame(sessionId)` — connect to ws://host/ws/game/{sessionId}
   - On message: parse JSON, call GameRenderer.updateUI(msg)
   - On close: show reconnect button
   - `sendAction(tool, args)` — send {"type":"manual_action","tool":...,"args":...}
   - `startAuto(systemPrompt, thinkCode)` — send {"type":"start_auto",...}
   - `stopAuto()` — send {"type":"stop_auto"}
   - `resetGame()` — send {"type":"reset"}

2. **Manual controls** (wired to #controls-area):
   - D-pad: 4 buttons (N/S/E/W) → sendAction("move", {direction: "north"}) etc.
   - Keyboard shortcuts: arrow keys or WASD for movement
   - Collect button → sendAction("collect", {})
   - Talk input + send button → sendAction("talk", {message: inputValue})
     Enter key submits talk.
   - Fabricate input + build button → sendAction("fabricate", {item: inputValue})
     Enter key submits fabricate.
   - Disable all controls during auto mode. Re-enable on stop.

3. **Code editor panel** (#editor-area):
   - System prompt: <textarea id="system-prompt"> with placeholder text showing
     a minimal example system prompt.
   - Think function: Display a read-only header line:
     "def think_llm(operative, world, history, client):"
     Below it: <textarea id="think-code"> where students write the function body.
     Placeholder shows a minimal working example:
       # Build context from game state
       status = operative.status_text()
       recent = history[-10:]
       ...
       response = client.models.generate_content(...)
       return response.text
   - Both textareas: monospace font, dark background, green text, tab key
     inserts 4 spaces (not focus change).

4. **Mode switching**:
   - Three buttons in title bar: [Manual] [Auto] [Reset]
   - Manual mode (default): controls visible, editor collapsed but expandable
   - Auto mode: click [Auto] → editor slides open, [▶ Run Agent] button appears
   - [▶ Run Agent]: reads textarea values, calls startAuto(). Button changes to
     [⏹ Stop]. Controls grey out.
   - [⏹ Stop]: calls stopAuto(). Controls re-enable.
   - [Reset]: calls resetGame(). Clears action log. Keeps editor content.

5. **Game initialization**:
   - On page load: POST /api/game/new, get session_id, call connectGame(),
     render initial state.
   - Store sessionId globally.

6. **Local storage persistence**:
   - Save system prompt + think code to localStorage on every edit.
   - Restore on page load (so students don't lose work on refresh).

Wire up all event listeners in a DOMContentLoaded handler.
Export: window.GameControls = { connectGame, sendAction, startAuto, stopAuto }
```

### Acceptance Criteria
- [ ] WebSocket connects and receives turn updates
- [ ] D-pad + keyboard shortcuts send correct actions
- [ ] Talk and fabricate inputs work with Enter key
- [ ] Code editor has working tab-to-spaces
- [ ] Mode toggle works (manual ↔ auto)
- [ ] Run/Stop buttons control auto mode
- [ ] Editor content persists across refresh (localStorage)
- [ ] Controls disabled during auto mode

---

## ISSUE-7: Integration, HTML Assembly & Polish

**Labels**: `integration`, `tier-3`
**Depends on**: ISSUE-2, ISSUE-4, ISSUE-5, ISSUE-6
**Blocks**: nothing

### Description

Wire all pieces together into the final `index.html`, fix integration issues, and polish the experience.

### Agent Prompt

```
You are doing final integration for "The Hidden Layer" web app.

All pieces exist:
- web/server.py (ISSUE-4) — FastAPI backend
- web/static/style.css (ISSUE-2) — CRT theme
- web/static/game.js (ISSUE-5 + ISSUE-6) — renderer + controls + WebSocket

Your job:

1. **Assemble index.html** — Update the skeleton from ISSUE-3 with the actual
   HTML structure. The layout should match this wireframe:

   ┌─────────────────────────────────────────────────┐
   │ 🕵️ THE HIDDEN LAYER    [Manual] [Auto] [Reset]  │
   ├────────────────────┬────────────────────────────┤
   │                    │ Turn ████░░░░ 12/100       │
   │  #game-map         │ Health ❤️❤️❤️               │
   │  (8x8 table)       │ Dossiers ████░░ 3/10      │
   │                    │ Inventory [💾] [⛽]         │
   │                    │ ─────────────────────      │
   │                    │ 📡 Scan: North: Wall...    │
   ├────────┬───────────┴────────────────────────────┤
   │  D-pad │ Talk: [__________] [💬]                │
   │ ↑←↓→   │ Fabricate: [______] [🔧]              │
   │[Collect]│ [▶ Run Agent] [⏹ Stop]               │
   ├────────┴────────────────────────────────────────┤
   │ 📝 AGENT CODE                        [collapse] │
   │ System Prompt:                                  │
   │ ┌──────────────────────────────────────────────┐│
   │ │ textarea                                     ││
   │ └──────────────────────────────────────────────┘│
   │ def think_llm(operative, world, history, client):│
   │ ┌──────────────────────────────────────────────┐│
   │ │ textarea                                     ││
   │ └──────────────────────────────────────────────┘│
   ├─────────────────────────────────────────────────┤
   │ Action Log (scrollable, last 20 turns)          │
   └─────────────────────────────────────────────────┘

   All elements must have the IDs expected by game.js:
   #game-map, #health-bar, #dossier-bar, #turn-bar, #inventory,
   #scan-panel, #action-log, #controls-area, #system-prompt,
   #think-code, #editor-area, #btn-run, #btn-stop, #btn-manual,
   #btn-auto, #btn-reset, #btn-collect, #talk-input, #talk-send,
   #fabricate-input, #fabricate-send, #dpad-north, #dpad-south,
   #dpad-east, #dpad-west, #game-over-overlay

2. **Integration testing** — Verify these flows work end-to-end:
   a) Page loads → game created → map renders with fog of war
   b) Click North → agent moves → map updates → action log shows result
   c) Click into an informant cell → type in talk input → send → see NPC response
   d) Switch to Auto → paste think code → Run Agent → turns stream in
   e) Stop → controls re-enable
   f) Reset → fresh game
   g) Game over (let agent die or win) → overlay appears
   h) Refresh page → editor content restored from localStorage

3. **Polish**:
   - Add a brief "Mission Briefing" modal/panel that shows on first load
     (dismissible), explaining the game objective in 3 bullets
   - Add "LLM thinking..." spinner during auto mode turns
   - Smooth CSS transitions on bar updates (health, dossiers, turns)
   - Ensure tab order is logical (d-pad → collect → talk → fabricate → editor)
   - Test in Chrome and Firefox

4. **README update** — Add a "Web App" section to the project README:
   ```
   ## Web App
   cd web
   pip install -r requirements.txt
   export GEMINI_API_KEY=your-key   # optional: enables LLM NPCs
   python server.py
   # Open http://localhost:8000
   ```

Do NOT modify server.py, style.css, or the core game.js logic —
only assemble index.html and make minor CSS/JS tweaks for integration.
```

### Acceptance Criteria
- [ ] index.html has all required element IDs
- [ ] Page loads and renders initial game state
- [ ] Manual mode works (move, talk, collect, fabricate)
- [ ] Auto mode works (run, stream turns, stop)
- [ ] Reset works
- [ ] Game over overlay displays
- [ ] Mission briefing shows on first visit
- [ ] README updated with web app instructions

---

## Dependency Summary Table

| Issue | Title | Tier | Depends On | Blocks |
|-------|-------|------|------------|--------|
| 1 | Game State Serialization | 0 | — | 4 |
| 2 | CRT Terminal Theme CSS | 0 | — | 5, 6, 7 |
| 3 | Project Scaffold | 0 | — | 4 |
| 4 | Backend API + WebSocket | 1 | 1, 3 | 5, 6, 7 |
| 5 | Frontend Game Renderer | 2 | 2, 4 | 7 |
| 6 | Code Editor + Auto Mode | 2 | 2, 4 | 7 |
| 7 | Integration & Polish | 3 | 2, 4, 5, 6 | — |

## Parallelism Schedule

```
Time →
Agent A: [ISSUE-1: Serialization] → [ISSUE-4: Backend] → [ISSUE-7: Integration]
Agent B: [ISSUE-2: CSS Theme]     → [ISSUE-5: Renderer] ──↗
Agent C: [ISSUE-3: Scaffold]      → [ISSUE-6: Editor]  ──↗
```

**3 agents, 4 tiers, maximum parallelism.** Tier 0 issues can all start Day 1.
ISSUE-4 gates the frontend work but can start as soon as ISSUE-1 + ISSUE-3 finish.
ISSUE-5 and ISSUE-6 are fully independent of each other. ISSUE-7 is the final merge.
