# aip_spy_games

## Web App (Micro Mission)

```
cd web
pip install -r requirements.txt
export GEMINI_API_KEY=your-key   # optional: enables LLM-powered NPCs
python server.py
# Open http://localhost:8000
```

Without `GEMINI_API_KEY`, manual mode works with keyword-matched NPC responses.
Auto mode requires the API key for LLM calls.