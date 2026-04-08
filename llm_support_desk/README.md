# The Support Layer

An educational game where you play as an LLM agent staffing a customer support desk. Resolve tickets, search knowledge bases, consult coworkers, and handle adversarial customers — all while managing your context budget and earning CSAT stars.

Built as a teaching tool for AI agent concepts: RAG, tool use, multi-agent orchestration, prompt injection defense, and human-in-the-loop escalation.

## Quick Start

```bash
# Install dependencies
pip install -r web/requirements.txt

# Run the web server
cd web && python server.py
# → http://localhost:8000

# Run tests
pytest tests/
```

## Game Concept

- **Unified inbox** with tickets of varying priority, topic, and difficulty
- **Manual mode**: You pick actions — open tickets, search KB, craft responses
- **Auto mode**: An LLM agent (Gemini) autonomously resolves tickets
- **Win condition**: Earn 3 CSAT stars (micro shift) before running out of turns or context budget

## KPI Mapping

| Real Support Desk | Game Mechanic |
|---|---|
| Customer Satisfaction | CSAT Stars (win condition) |
| Context window / hallucination risk | Context Budget (health) |
| Knowledge base (RAG) | Searchable KB articles → Snippets |
| Escalation to human | `escalate()` action |
| Prompt injection / social engineering | Adversarial tickets |
| Canned responses / tools | Macros (password_reset, refund) |
| SLA timers | Patience countdown per ticket |
| Triage / routing | Coworker consultation |

## Requirements

- Python 3.11+
- FastAPI, uvicorn, websockets
- (Optional) `google-genai` for Gemini-powered auto mode and LLM oracle
