# Security Architecture & Threat Model

This document outlines the security measures implemented in the DataScout application. As an AI Agent that executes Python code in the backend, strict guardrails are necessary to prevent malicious activities, data corruption, and system abuse. 

We have designed our defenses across four main pillars to ensure safe deployment on public cloud infrastructure (e.g., Streamlit Community Cloud).

---

## 1. Secrets Management (Authentication Security)
**Risk:** Exposing the Gemini API Key would allow attackers to consume our billing quota or impersonate the application.
**Mitigation:** 
- The API key is **never hardcoded** in the source code.
- The project relies on Streamlit's native Secrets Manager (`st.secrets["GEMINI_API_KEY"]`). 
- A comprehensive `.gitignore` ensures that local `.env` or `secrets.toml` files are never accidentally committed to the GitHub repository.

## 2. Safe Tool Execution (Injection Prevention)
**Risk:** When connecting an LLM to a backend, there is a severe risk of Prompt Injection leading to Remote Code Execution (RCE) if the agent is allowed to write and execute arbitrary Python code via `eval()` or `exec()`.
**Mitigation:**
- **No dynamic execution:** The application completely avoids `eval()`, `exec()`, or any arbitrary code execution engines.
- **Strict Allowlisting:** The LLM does not write code. Instead, it is constrained to a strictly defined JSON schema (Function Calling). The backend maps these JSON requests to predefined, safe Python functions (`describe_data`, `detect_outliers`, etc.).
- **Input Validation:** Tools like `describe_data` actively sanitize the inputs requested by the LLM. If the LLM hallucinates and requests a non-existent column, the tool catches the error and rejects the execution, preventing internal `KeyError` crashes.

## 3. Data Mutation Guardrails (Human-in-the-Loop)
**Risk:** The agent might hallucinate a reason to delete or alter data, or a malicious user might attempt to prompt-inject the agent to corrupt the dataset.
**Mitigation:**
- We categorize data mutations into **Additive** (e.g. `calculate_kpi` adding a new derived column) and **Destructive** (e.g. `modify_data` dropping rows or columns).
- Additive operations are permitted to run autonomously to preserve conversational fluidity. If a column is overwritten, the tool explicitly warns the LLM so it can inform the user transparently.
- Destructive operations (`modify_data`) require strict explicit authorization via a **Human-in-the-Loop (HITL)** pattern. When the agent attempts a destructive action, the execution loop is instantly paused.
- The application stores the intent in a stateless session (`st.session_state`) and renders an explicit `Confirm / Cancel` button in the UI. 
- The data is never destructively altered unless a physical human click is detected on the server. This control is hardcoded in the execution layer (Python), making it impervious to prompt injection bypasses.

## 4. Denial of Service (DoS) Prevention
**Risk:** A malicious actor could upload an extremely large or corrupted CSV file to exhaust the server's RAM (OOM - Out of Memory) or crash the application.
**Mitigation:**
- **File Size Limits:** The file uploader strictly enforces a maximum size limit (e.g., 50MB) before attempting to read the file into memory.
- **Parse Validation:** The `pd.read_csv` function is wrapped in a secure `try/except` block. If the file is malformed, the application catches the `ParserError` and displays a clean error message to the user, keeping the server stable.
