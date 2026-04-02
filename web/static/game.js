// ============================================================
// THE HIDDEN LAYER — Game Renderer (ISSUE-5)
// ============================================================

(function () {
  "use strict";

  // Track previously visible cell positions for reveal animations
  let previouslyVisible = new Set();

  // Item icon mapping
  const ITEM_ICONS = {
    "USB Drive": "\u{1F4BE}",
    "Flamethrower": "\u{1F525}",
    "Scrap Metal": "\u2699\uFE0F",
    "Microfilm": "\u{1F4F7}",
    "Fuel Canister": "\u26FD",
    "Hard Drive": "\u{1F4BF}",
    "Medical Supplies": "\u{1FA79}",
    "Virus Code": "\u{1F4BB}",
    "Computer Virus": "\u{1F41B}",
    "Radio Codebook": "\u{1F4D7}",
  };

  // NPC portrait mapping
  const NPC_PORTRAITS = {
    "dr_vapnik": "assets/dr_vapnik.jpg",
    "dropout": "assets/agent_dropout.jpg",
    "cryo_sentinel": "assets/cryo_sentinel.png",
  };

  // Action icon mapping
  const ACTION_ICONS = {
    move: "\u{1F9ED}",
    talk: "\u{1F4AC}",
    collect: "\u270B",
    fabricate: "\u{1F527}",
  };

  // Success/damage keyword patterns
  const SUCCESS_PATTERN =
    /dossier|collected|delivered|built|destroy|reward|mission complete/i;
  const DAMAGE_PATTERN =
    /damage|hurt|fail|cannot|retreat|tripwire|neutralized/i;

  // ---- 1. renderGrid(state) ----
  function renderGrid(state) {
    const container = document.getElementById("game-map");
    if (!container) return;

    const rows = state.rows;
    const cols = state.cols;
    const grid = state.grid;
    const position = state.position;

    // Build set of currently visible positions
    const currentlyVisible = new Set();
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        if (grid[r][c].visible) {
          currentlyVisible.add(r + "," + c);
        }
      }
    }

    // Set CSS grid columns
    container.style.setProperty("--grid-cols", cols);

    // Clear existing grid if dimensions changed
    const existingCells = container.querySelectorAll(".cell");
    if (existingCells.length !== rows * cols) {
      while (container.firstChild) {
        container.removeChild(container.firstChild);
      }
    }

    // Ensure we have enough cells
    let cells = container.querySelectorAll(".cell");
    if (cells.length === 0) {
      for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
          const div = document.createElement("div");
          container.appendChild(div);
        }
      }
      cells = container.querySelectorAll("div");
    }

    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const idx = r * cols + c;
        const cellEl = cells[idx];
        const cellData = grid[r][c];
        const key = r + "," + c;
        const isAgent = position[0] === r && position[1] === c;

        // Reset classes
        cellEl.className = "cell";

        if (!cellData.visible) {
          cellEl.classList.add("cell--fog");
          cellEl.textContent = "\u2591";
        } else {
          cellEl.classList.add("cell--" + cellData.type);

          if (isAgent) {
            cellEl.classList.add("cell--agent");
            cellEl.textContent = "\u{1F574}\uFE0F";
          } else {
            cellEl.textContent = cellData.emoji;
          }

          // Check if newly revealed
          if (!previouslyVisible.has(key)) {
            cellEl.classList.add("cell--reveal");
            setTimeout(function () {
              cellEl.classList.remove("cell--reveal");
            }, 300);
          }
        }
      }
    }

    // Update tracked visible set
    previouslyVisible = currentlyVisible;
  }

  // ---- 2. renderHealth(state) ----
  function renderHealth(state) {
    const container = document.getElementById("health-bar");
    if (!container) return;

    while (container.firstChild) {
      container.removeChild(container.firstChild);
    }

    for (let i = 0; i < state.max_health; i++) {
      const span = document.createElement("span");
      span.textContent = i < state.health ? "\u2764\uFE0F" : "\u{1F5A4}";
      container.appendChild(span);
    }
  }

  // ---- 3. renderDossierBar(state) ----
  function renderDossierBar(state) {
    const container = document.getElementById("dossier-bar");
    if (!container) return;

    // Ensure inner bar and label exist
    let inner = container.querySelector(".dossier-bar__fill");
    let label = container.querySelector(".dossier-bar__text");

    if (!inner) {
      inner = document.createElement("div");
      inner.className = "dossier-bar__fill";
      container.appendChild(inner);
    }
    if (!label) {
      label = document.createElement("span");
      label.className = "dossier-bar__text";
      container.appendChild(label);
    }

    const pct = state.win_dossiers > 0
      ? (state.dossiers / state.win_dossiers) * 100
      : 0;
    inner.style.width = Math.min(pct, 100) + "%";

    label.textContent = state.dossiers + "/" + state.win_dossiers;

    if (state.dossiers >= state.win_dossiers) {
      container.classList.add("dossier-bar--complete");
    } else {
      container.classList.remove("dossier-bar--complete");
    }
  }

  // ---- 4. renderTurnBar(state) ----
  function renderTurnBar(state) {
    const container = document.getElementById("turn-bar");
    if (!container) return;

    let inner = container.querySelector(".turn-bar__fill");
    let label = container.querySelector(".turn-bar__text");

    if (!inner) {
      inner = document.createElement("div");
      inner.className = "turn-bar__fill";
      container.appendChild(inner);
    }
    if (!label) {
      label = document.createElement("span");
      label.className = "turn-bar__text";
      container.appendChild(label);
    }

    const pct = state.max_turns > 0
      ? (state.turn / state.max_turns) * 100
      : 0;
    inner.style.width = Math.min(pct, 100) + "%";

    label.textContent = "Turn " + state.turn + "/" + state.max_turns;

    // Remove old color classes
    container.classList.remove("turn-bar--ok", "turn-bar--warn", "turn-bar--danger");

    if (pct >= 80) {
      container.classList.add("turn-bar--danger");
    } else if (pct >= 60) {
      container.classList.add("turn-bar--warn");
    } else {
      container.classList.add("turn-bar--ok");
    }
  }

  // ---- 5. renderInventory(state) ----
  function renderInventory(state) {
    const container = document.getElementById("inventory");
    if (!container) return;

    // Target the .inventory-items child, or fall back to container
    let target = container.querySelector(".inventory-items") || container;

    while (target.firstChild) {
      target.removeChild(target.firstChild);
    }

    if (!state.inventory || state.inventory.length === 0) {
      const empty = document.createElement("span");
      empty.className = "item-slot";
      empty.style.fontStyle = "italic";
      empty.textContent = "Empty";
      target.appendChild(empty);
      return;
    }

    for (let i = 0; i < state.inventory.length; i++) {
      const name = state.inventory[i];
      const icon = ITEM_ICONS[name] || "\u{1F4E6}";
      const span = document.createElement("span");
      span.className = "item-slot";
      span.textContent = icon + " " + name;
      target.appendChild(span);
    }
  }

  // ---- 6. renderActionLog(action, result, portraitKey) ----
  function renderActionLog(action, result, portraitKey) {
    const container = document.getElementById("action-log");
    if (!container) return;

    const entry = document.createElement("div");
    entry.className = "log-entry";

    // Determine action icon
    var icon = "\u{1F4CB}";
    if (action) {
      var actionName = action.split("(")[0];
      if (ACTION_ICONS[actionName]) {
        icon = ACTION_ICONS[actionName];
      }
    }

    // Action line
    if (action) {
      const actionSpan = document.createElement("div");
      actionSpan.className = "log-action";
      actionSpan.textContent = icon + " " + action;
      entry.appendChild(actionSpan);
    }

    // NPC portrait if talking to an NPC
    if (portraitKey && NPC_PORTRAITS[portraitKey]) {
      const img = document.createElement("img");
      img.className = "log-portrait";
      img.src = NPC_PORTRAITS[portraitKey];
      img.alt = portraitKey;
      entry.appendChild(img);
    }

    // Result line with color coding
    if (result) {
      const resultSpan = document.createElement("div");
      resultSpan.className = "log-result";

      if (SUCCESS_PATTERN.test(result)) {
        resultSpan.classList.add("result--success");
      } else if (DAMAGE_PATTERN.test(result)) {
        resultSpan.classList.add("result--damage");
      } else {
        resultSpan.classList.add("result--neutral");
      }

      resultSpan.textContent = result;
      entry.appendChild(resultSpan);
    }

    container.appendChild(entry);

    // Cap at 20 entries (keep log-header)
    var entries = container.querySelectorAll(".log-entry");
    while (entries.length > 20) {
      container.removeChild(entries[0]);
      entries = container.querySelectorAll(".log-entry");
    }

    // Auto-scroll to bottom
    container.scrollTop = container.scrollHeight;
  }

  // ---- 7. renderScan(scanText) ----
  function renderScan(scanText) {
    const container = document.getElementById("scan-panel");
    if (!container) return;
    const pre = container.querySelector(".scan-text");
    if (pre) {
      pre.textContent = scanText || "";
    } else {
      container.textContent = scanText || "";
    }
  }

  // ---- 8. renderGameOver(data) ----
  function renderGameOver(data) {
    const overlay = document.getElementById("game-over-overlay");
    if (!overlay) return;

    // Clear previous content
    while (overlay.firstChild) {
      overlay.removeChild(overlay.firstChild);
    }

    overlay.className = "game-over-overlay game-over--visible";

    // Determine outcome class
    if (data.won) {
      overlay.classList.add("game-over--victory");
    } else if (data.reason && /fallen/i.test(data.reason)) {
      overlay.classList.add("game-over--defeat");
    } else {
      overlay.classList.add("game-over--timeout");
    }

    const panel = document.createElement("div");
    panel.className = "game-over-box";

    // Title
    const title = document.createElement("h2");
    title.textContent = data.won ? "MISSION COMPLETE" : "MISSION FAILED";
    panel.appendChild(title);

    // Reason
    if (data.reason) {
      const reason = document.createElement("p");
      reason.textContent = data.reason;
      panel.appendChild(reason);
    }

    // Stats
    if (data.stats) {
      const stats = document.createElement("div");
      stats.className = "stats";

      var lines = [
        "Turns: " + data.stats.turns,
        "Dossiers: " + data.stats.dossiers,
        "Health: " + data.stats.health,
        "Cells Visited: " + data.stats.visited,
      ];

      for (var i = 0; i < lines.length; i++) {
        var line = document.createElement("div");
        line.textContent = lines[i];
        stats.appendChild(line);
      }

      panel.appendChild(stats);
    }

    // Button row
    const btnRow = document.createElement("div");
    btnRow.style.display = "flex";
    btnRow.style.gap = "8px";
    btnRow.style.justifyContent = "center";
    btnRow.style.marginTop = "12px";

    // Play Again button
    const btn = document.createElement("button");
    btn.className = "btn btn--primary";
    btn.textContent = "Play Again";
    btn.addEventListener("click", function () {
      overlay.classList.remove("game-over--visible");
      if (window.GameControls && window.GameControls.resetGame) {
        window.GameControls.resetGame();
      }
    });
    btnRow.appendChild(btn);

    // Download Log button
    if (data.log) {
      const dlBtn = document.createElement("button");
      dlBtn.className = "btn btn--success";
      dlBtn.textContent = "\u{1F4BE} Download Log";
      dlBtn.addEventListener("click", function () {
        var logData = {
          outcome: data.won ? "mission_complete" : "mission_failed",
          reason: data.reason,
          stats: data.stats,
          history: data.log,
        };
        var blob = new Blob([JSON.stringify(logData, null, 2)], { type: "application/json" });
        var url = URL.createObjectURL(blob);
        var a = document.createElement("a");
        a.href = url;
        a.download = "game_log_" + (data.won ? "win" : "fail") + "_" + Date.now() + ".json";
        a.click();
        URL.revokeObjectURL(url);
      });
      btnRow.appendChild(dlBtn);
    }

    panel.appendChild(btnRow);
    overlay.appendChild(panel);
  }

  // Helper: detect NPC portrait key from talk action and current cell
  function detectPortraitKey(state, action) {
    if (!action || !action.startsWith("talk")) return null;
    if (!state || !state.grid || !state.position) return null;
    var r = state.position[0], c = state.position[1];
    var cell = state.grid[r] && state.grid[r][c];
    if (!cell || !cell.npc_name) return null;
    // Map NPC names to portrait keys
    var name = cell.npc_name.toLowerCase();
    if (name.indexOf("vapnik") !== -1) return "dr_vapnik";
    if (name.indexOf("dropout") !== -1) return "dropout";
    if (name.indexOf("cryo") !== -1) return "cryo_sentinel";
    return null;
  }

  // Remove LLM thinking spinner from action log
  function removeSpinner() {
    var container = document.getElementById("action-log");
    if (!container) return;
    var spinner = container.querySelector(".log-spinner");
    if (spinner) spinner.parentNode.removeChild(spinner);
  }

  // Add LLM thinking spinner to action log
  function showSpinner() {
    removeSpinner();
    var container = document.getElementById("action-log");
    if (!container) return;
    var el = document.createElement("div");
    el.className = "log-entry log-spinner";
    var span = document.createElement("span");
    span.className = "spinner";
    el.appendChild(span);
    var text = document.createElement("span");
    text.textContent = " LLM thinking...";
    text.style.color = "var(--amber)";
    el.appendChild(text);
    container.appendChild(el);
    container.scrollTop = container.scrollHeight;
  }

  // ---- 9. updateUI(message) ----
  function updateUI(message) {
    if (!message || !message.type) return;

    switch (message.type) {
      case "turn_update":
        removeSpinner();
        if (message.state) {
          renderGrid(message.state);
          renderHealth(message.state);
          renderDossierBar(message.state);
          renderTurnBar(message.state);
          renderInventory(message.state);
        }
        var portrait = detectPortraitKey(message.state, message.action);
        renderActionLog(message.action, message.result, portrait);
        // Show LLM debug info if there were errors
        if (message.think_error) {
          renderActionLog("", "\u26a0\ufe0f think_llm error: " + message.think_error);
        }
        if (message.parse_error) {
          renderActionLog("", "\u26a0\ufe0f Parse error: " + message.parse_error);
        }
        if (message.llm_raw && (message.think_error || message.parse_error || (message.action && message.action.startsWith("scan")))) {
          renderActionLog("", "\u{1F916} LLM raw: " + message.llm_raw);
        }
        renderScan(message.scan);
        // Show spinner if auto mode is running (next turn coming)
        if (window._autoRunning && message.state && message.state.is_alive && !message.state.has_won) {
          showSpinner();
        }
        break;

      case "game_over":
        removeSpinner();
        renderGameOver(message);
        break;

      case "auto_started":
        showSpinner();
        break;

      case "auto_stopped":
        removeSpinner();
        break;

      case "error":
        removeSpinner();
        renderActionLog("", message.message || "Unknown error");
        // Force damage styling on the last entry
        var log = document.getElementById("action-log");
        if (log) {
          var lastEntry = log.lastElementChild;
          if (lastEntry) {
            var resultEl = lastEntry.querySelector(".log-result");
            if (resultEl) {
              resultEl.className = "log-result result--damage";
            }
          }
        }
        break;
    }
  }

  // Expose renderer globally
  window.GameRenderer = {
    updateUI: updateUI,
    renderGameOver: renderGameOver,
    renderGrid: renderGrid,
    renderHealth: renderHealth,
    renderDossierBar: renderDossierBar,
    renderTurnBar: renderTurnBar,
    renderInventory: renderInventory,
    renderActionLog: renderActionLog,
    renderScan: renderScan,
  };
})();

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
        window._autoRunning = true;
        updateControlState();
      } else if (msg.type === "auto_stopped") {
        autoRunning = false;
        window._autoRunning = false;
        updateControlState();
      } else if (msg.type === "game_over") {
        gameOver = true;
        autoRunning = false;
        window._autoRunning = false;
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

  function startAuto(systemPrompt) {
    sendMessage({
      type: "start_auto",
      system_prompt: systemPrompt,
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
    // Hide game over panel
    const overlay = document.getElementById("game-over-overlay");
    if (overlay) overlay.classList.remove("game-over--visible");
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
      const sp = sysPrompt ? sysPrompt.value : "";
      if (!sp.trim()) {
        GameRenderer.renderActionLog("", "Please provide a system prompt before running the agent.");
        return;
      }
      startAuto(sp);
    });

    const btnStop = document.getElementById("btn-stop");
    if (btnStop) btnStop.addEventListener("click", function () { stopAuto(); });

    // Reset
    const btnReset = document.getElementById("btn-reset");
    if (btnReset) btnReset.addEventListener("click", function () { resetGame(); });

    // Download Log
    const btnDownloadLog = document.getElementById("btn-download-log");
    if (btnDownloadLog) btnDownloadLog.addEventListener("click", function () {
      if (!sessionId) {
        GameRenderer.renderActionLog("", "No active session.");
        return;
      }
      fetch("/api/game/" + sessionId + "/log")
        .then(function (r) { return r.json(); })
        .then(function (logData) {
          var blob = new Blob([JSON.stringify(logData, null, 2)], { type: "application/json" });
          var url = URL.createObjectURL(blob);
          var a = document.createElement("a");
          a.href = url;
          a.download = "game_log_" + sessionId + ".json";
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          URL.revokeObjectURL(url);
        })
        .catch(function (err) {
          GameRenderer.renderActionLog("", "Failed to download log: " + err.message);
        });
    });

    // API key
    const apiKeyInput = document.getElementById("api-key");
    const btnSaveKey = document.getElementById("btn-save-key");
    const apiKeyStatus = document.getElementById("api-key-status");

    function saveApiKey() {
      const key = apiKeyInput ? apiKeyInput.value.trim() : "";
      if (!key) return;
      fetch("/api/key", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_key: key }),
      })
        .then(function (r) { return r.json(); })
        .then(function (resp) {
          if (apiKeyStatus) {
            apiKeyStatus.textContent = resp.message;
            apiKeyStatus.className = "api-key-status " + (resp.ok ? "api-key--ok" : "api-key--err");
          }
          if (resp.ok && apiKeyInput) {
            localStorage.setItem("spy_gemini_key", key);
          }
        })
        .catch(function (err) {
          if (apiKeyStatus) {
            apiKeyStatus.textContent = "Network error: " + err.message;
            apiKeyStatus.className = "api-key-status api-key--err";
          }
        });
    }

    if (btnSaveKey) btnSaveKey.addEventListener("click", saveApiKey);
    if (apiKeyInput) apiKeyInput.addEventListener("keydown", function (e) {
      if (e.key === "Enter") { e.preventDefault(); saveApiKey(); }
    });

    // Editor collapse toggle
    const editorToggle = document.getElementById("editor-toggle");
    const editorArea = document.getElementById("editor-area");
    if (editorToggle && editorArea) {
      editorToggle.addEventListener("click", function () {
        editorArea.classList.toggle("editor-panel--collapsed");
      });
    }

    // Tab key in textareas — insert 4 spaces
    for (const id of ["system-prompt"]) {
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

    if (sysPromptEl) {
      sysPromptEl.addEventListener("input", function () {
        localStorage.setItem("spy_system_prompt", sysPromptEl.value);
      });
    }
  }

  // -------------------------------------------------------------------
  // Restore editor from localStorage
  // -------------------------------------------------------------------

  function restoreEditor() {
    const savedPrompt = localStorage.getItem("spy_system_prompt");
    const sysPromptEl = document.getElementById("system-prompt");
    if (savedPrompt && sysPromptEl) sysPromptEl.value = savedPrompt;

    // Restore saved API key and check status
    const savedKey = localStorage.getItem("spy_gemini_key");
    const apiKeyInput = document.getElementById("api-key");
    if (savedKey && apiKeyInput) apiKeyInput.value = savedKey;

    // Check current key status from server
    fetch("/api/key/status")
      .then(function (r) { return r.json(); })
      .then(function (resp) {
        const apiKeyStatus = document.getElementById("api-key-status");
        if (!apiKeyStatus) return;
        if (resp.configured) {
          apiKeyStatus.textContent = "Key active";
          apiKeyStatus.className = "api-key-status api-key--ok";
        } else if (savedKey) {
          // Have a saved key but server doesn't — re-send it
          fetch("/api/key", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ api_key: savedKey }),
          })
            .then(function (r) { return r.json(); })
            .then(function (r2) {
              apiKeyStatus.textContent = r2.ok ? "Key active" : r2.message;
              apiKeyStatus.className = "api-key-status " + (r2.ok ? "api-key--ok" : "api-key--err");
            });
        } else {
          apiKeyStatus.textContent = "No key set";
          apiKeyStatus.className = "api-key-status api-key--err";
        }
      })
      .catch(function () {});
  }

  // -------------------------------------------------------------------
  // Mission briefing panel
  // -------------------------------------------------------------------

  function showMissionBriefing() {
    var log = document.getElementById("action-log");
    if (!log) return;
    var panel = document.createElement("div");
    panel.className = "log-entry mission-briefing";
    var text = document.createElement("div");
    text.className = "result--success";
    text.textContent = "\u{1F4CB} Collect 3 dossiers. Talk to informants. Destroy the robot. 30 turns.";
    panel.appendChild(text);
    var dismiss = document.createElement("button");
    dismiss.className = "btn";
    dismiss.textContent = "\u2715 Dismiss";
    dismiss.style.marginTop = "4px";
    dismiss.style.fontSize = "10px";
    dismiss.addEventListener("click", function () {
      panel.parentNode.removeChild(panel);
    });
    panel.appendChild(dismiss);
    // Insert at top (after log-header)
    var header = log.querySelector(".log-header");
    if (header && header.nextSibling) {
      log.insertBefore(panel, header.nextSibling);
    } else {
      log.appendChild(panel);
    }
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

        // Show dismissible mission briefing panel
        showMissionBriefing();
      })
      .catch(function (err) {
        GameRenderer.renderActionLog("", "Failed to create game: " + err.message);
      });
  }

  document.addEventListener("DOMContentLoaded", init);

  return { connectGame, sendAction, startAuto, stopAuto, resetGame };
})();

window.GameControls = GameControls;
