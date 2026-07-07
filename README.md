# DataScout — Conversational Data Analysis Concierge Agent

**Track:** Concierge Agents
**Course:** Kaggle × Google — 5-Day AI Agents: Intensive Vibe Coding Course

## Problem

Exploratory data analysis involves a repetitive set of steps — checking summary stats,
looking for outliers, testing correlations, plotting distributions — that usually require
translating a question into pandas code every single time. DataScout removes that
translation step: you upload a CSV and talk to it in plain language.

## Solution

DataScout is a Gemini-powered agent that exposes five real Python functions as tools.
The model — not a hardcoded dispatcher — decides which tool to call based on the user's
question, executes it against a live pandas DataFrame, and reports the result back in
natural language.

## Architecture

```
                     ┌─────────────────────┐
                     │   User (chat input)  │
                     └──────────┬───────────┘
                                │ natural language question
                                ▼
                     ┌─────────────────────┐
                     │   chat_history[]     │  ◄── conversational memory
                     │  (full turn history) │      (context engineering)
                     └──────────┬───────────┘
                                ▼
        ┌───────────────────────────────────────────┐
        │              Gemini (function calling)      │
        │   system_instruction = SKILL.md content      │◄── Agent Skill
        │   tools = [describe_data, detect_outliers,   │    (Day 3 pattern)
        │            run_correlation, plot_chart,      │
        │            modify_data]                      │
        └───────────────────┬───────────────────────────┘
                             │ decides which tool + args
                             ▼
        ┌─────────────────────────────────────────────┐
        │                Tool execution                │
        │  describe_data / detect_outliers /            │
        │  run_correlation / plot_chart   → read-only   │
        │                                                │
        │  modify_data()  → SENSITIVE (mutates df)       │
        │      │                                          │
        │      ▼                                          │
        │  input() confirmation prompt                    │◄── Security guardrail
        │  (human-in-the-loop, Day 4 pattern)             │
        └─────────────────────┬─────────────────────────┘
                               ▼
                     ┌─────────────────────┐
                     │  session_memory{}    │  ◄── logs every tool call
                     └──────────┬───────────┘
                                ▼
                     ┌─────────────────────┐
                     │  Natural-language     │
                     │  response to user      │
                     └─────────────────────┘
```

## Key Concepts Demonstrated (course requirement: 3+)

| Concept | Where | Details |
|---|---|---|
| **Security features** | Code (`modify_data`) | The only function able to mutate the dataset requires an explicit `input()` confirmation before executing. Enforcement lives in code, not just in the prompt, so it holds even if the model's reasoning were wrong. |
| **Agent Skills** | Code (`SKILL.md` + loader cell) | Agent instructions live in a standalone `SKILL.md` file, loaded at runtime rather than hardcoded in Python — the same separation-of-concerns pattern the course teaches for persistent, portable skills. |
| **Deployability** | Video + Code | The Gemini API key is never hardcoded; it's read from Colab's Secrets manager (`google.colab.userdata`), so the notebook can be shared and run publicly without leaking credentials. |

Also present, though not counted toward the required 3: real tool use via Gemini automatic
function calling, and session-scoped context/memory (`chat_history`, `session_memory`).

## Setup Instructions

1. Open `DataScout_Agent.ipynb` in [Google Colab](https://colab.research.google.com) (upload the file, or File → Open notebook → Upload).
2. In Colab, open the **Secrets** panel (🔑 icon, left sidebar).
3. Create a secret named `GEMINI_API_KEY` with your key from [Google AI Studio](https://aistudio.google.com/apikey), and enable "Notebook access."
4. Run the cells top to bottom.
5. When prompted, upload:
   - Your dataset (any `.csv` file).
   - The `SKILL.md` file included in this repo (defines the agent's behavior).
6. Use `ask_agent("your question here")` to interact with DataScout.

**No API key or credential is stored anywhere in this repository.**

## Repository Contents

- `DataScout_Agent.ipynb` — the agent notebook (run in Colab).
- `SKILL.md` — the agent's skill/instruction definition, loaded at runtime.
- `README.md` — this file.

## Limitations & Future Work

- Memory is session-scoped only (resets when the Colab runtime restarts); persistence
  across sessions is a natural next step.
- Tool set is intentionally narrow (5 tools) to keep the demo legible within the
  hackathon timeframe — hypothesis testing, categorical analysis, and report export
  are logical additions.
- Single-agent design; a multi-agent extension (a cleaning agent handing off to this
  analysis agent) would exercise agent-to-agent interoperability directly.
