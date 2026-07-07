# DataScout — Conversational Data Analysis Concierge Agent

**Track:** Concierge Agents
**Course:** Kaggle × Google — 5-Day AI Agents: Intensive Vibe Coding Course

## Problem

Exploratory data analysis involves a repetitive set of steps — checking summary stats,
looking for outliers, testing correlations, plotting distributions — that usually require
translating a question into pandas code every single time. DataScout removes that
translation step: you upload a CSV and talk to it in plain language.

## Solution

DataScout is a Streamlit-powered Web App that acts as a Gemini-backed conversational agent.
It exposes five real Python functions as tools via the Gemini API.
The model — not a hardcoded dispatcher — decides which tool to call based on the user's
question, executes it against a live pandas DataFrame in the backend, and reports the result back in
natural language.

## Architecture

```
                     ┌─────────────────────┐
                     │   User (Web UI)      │
                     └──────────┬───────────┘
                                │ CSV upload & natural language
                                ▼
                     ┌─────────────────────┐
                     │ st.session_state     │  ◄── Stateless UI workaround
                     │  (chat_history)      │      (context engineering)
                     └──────────┬───────────┘
                                ▼
         ┌───────────────────────────────────────────┐
         │              Gemini (function calling)      │
         │   system_instruction = SKILL.md content     │◄── Agent Skill &
         │                      + df.columns           │    Dynamic Context
         │   tools = [describe_data, detect_outliers,  │    
         │            run_correlation, plot_chart,     │
         │            modify_data]                     │
         └───────────────────┬───────────────────────────┘
                              │ Tool Execution Loop (app.py)
                              ▼
         ┌─────────────────────────────────────────────┐
         │                Tool execution                │
         │  describe_data / detect_outliers /           │
         │  run_correlation / plot_chart   → read-only  │
         │                                               │
         │  modify_data()  → SENSITIVE (mutates df)      │
         │      │                                         │
         │      ▼                                         │
         │  st.button() confirmation prompt              │◄── Security guardrail
         │  (human-in-the-loop via UI state)             │
         └─────────────────────┬─────────────────────────┘
                                ▼
                      ┌─────────────────────┐
                      │  session_memory{}    │  ◄── logs every tool call
                      └──────────┬───────────┘
                                 ▼
                      ┌─────────────────────┐
                      │  Natural-language    │
                      │  response to user     │
                      └─────────────────────┘
```

## Key Concepts Demonstrated (course requirement: 3+)

| Concept | Where | Details |
|---|---|---|
| **Security features** | Code (`modify_data`) & `SECURITY.md` | The only function able to mutate the dataset requires explicit Human-in-the-loop (HITL) confirmation via a UI button before executing. Enforcement lives in code, not just in the prompt. |
| **Agent Skills** | Code (`SKILL.md`) | Agent instructions live in a standalone `SKILL.md` file, loaded at runtime rather than hardcoded in Python — the same separation-of-concerns pattern for persistent skills. |
| **Deployability** | `DEPLOY.md` & Streamlit Cloud | The Gemini API key is never hardcoded; it's read from `st.secrets`, allowing the app to be safely deployed on Streamlit Cloud without leaking credentials. |

Also present: real tool use via Gemini automatic function calling (handled by a custom execution loop to support multi-turn reasoning), and dynamic Context Engineering (injecting columns via RAG-style prompt formatting).

## Documentation

- [SECURITY.md](./SECURITY.md) — Threat modeling (STRIDE) for the `modify_data` tool.
- [DEPLOY.md](./DEPLOY.md) — Step-by-step instructions to deploy the agent to Streamlit Cloud safely.
- [SKILL.md](./.agent/skills/datascout-analysis/SKILL.md) — The standalone persona definition.

## Setup Instructions

### Run locally

1. Ensure you have Python 3.9+ installed.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.streamlit/secrets.toml` file at the root of the project with your API key:
   ```toml
   GEMINI_API_KEY = "AIzaSy_YOUR_KEY_HERE"
   ```
4. Run the application:
   ```bash
   streamlit run app.py
   ```

### Deploy to Cloud
See [DEPLOY.md](./DEPLOY.md) for public deployment instructions on Streamlit Community Cloud.

## Limitations & Future Work

- Memory is session-scoped only; persistence across sessions using a database is a natural next step.
- Tool set is intentionally narrow (5 tools) to keep the demo legible within the hackathon timeframe.
- Single-agent design; a multi-agent extension (a cleaning agent handing off to this analysis agent) would exercise agent-to-agent interoperability directly.
