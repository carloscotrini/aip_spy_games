# The Hidden Layer — An Agentic AI Infiltration Exercise

A spy-themed coding exercise where students build an LLM-powered AI agent that
infiltrates a military base on the fictional Isla Perdida.

Students implement `think_llm()` — a function that uses the Gemini API to
reason about the game state, interpret informant clues, and decide actions.

## Quick start

```bash
pip install -r requirements.txt
```

Open the student notebook and follow the instructions inside.

## Game overview

You are **Agent Lambda**, inserted on the south shore of Isla Perdida.  Your
mission: recover **10 classified dossiers** from the OVERFIT Corporation base.
Navigate the 8x8 base grid, talk to informants, gather materials,
craft weapons, and defeat the two robots guarding the most sensitive files.

## Structure

```
hidden_layer/       Core game engine (do NOT modify)
  operative.py      Operative (player) state
  game_world.py     Map, cells, NPCs, facilities
  tools.py          9 agent tools
  agent.py          Agent loop + think_llm stub (students edit this)
  oracle.py         Informant dialogue (LLM-powered)
  display.py        Notebook visualization
  interactive.py    Interactive play mode
  main.py           Game runner convenience functions
```
