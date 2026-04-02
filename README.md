# aip_spy_games

## Quick Start — Web App (Micro Mission)

### 1. Create a virtual environment

```bash
cd web
python -m venv .venv
```

### 2. Activate the virtual environment

macOS / Linux:
```bash
source .venv/bin/activate
```

Windows:
```bash
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Launch the server

```bash
python server.py
```

Open http://localhost:8000 in your browser.

### 5. Set up the Gemini API key

You can provide the API key in two ways:

- **From the web UI** (recommended): Paste your key into the "Gemini API Key" field in the System Prompt panel and click **Save**. The key is stored in your browser and re-sent automatically on reload.
- **From the terminal** (before launching): `export GEMINI_API_KEY=your-key` (macOS/Linux) or `set GEMINI_API_KEY=your-key` (Windows).

Without a Gemini API key, manual mode works with keyword-matched NPC responses. Auto mode requires the key for LLM calls.

## Jupyter Notebooks

The notebooks are in `agentic_ai_spy/`. To run them locally:

```bash
cd agentic_ai_spy
python -m venv .venv
source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
pip install jupyter
jupyter notebook
```
