/**
 * The Support Layer — Frontend game client.
 *
 * Equivalent to game.js in the spy game. Handles:
 * - WebSocket connection to the server
 * - Rendering inbox, ticket details, stats, and action log
 * - Manual and auto mode controls
 */

// =========================================================================
// GameRenderer — updates UI from state
// =========================================================================
const GameRenderer = (() => {
    function renderStats(state) {
        // CSAT bar
        const csatFill = document.querySelector('#csat-bar .fill');
        const csatPct = (state.csat_stars / state.win_csat) * 100;
        csatFill.style.width = `${Math.min(100, csatPct)}%`;
        document.getElementById('csat-label').textContent =
            `${state.csat_stars}/${state.win_csat}`;

        // Turn bar
        const turnFill = document.querySelector('#turn-bar .fill');
        const turnPct = (state.turn / state.max_turns) * 100;
        turnFill.style.width = `${turnPct}%`;
        if (turnPct > 80) turnFill.style.background = 'var(--danger)';
        else if (turnPct > 60) turnFill.style.background = 'var(--warning)';
        else turnFill.style.background = 'var(--info)';
        document.getElementById('turn-label').textContent =
            `${state.turn}/${state.max_turns}`;

        // Context budget pips
        const budgetEl = document.getElementById('budget-display');
        budgetEl.innerHTML = '';
        for (let i = 0; i < state.max_context_budget; i++) {
            const pip = document.createElement('div');
            pip.className = `budget-pip ${i < state.context_budget ? 'full' : 'empty'}`;
            budgetEl.appendChild(pip);
        }

        // Snippets
        const snippetsEl = document.getElementById('snippets-list');
        snippetsEl.textContent = state.snippets.length > 0
            ? state.snippets.join(', ')
            : 'none';
    }

    function renderInbox(state) {
        const listEl = document.getElementById('inbox-list');
        listEl.innerHTML = '';

        const selectEl = document.getElementById('ticket-select');
        selectEl.innerHTML = '';

        for (const ticket of state.inbox) {
            // Card
            const card = document.createElement('div');
            card.className = `ticket-card ${ticket.status}`;
            if (ticket.id === state.current_ticket_id) card.classList.add('active');

            const patienceChars = Math.max(0, ticket.patience_remaining);
            const patienceMax = ticket.patience;
            const pBar = '█'.repeat(patienceChars) + '░'.repeat(patienceMax - patienceChars);

            card.innerHTML = `
                <div class="ticket-id">${ticket.id}
                    <span class="priority-badge priority-${ticket.priority}">${ticket.priority}</span>
                </div>
                <div class="ticket-subject">${ticket.subject}</div>
                <div class="ticket-meta">
                    <span>${ticket.topic}</span>
                    <span>${ticket.customer_name}</span>
                    <span class="patience-bar">${pBar} ${ticket.patience_remaining}/${ticket.patience}</span>
                </div>
            `;

            card.onclick = () => {
                if (ticket.status === 'open' || ticket.status === 'in_progress') {
                    GameControls.sendAction('open_ticket', { ticket_id: ticket.id });
                }
            };

            listEl.appendChild(card);

            // Select option (only open/in_progress)
            if (ticket.status === 'open' || ticket.status === 'in_progress') {
                const opt = document.createElement('option');
                opt.value = ticket.id;
                opt.textContent = `${ticket.id}: ${ticket.subject.substring(0, 30)}`;
                selectEl.appendChild(opt);
            }
        }
    }

    function renderTicketDetail(state) {
        const panel = document.getElementById('ticket-panel');
        const header = document.getElementById('ticket-header');
        const messagesEl = document.getElementById('ticket-messages');

        if (!state.current_ticket_id) {
            panel.classList.remove('visible');
            panel.style.display = 'none';
            document.getElementById('inbox-panel').style.display = 'block';
            return;
        }

        const ticket = state.inbox.find(t => t.id === state.current_ticket_id);
        if (!ticket) return;

        document.getElementById('inbox-panel').style.display = 'none';
        panel.style.display = 'block';
        panel.classList.add('visible');

        header.textContent = `${ticket.id}: ${ticket.subject}`;
        messagesEl.innerHTML = '';

        if (ticket.messages && ticket.messages.length > 0) {
            for (const msg of ticket.messages) {
                const bubble = document.createElement('div');
                bubble.className = `message-bubble ${msg.sender}`;
                bubble.innerHTML = `
                    <div class="message-sender">${msg.sender}</div>
                    <div>${msg.content}</div>
                `;
                messagesEl.appendChild(bubble);
            }
        } else {
            messagesEl.innerHTML = '<p style="color: var(--text-dim)">Ticket not yet read. Use "Read Ticket" to see messages.</p>';
        }
    }

    function renderMacros(state) {
        const selectEl = document.getElementById('macro-select');
        selectEl.innerHTML = '';
        for (const [id, macro] of Object.entries(state.macros)) {
            const opt = document.createElement('option');
            opt.value = id;
            let label = macro.name;
            if (macro.requires_authorization && !macro.authorized) {
                label += ' (needs auth)';
            } else if (macro.requires_authorization && macro.authorized) {
                label += ' (authorized)';
            }
            opt.textContent = label;
            selectEl.appendChild(opt);
        }
    }

    function addLogEntry(turn, action, result, success, thought) {
        const logEl = document.getElementById('action-log');
        const entry = document.createElement('div');

        let cls = 'info';
        if (result && /resolved|csat|excellent|great/i.test(result)) cls = 'success';
        if (result && /error|fail|breach|damage|expired|crash/i.test(result)) cls = 'error';

        entry.className = `log-entry ${success ? cls : 'error'}`;
        entry.innerHTML = `
            <div class="log-turn">Turn ${turn}</div>
            <div class="log-action">${action}</div>
            ${thought ? `<div class="log-thought">${thought.substring(0, 200)}</div>` : ''}
            <div class="log-result">${result}</div>
        `;
        logEl.insertBefore(entry, logEl.firstChild);
    }

    function renderGameOver(data) {
        const modal = document.getElementById('game-over-modal');
        const title = document.getElementById('game-over-title');
        const reason = document.getElementById('game-over-reason');
        const stats = document.getElementById('game-over-stats');

        modal.classList.remove('hidden');
        title.textContent = data.won ? 'SHIFT COMPLETE!' : 'SHIFT FAILED';
        title.style.color = data.won ? 'var(--success)' : 'var(--danger)';
        reason.textContent = data.reason;

        const s = data.state;
        stats.innerHTML = `
            <p>CSAT Stars: ${s.csat_stars}/${s.win_csat}</p>
            <p>Context Budget: ${s.context_budget}/${s.max_context_budget}</p>
            <p>Turns Used: ${s.turn}/${s.max_turns}</p>
            <p>Resolved: ${s.resolved_tickets.length}</p>
            <p>Escalated: ${s.escalated_tickets.length}</p>
            <p>Snippets: ${s.snippets.join(', ') || 'none'}</p>
        `;
    }

    function updateUI(message) {
        if (message.type === 'turn_update') {
            renderStats(message.state);
            renderInbox(message.state);
            renderTicketDetail(message.state);
            renderMacros(message.state);
            addLogEntry(message.turn, message.action, message.result,
                message.state.is_alive, message.thought);
        } else if (message.type === 'state_update' || message.type === 'reset_complete') {
            renderStats(message.state);
            renderInbox(message.state);
            renderTicketDetail(message.state);
            renderMacros(message.state);
            if (message.type === 'reset_complete') {
                document.getElementById('action-log').innerHTML = '';
                document.getElementById('game-over-modal').classList.add('hidden');
            }
        } else if (message.type === 'game_over') {
            renderGameOver(message);
        } else if (message.type === 'error') {
            addLogEntry('-', 'ERROR', message.message, false);
        } else if (message.type === 'auto_stopped') {
            document.getElementById('btn-run').disabled = false;
            document.getElementById('btn-stop').disabled = true;
        }
    }

    return { renderStats, renderInbox, renderTicketDetail, renderMacros, addLogEntry, renderGameOver, updateUI };
})();


// =========================================================================
// GameControls — WebSocket client & action dispatch
// =========================================================================
const GameControls = (() => {
    let ws = null;
    let sessionId = null;

    async function init() {
        // Restore system prompt
        const saved = localStorage.getItem('support_system_prompt');
        if (saved) document.getElementById('system-prompt').value = saved;

        // Restore API key
        const savedKey = localStorage.getItem('support_gemini_key');
        if (savedKey) {
            document.getElementById('api-key-input').value = savedKey;
        }

        // Check API key status
        try {
            const resp = await fetch('/api/key/status');
            const data = await resp.json();
            const el = document.getElementById('key-status');
            if (data.configured) {
                el.textContent = '(configured)';
                el.className = 'key-ok';
            } else {
                el.textContent = '(not set)';
                el.className = 'key-missing';
            }
        } catch (e) {}

        // Create new game
        try {
            const resp = await fetch('/api/game/new', { method: 'POST' });
            const data = await resp.json();
            sessionId = data.session_id;
            GameRenderer.updateUI({ type: 'state_update', state: data.state });
            connectWS();
        } catch (e) {
            console.error('Failed to create game:', e);
        }
    }

    function connectWS() {
        const proto = location.protocol === 'https:' ? 'wss' : 'ws';
        ws = new WebSocket(`${proto}://${location.host}/ws/game/${sessionId}`);

        ws.onmessage = (evt) => {
            const msg = JSON.parse(evt.data);
            GameRenderer.updateUI(msg);

            // Disable run button during auto
            if (msg.type === 'turn_update' && msg.thought) {
                document.getElementById('btn-run').disabled = true;
                document.getElementById('btn-stop').disabled = false;
            }
        };

        ws.onclose = () => {
            console.log('WebSocket closed');
        };
    }

    function sendMessage(obj) {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify(obj));
        }
    }

    function sendAction(tool, args) {
        sendMessage({ type: 'manual_action', tool, args });
    }

    function openTicket() {
        const id = document.getElementById('ticket-select').value;
        if (id) sendAction('open_ticket', { ticket_id: id });
    }

    function searchKB() {
        const query = document.getElementById('kb-query').value.trim();
        if (query) {
            sendAction('search_kb', { query });
            document.getElementById('kb-query').value = '';
        }
    }

    function consultCoworker() {
        const cw = document.getElementById('coworker-select').value;
        sendAction('consult', { coworker: cw });
    }

    function applyMacro() {
        const macro = document.getElementById('macro-select').value;
        if (macro) sendAction('apply_macro', { macro });
    }

    function respond() {
        const msg = document.getElementById('message-input').value.trim();
        if (msg) {
            sendAction('respond', { message: msg });
            document.getElementById('message-input').value = '';
        }
    }

    function askCustomer() {
        const msg = document.getElementById('message-input').value.trim();
        if (msg) {
            sendAction('ask_customer', { question: msg });
            document.getElementById('message-input').value = '';
        }
    }

    function startAuto() {
        const prompt = document.getElementById('system-prompt').value;
        localStorage.setItem('support_system_prompt', prompt);
        sendMessage({ type: 'start_auto', system_prompt: prompt });
        document.getElementById('btn-run').disabled = true;
        document.getElementById('btn-stop').disabled = false;
    }

    function stopAuto() {
        sendMessage({ type: 'stop_auto' });
        document.getElementById('btn-run').disabled = false;
        document.getElementById('btn-stop').disabled = true;
    }

    async function resetGame() {
        sendMessage({ type: 'reset' });
        document.getElementById('btn-run').disabled = false;
        document.getElementById('btn-stop').disabled = true;
    }

    async function setApiKey() {
        const key = document.getElementById('api-key-input').value.trim();
        if (!key) return;
        localStorage.setItem('support_gemini_key', key);
        try {
            const resp = await fetch('/api/key', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ key }),
            });
            const data = await resp.json();
            const el = document.getElementById('key-status');
            if (data.configured) {
                el.textContent = '(configured)';
                el.className = 'key-ok';
            }
        } catch (e) {
            console.error('Failed to set API key:', e);
        }
    }

    // Initialize on load
    window.addEventListener('DOMContentLoaded', init);

    return {
        sendAction, sendMessage, openTicket, searchKB, consultCoworker,
        applyMacro, respond, askCustomer, startAuto, stopAuto, resetGame, setApiKey,
    };
})();
