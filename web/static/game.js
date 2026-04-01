// ==========================================================================
// RENDERER module (ISSUE-5)
// ==========================================================================

const GameRenderer = (function () {
  // Track previously visible cells for reveal animation
  let prevVisible = new Set();

  const ITEM_ICONS = {
    "USB Drive": "\uD83D\uDCBE",
    "Flamethrower": "\uD83D\uDD25",
    "Scrap Metal": "\u2699\uFE0F",
    "Microfilm": "\uD83D\uDCF7",
    "Fuel Canister": "\u26FD",
    "Hard Drive": "\uD83D\uDCBF",
    "Medical Supplies": "\uD83E\uDE79",
    "Virus Code": "\uD83D\uDCBB",
    "Computer Virus": "\uD83D\uDC1B",
    "Radio Codebook": "\uD83D\uDCD7",
  };

  const ACTION_ICONS = {
    move: "\uD83E\uDDED",
    talk: "\uD83D\uDCAC",
    collect: "\u270B",
    fabricate: "\uD83D\uDD27",
    scan: "\uD83D\uDCE1",
  };

  const SUCCESS_RE = /dossier|collected|delivered|built|destroy|reward|mission complete/i;
  const DAMAGE_RE = /damage|hurt|fail|cannot|retreat|tripwire|neutralized/i;

  function renderGrid(state) {
    const map = document.getElementById("game-map");
    if (!map) return;

    map.style.setProperty("--grid-cols", state.cols);
    map.innerHTML = "";

    const nowVisible = new Set();

    for (let r = 0; r < state.rows; r++) {
      for (let c = 0; c < state.cols; c++) {
        const cell = state.grid[r][c];
        const div = document.createElement("div");
        const key = r + "," + c;

        if (!cell.visible) {
          div.className = "cell cell--fog";
          div.textContent = "\u2591";
        } else {
          nowVisible.add(key);
          const isAgent = state.position[0] === r && state.position[1] === c;
          div.className = "cell cell--" + cell.type;
          if (isAgent) {
            div.classList.add("cell--agent");
            div.textContent = "\uD83D\uDD74\uFE0F";
          } else {
            div.textContent = cell.emoji;
          }
          // Reveal animation for newly visible cells
          if (!prevVisible.has(key)) {
            div.classList.add("cell--reveal");
            setTimeout(() => div.classList.remove("cell--reveal"), 300);
          }
        }

        map.appendChild(div);
      }
    }

    prevVisible = nowVisible;
  }

  function renderHealth(state) {
    const bar = document.getElementById("health-bar");
    if (!bar) return;
    bar.textContent = "";
    for (let i = 0; i < state.max_health; i++) {
      const span = document.createElement("span");
      span.textContent = i < state.health ? "\u2764\uFE0F" : "\uD83D\uDDA4";
      bar.appendChild(span);
    }
  }

  function renderDossierBar(state) {
    const bar = document.getElementById("dossier-bar");
    if (!bar) return;
    const fill = bar.querySelector(".bar-fill");
    const text = bar.querySelector(".bar-text");
    const pct = state.win_dossiers > 0 ? (state.dossiers / state.win_dossiers) * 100 : 0;
    if (fill) fill.style.width = Math.min(pct, 100) + "%";
    if (text) text.textContent = state.dossiers + "/" + state.win_dossiers;
    bar.classList.toggle("dossier-bar--complete", state.dossiers >= state.win_dossiers);
  }

  function renderTurnBar(state) {
    const bar = document.getElementById("turn-bar");
    if (!bar) return;
    const fill = bar.querySelector(".bar-fill");
    const text = bar.querySelector(".bar-text");
    const pct = state.max_turns > 0 ? (state.turn / state.max_turns) * 100 : 0;
    if (fill) fill.style.width = Math.min(pct, 100) + "%";
    if (text) text.textContent = "Turn " + state.turn + "/" + state.max_turns;
    bar.classList.remove("turn-bar--ok", "turn-bar--warn", "turn-bar--danger");
    if (pct >= 80) bar.classList.add("turn-bar--danger");
    else if (pct >= 60) bar.classList.add("turn-bar--warn");
    else bar.classList.add("turn-bar--ok");
  }

  function renderInventory(state) {
    const container = document.getElementById("inventory");
    if (!container) return;
    const items = container.querySelector(".inventory-items");
    if (!items) return;
    items.textContent = "";
    if (!state.inventory || state.inventory.length === 0) {
      const empty = document.createElement("span");
      empty.style.fontStyle = "italic";
      empty.textContent = "Empty";
      items.appendChild(empty);
      return;
    }
    for (const name of state.inventory) {
      const slot = document.createElement("span");
      slot.className = "item-slot";
      const icon = ITEM_ICONS[name] || "\uD83D\uDCE6";
      slot.textContent = icon + " " + name;
      items.appendChild(slot);
    }
  }

  function renderActionLog(action, result) {
    const log = document.getElementById("action-log");
    if (!log) return;

    const entry = document.createElement("div");
    entry.className = "log-entry";

    // Determine action icon
    let icon = "\u25B6";
    if (action) {
      const toolName = action.split("(")[0];
      icon = ACTION_ICONS[toolName] || "\u25B6";
    }

    // Determine result class
    let resultClass = "result--neutral";
    if (result && SUCCESS_RE.test(result)) resultClass = "result--success";
    else if (result && DAMAGE_RE.test(result)) resultClass = "result--damage";

    if (action) {
      const actionSpan = document.createElement("span");
      actionSpan.className = "log-action";
      actionSpan.textContent = icon + " " + action;
      entry.appendChild(actionSpan);
    }

    if (result) {
      const resultSpan = document.createElement("span");
      resultSpan.className = "log-result " + resultClass;
      resultSpan.textContent = result;
      entry.appendChild(resultSpan);
    }

    log.appendChild(entry);

    // Max 20 entries (skip the header)
    const entries = log.querySelectorAll(".log-entry");
    while (entries.length > 20) {
      entries[0].remove();
    }

    // Auto-scroll
    log.scrollTop = log.scrollHeight;
  }

  function renderScan(scanText) {
    const panel = document.getElementById("scan-panel");
    if (!panel) return;
    const pre = panel.querySelector(".scan-text");
    if (pre) pre.textContent = scanText || "";
  }

  function renderGameOver(data) {
    const overlay = document.getElementById("game-over-overlay");
    if (!overlay) return;

    overlay.style.display = "flex";
    overlay.className = "game-over-overlay";

    if (data.won) {
      overlay.classList.add("game-over--victory");
    } else if (data.reason && /fallen/i.test(data.reason)) {
      overlay.classList.add("game-over--defeat");
    } else {
      overlay.classList.add("game-over--timeout");
    }

    overlay.textContent = "";

    const title = document.createElement("h2");
    title.textContent = data.won ? "MISSION COMPLETE" : "MISSION FAILED";
    overlay.appendChild(title);

    const reason = document.createElement("p");
    reason.textContent = data.reason || "";
    overlay.appendChild(reason);

    if (data.stats) {
      const stats = document.createElement("div");
      stats.className = "game-over-stats";
      const lines = [
        "Turns: " + data.stats.turns,
        "Dossiers: " + data.stats.dossiers,
        "Health: " + data.stats.health,
        "Explored: " + data.stats.visited + " cells",
      ];
      for (const line of lines) {
        const p = document.createElement("p");
        p.textContent = line;
        stats.appendChild(p);
      }
      overlay.appendChild(stats);
    }

    const btn = document.createElement("button");
    btn.className = "btn btn--primary";
    btn.textContent = "Play Again";
    btn.addEventListener("click", function () {
      overlay.style.display = "none";
      if (window.GameControls) window.GameControls.resetGame();
    });
    overlay.appendChild(btn);
  }

  function updateUI(message) {
    if (!message) return;

    if (message.type === "turn_update") {
      const s = message.state;
      if (s) {
        renderGrid(s);
        renderHealth(s);
        renderDossierBar(s);
        renderTurnBar(s);
        renderInventory(s);
        renderScan(message.scan);
      }
      renderActionLog(message.action, message.result);
    } else if (message.type === "game_over") {
      renderGameOver(message);
    } else if (message.type === "error") {
      renderActionLog("", message.message);
      // Style the last entry as damage
      const log = document.getElementById("action-log");
      if (log) {
        const last = log.querySelector(".log-entry:last-child .log-result");
        if (last) {
          last.classList.remove("result--neutral", "result--success");
          last.classList.add("result--damage");
        }
      }
    }
  }

  return { updateUI, renderGameOver, renderActionLog };
})();

window.GameRenderer = GameRenderer;

// CONTROLS module follows (ISSUE-6)

// ==========================================================================
// CONTROLS + WEBSOCKET module (ISSUE-6)
// ==========================================================================

const GameControls = (function () {
  let ws = null;
  let sessionId = null;
  let mode = "manual";
  let autoRunning = false;
  let gameOver = false;

  // -------------------------------------------------------------------
  // WebSocket client
  // -------------------------------------------------------------------

  function connectGame(sid) {
    sessionId = sid;
    const protocol = location.protocol === "https:" ? "wss:" : "ws:";
    ws = new WebSocket(protocol + "//" + location.host + "/ws/game/" + sid);

    ws.onmessage = function (event) {
      let msg;
      try {
        msg = JSON.parse(event.data);
      } catch (e) {
        return;
      }

      if (msg.type === "auto_started") {
        autoRunning = true;
        updateControlState();
      } else if (msg.type === "auto_stopped") {
        autoRunning = false;
        updateControlState();
      } else if (msg.type === "game_over") {
        gameOver = true;
        updateControlState();
      }

      GameRenderer.updateUI(msg);
    };

    ws.onclose = function () {
      GameRenderer.renderActionLog("", "Disconnected from server.");
    };

    ws.onerror = function () {
      GameRenderer.renderActionLog("", "WebSocket error.");
    };
  }

  function sendMessage(obj) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(obj));
    }
  }

  function sendAction(tool, args) {
    sendMessage({ type: "manual_action", tool: tool, args: args });
  }

  function startAuto(systemPrompt, thinkCode) {
    sendMessage({
      type: "start_auto",
      system_prompt: systemPrompt,
      think_code: thinkCode,
    });
  }

  function stopAuto() {
    sendMessage({ type: "stop_auto" });
  }

  function resetGame() {
    sendMessage({ type: "reset" });
    // Clear action log
    const log = document.getElementById("action-log");
    if (log) {
      const header = log.querySelector(".log-header");
      log.textContent = "";
      if (header) log.appendChild(header);
    }
    gameOver = false;
    autoRunning = false;
    // Hide game over overlay
    const overlay = document.getElementById("game-over-overlay");
    if (overlay) overlay.style.display = "none";
    updateControlState();
  }

  // -------------------------------------------------------------------
  // Control state management
  // -------------------------------------------------------------------

  function updateControlState() {
    const disabled = autoRunning || gameOver;

    // D-pad buttons
    for (const id of ["dpad-north", "dpad-south", "dpad-east", "dpad-west"]) {
      const btn = document.getElementById(id);
      if (btn) btn.disabled = disabled;
    }

    // Action buttons
    const collect = document.getElementById("btn-collect");
    if (collect) collect.disabled = disabled;

    const talkSend = document.getElementById("talk-send");
    if (talkSend) talkSend.disabled = disabled;
    const talkInput = document.getElementById("talk-input");
    if (talkInput) talkInput.disabled = disabled;

    const fabSend = document.getElementById("fabricate-send");
    if (fabSend) fabSend.disabled = disabled;
    const fabInput = document.getElementById("fabricate-input");
    if (fabInput) fabInput.disabled = disabled;

    // Auto mode buttons
    const btnRun = document.getElementById("btn-run");
    if (btnRun) btnRun.disabled = mode !== "auto" || autoRunning || gameOver;

    const btnStop = document.getElementById("btn-stop");
    if (btnStop) btnStop.disabled = !autoRunning;

    // Mode buttons
    const btnManual = document.getElementById("btn-manual");
    const btnAuto = document.getElementById("btn-auto");
    if (btnManual) btnManual.classList.toggle("btn--primary", mode === "manual");
    if (btnAuto) btnAuto.classList.toggle("btn--primary", mode === "auto");

    // Show/hide sections based on mode
    const controlsArea = document.getElementById("controls-area");
    const editorArea = document.getElementById("editor-area");

    if (mode === "manual") {
      if (controlsArea) controlsArea.style.display = "";
      if (editorArea) editorArea.classList.add("editor-panel--collapsed");
    } else {
      if (controlsArea) controlsArea.style.display = "";
      if (editorArea) editorArea.classList.remove("editor-panel--collapsed");
    }
  }

  // -------------------------------------------------------------------
  // Event binding
  // -------------------------------------------------------------------

  function bindControls() {
    // D-pad
    const directions = { "dpad-north": "north", "dpad-south": "south", "dpad-east": "east", "dpad-west": "west" };
    for (const [id, dir] of Object.entries(directions)) {
      const btn = document.getElementById(id);
      if (btn) btn.addEventListener("click", function () { sendAction("move", { direction: dir }); });
    }

    // Keyboard controls
    document.addEventListener("keydown", function (e) {
      // Skip if a textarea or input is focused
      const tag = document.activeElement && document.activeElement.tagName;
      if (tag === "TEXTAREA" || tag === "INPUT") return;
      if (autoRunning || gameOver) return;

      const keyMap = {
        ArrowUp: "north", w: "north", W: "north",
        ArrowDown: "south", s: "south", S: "south",
        ArrowLeft: "west", a: "west", A: "west",
        ArrowRight: "east", d: "east", D: "east",
      };
      const dir = keyMap[e.key];
      if (dir) {
        e.preventDefault();
        sendAction("move", { direction: dir });
      }
    });

    // Collect
    const collectBtn = document.getElementById("btn-collect");
    if (collectBtn) collectBtn.addEventListener("click", function () { sendAction("collect", {}); });

    // Talk
    const talkInput = document.getElementById("talk-input");
    const talkSend = document.getElementById("talk-send");
    function doTalk() {
      const val = talkInput ? talkInput.value.trim() : "";
      if (!val) return;
      sendAction("talk", { message: val });
      if (talkInput) talkInput.value = "";
    }
    if (talkSend) talkSend.addEventListener("click", doTalk);
    if (talkInput) talkInput.addEventListener("keydown", function (e) {
      if (e.key === "Enter") { e.preventDefault(); doTalk(); }
    });

    // Fabricate
    const fabInput = document.getElementById("fabricate-input");
    const fabSend = document.getElementById("fabricate-send");
    function doFabricate() {
      const val = fabInput ? fabInput.value.trim() : "";
      if (!val) return;
      sendAction("fabricate", { item: val });
      if (fabInput) fabInput.value = "";
    }
    if (fabSend) fabSend.addEventListener("click", doFabricate);
    if (fabInput) fabInput.addEventListener("keydown", function (e) {
      if (e.key === "Enter") { e.preventDefault(); doFabricate(); }
    });

    // Mode switching
    const btnManual = document.getElementById("btn-manual");
    const btnAuto = document.getElementById("btn-auto");
    if (btnManual) btnManual.addEventListener("click", function () {
      mode = "manual";
      updateControlState();
    });
    if (btnAuto) btnAuto.addEventListener("click", function () {
      mode = "auto";
      updateControlState();
    });

    // Run / Stop
    const btnRun = document.getElementById("btn-run");
    if (btnRun) btnRun.addEventListener("click", function () {
      const sysPrompt = document.getElementById("system-prompt");
      const thinkCode = document.getElementById("think-code");
      const sp = sysPrompt ? sysPrompt.value : "";
      const tc = thinkCode ? thinkCode.value : "";
      if (!tc.trim()) {
        GameRenderer.renderActionLog("", "No think_llm code provided.");
        return;
      }
      startAuto(sp, tc);
    });

    const btnStop = document.getElementById("btn-stop");
    if (btnStop) btnStop.addEventListener("click", function () { stopAuto(); });

    // Reset
    const btnReset = document.getElementById("btn-reset");
    if (btnReset) btnReset.addEventListener("click", function () { resetGame(); });

    // Editor collapse toggle
    const editorToggle = document.getElementById("editor-toggle");
    const editorArea = document.getElementById("editor-area");
    if (editorToggle && editorArea) {
      editorToggle.addEventListener("click", function () {
        editorArea.classList.toggle("editor-panel--collapsed");
      });
    }

    // Tab key in textareas — insert 4 spaces
    for (const id of ["system-prompt", "think-code"]) {
      const ta = document.getElementById(id);
      if (ta) {
        ta.addEventListener("keydown", function (e) {
          if (e.key === "Tab") {
            e.preventDefault();
            const start = ta.selectionStart;
            const end = ta.selectionEnd;
            ta.value = ta.value.substring(0, start) + "    " + ta.value.substring(end);
            ta.selectionStart = ta.selectionEnd = start + 4;
          }
        });
      }
    }

    // localStorage persistence for editor
    const sysPromptEl = document.getElementById("system-prompt");
    const thinkCodeEl = document.getElementById("think-code");

    if (sysPromptEl) {
      sysPromptEl.addEventListener("input", function () {
        localStorage.setItem("spy_system_prompt", sysPromptEl.value);
      });
    }
    if (thinkCodeEl) {
      thinkCodeEl.addEventListener("input", function () {
        localStorage.setItem("spy_think_code", thinkCodeEl.value);
      });
    }
  }

  // -------------------------------------------------------------------
  // Restore editor from localStorage
  // -------------------------------------------------------------------

  function restoreEditor() {
    const savedPrompt = localStorage.getItem("spy_system_prompt");
    const savedCode = localStorage.getItem("spy_think_code");
    const sysPromptEl = document.getElementById("system-prompt");
    const thinkCodeEl = document.getElementById("think-code");

    if (savedPrompt && sysPromptEl) sysPromptEl.value = savedPrompt;
    if (savedCode && thinkCodeEl) thinkCodeEl.value = savedCode;
  }

  // -------------------------------------------------------------------
  // Initialization
  // -------------------------------------------------------------------

  function init() {
    bindControls();
    restoreEditor();
    updateControlState();

    fetch("/api/game/new", { method: "POST" })
      .then(function (r) { return r.json(); })
      .then(function (resp) {
        sessionId = resp.session_id;
        connectGame(sessionId);

        // Render initial state
        GameRenderer.updateUI({
          type: "turn_update",
          turn: 0,
          action: "",
          result: resp.mission_briefing,
          scan: "",
          state: resp.state,
        });
      })
      .catch(function (err) {
        GameRenderer.renderActionLog("", "Failed to create game: " + err.message);
      });
  }

  document.addEventListener("DOMContentLoaded", init);

  return { connectGame, sendAction, startAuto, stopAuto, resetGame };
})();

window.GameControls = GameControls;
