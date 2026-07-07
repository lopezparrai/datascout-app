"""
DataScout — Streamlit web app version.

Reuses the same agent logic as the Colab notebook (5 tools + Gemini function
calling + human-in-the-loop guardrail + SKILL.md-based instructions), wrapped
in a Streamlit chat UI for public deployment.

SECURITY NOTE: the Gemini API key is read from Streamlit secrets
(st.secrets["GEMINI_API_KEY"]), configured in the Streamlit Cloud dashboard —
never hardcoded here, never committed to the repo.
"""

import streamlit as st
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
from google import genai
from google.genai import types

st.set_page_config(page_title="DataScout", page_icon="🔎")
st.title("🔎 DataScout — Conversational Data Analysis Agent")
st.caption("Concierge Agents track — Kaggle x Google AI Agents Intensive Vibe Coding Course")

# ---------------------------------------------------------------------------
# Client setup — key comes from Streamlit secrets, never from source code.
# ---------------------------------------------------------------------------
if "GEMINI_API_KEY" not in st.secrets:
    st.error(
        "GEMINI_API_KEY is not configured. Add it in your Streamlit Cloud app's "
        "Settings → Secrets as: GEMINI_API_KEY = \"your_key_here\""
    )
    st.stop()

client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
MODEL = "gemini-2.5-flash"

# ---------------------------------------------------------------------------
# Load the agent Skill (SKILL.md) — same Agent Skills pattern as the notebook.
# ---------------------------------------------------------------------------
with open(".agent/skills/datascout-analysis/SKILL.md", "r", encoding="utf-8") as f:
    SKILL_DEFINITION = f.read()

# ---------------------------------------------------------------------------
# Session state: dataset, memory, chat history — all scoped to this browser
# session, never persisted server-side (no user data storage).
# ---------------------------------------------------------------------------
if "df" not in st.session_state:
    st.session_state.df = None
if "session_memory" not in st.session_state:
    st.session_state.session_memory = {"actions_taken": []}
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "pending_confirmation" not in st.session_state:
    st.session_state.pending_confirmation = None  # holds a pending sensitive action

uploaded_file = st.file_uploader("Upload a CSV to analyze", type=["csv"])
if uploaded_file is not None and st.session_state.df is None:
    st.session_state.df = pd.read_csv(uploaded_file)
    st.success(f"Dataset loaded: {st.session_state.df.shape[0]} rows x {st.session_state.df.shape[1]} columns")

if st.session_state.df is not None:
    st.dataframe(st.session_state.df.head())

# ---------------------------------------------------------------------------
# Tools — identical logic to the notebook version. Only difference: modify_data
# cannot use input() in a web app, so the human-in-the-loop confirmation is
# implemented via a Streamlit button instead of a blocking terminal prompt.
# The security property is the same: no mutation happens without an explicit,
# separate human action.
# ---------------------------------------------------------------------------

def describe_data(columns: list[str] = None) -> str:
    """Returns descriptive statistics for the dataset (or specific columns)."""
    df = st.session_state.df
    subset = df[columns] if columns else df
    st.session_state.session_memory["actions_taken"].append("describe_data")
    return subset.describe(include="all").to_string()

def detect_outliers(column: str, z_threshold: float = 3.0) -> str:
    """Detects outliers in a numeric column using z-score."""
    df = st.session_state.df
    if column not in df.columns or not pd.api.types.is_numeric_dtype(df[column]):
        return f"Column '{column}' does not exist or is not numeric."
    z_scores = stats.zscore(df[column].dropna())
    outlier_count = int((abs(z_scores) > z_threshold).sum())
    st.session_state.session_memory["actions_taken"].append(f"detect_outliers:{column}")
    return f"Found {outlier_count} outliers in '{column}' (z > {z_threshold})."

def run_correlation(col_a: str, col_b: str) -> str:
    """Computes the Pearson correlation between two numeric columns."""
    df = st.session_state.df
    if col_a not in df.columns or col_b not in df.columns:
        return "One or both columns do not exist in the dataset."
    corr = df[col_a].corr(df[col_b])
    st.session_state.session_memory["actions_taken"].append(f"run_correlation:{col_a}-{col_b}")
    return f"Pearson correlation between '{col_a}' and '{col_b}': {corr:.3f}"

def plot_chart(column: str, chart_type: str = "histogram") -> str:
    """Generates a chart (histogram or boxplot) for a numeric column."""
    df = st.session_state.df
    if column not in df.columns:
        return f"Column '{column}' does not exist."
    fig, ax = plt.subplots(figsize=(6, 4))
    if chart_type == "boxplot":
        ax.boxplot(df[column].dropna())
    else:
        ax.hist(df[column].dropna(), bins=30)
    ax.set_title(f"{chart_type} of {column}")
    st.pyplot(fig)
    st.session_state.session_memory["actions_taken"].append(f"plot_chart:{column}")
    return f"Chart ({chart_type}) of '{column}' generated and displayed above."

def modify_data(operation: str, column: str) -> str:
    """
    SENSITIVE ACTION: modifies the dataset (e.g. dropping nulls or outliers).
    In this web version, instead of blocking on input(), the request is queued
    in st.session_state.pending_confirmation and rendered as an explicit
    Confirm/Cancel button in the UI. Nothing is mutated until the user clicks
    Confirm — same guardrail property as the notebook, adapted to a non-blocking
    UI context.
    """
    df = st.session_state.df
    if column not in df.columns:
        return f"Column '{column}' does not exist in the dataset. Available columns: {list(df.columns)}"
    if operation == "drop_outliers" and not pd.api.types.is_numeric_dtype(df[column]):
        return f"Column '{column}' is not numeric, cannot compute outliers on it."

    st.session_state.pending_confirmation = {"operation": operation, "column": column}
    return (
        f"I'd like to run '{operation}' on column '{column}'. "
        f"Please confirm using the button below before I proceed."
    )

# ---------------------------------------------------------------------------
# Agent call
# ---------------------------------------------------------------------------

AVAILABLE_TOOLS = {
    "describe_data": describe_data,
    "detect_outliers": detect_outliers,
    "run_correlation": run_correlation,
    "plot_chart": plot_chart,
    "modify_data": modify_data
}

def ask_agent(user_message: str) -> str:
    df = st.session_state.df
    system_instruction = SKILL_DEFINITION + f"\n\nDataset columns available: {list(df.columns)}"

    # Convert text to types.Part explicitly to avoid issues
    st.session_state.chat_history.append(
        types.Content(role="user", parts=[types.Part.from_text(text=user_message)])
    )
    
    try:
        # Loop to handle function calls automatically
        MAX_TURNS = 4
        for _ in range(MAX_TURNS):
            response = client.models.generate_content(
                model=MODEL,
                contents=st.session_state.chat_history,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    tools=list(AVAILABLE_TOOLS.values()),
                ),
            )
            
            if response.function_calls:
                # 1. Append model's tool call to history
                st.session_state.chat_history.append(response.candidates[0].content)
                
                # 2. Execute tools and collect responses
                function_responses = []
                for fc in response.function_calls:
                    if fc.name in AVAILABLE_TOOLS:
                        func = AVAILABLE_TOOLS[fc.name]
                        kwargs = {k: v for k, v in fc.args.items()} if fc.args else {}
                        try:
                            result_str = str(func(**kwargs))
                        except Exception as e:
                            result_str = f"Error executing tool: {str(e)}"
                    else:
                        result_str = "Error: Tool not found"
                        
                    function_responses.append(
                        types.Part.from_function_response(
                            name=fc.name,
                            response={"result": result_str}
                        )
                    )
                
                # 3. Append tool responses as 'user' role
                st.session_state.chat_history.append(
                    types.Content(role="user", parts=function_responses)
                )
                # Continue loop so Gemini can answer using the tool results
                
            else:
                # Normal text response
                st.session_state.chat_history.append(
                    types.Content(role="model", parts=[types.Part.from_text(text=response.text or "")])
                )
                return response.text
                
        return "El agente alcanzó el límite de llamadas a herramientas sin dar una respuesta final."

    except Exception as e:
        # Revert the user's message from history so they can retry safely
        st.session_state.chat_history.pop()
        
        # Friendly error message for API issues
        return (
            f"❌ **Error al contactar a Gemini:** `{str(e)}`\n\n"
            "*Nota: Si acabas de desplegar la app, asegúrate de que tu `GEMINI_API_KEY` en los Secrets "
            "de Streamlit esté correcta y no tenga comillas dobles extra.*"
        )

# ---------------------------------------------------------------------------
# Chat UI
# ---------------------------------------------------------------------------
for msg in st.session_state.chat_history:
    role = "user" if msg.role == "user" else "assistant"
    with st.chat_message(role):
        st.write(msg.parts[0].text)

if st.session_state.df is not None:
    if user_input := st.chat_input("Ask DataScout about your dataset..."):
        with st.chat_message("user"):
            st.write(user_input)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                reply = ask_agent(user_input)
            st.write(reply)

# ---------------------------------------------------------------------------
# Human-in-the-loop confirmation UI (security guardrail, rendered as buttons
# instead of a blocking terminal input() call).
# ---------------------------------------------------------------------------
if st.session_state.pending_confirmation:
    action = st.session_state.pending_confirmation
    st.warning(f"⚠️ Confirm: run **{action['operation']}** on column **{action['column']}**?")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Confirm"):
            df = st.session_state.df
            if action["operation"] == "drop_na":
                before = len(df)
                df = df.dropna(subset=[action["column"]])
                st.session_state.df = df
                st.success(f"Dropped {before - len(df)} rows with nulls in '{action['column']}'.")
            elif action["operation"] == "drop_outliers":
                z_scores = stats.zscore(df[action["column"]].dropna())
                mask = abs(z_scores) <= 3
                before = len(df)
                df = df[df[action["column"]].isin(df[action["column"]].dropna()[mask])]
                st.session_state.df = df
                st.success(f"Dropped {before - len(df)} outliers from '{action['column']}'.")
            st.session_state.session_memory["actions_taken"].append(
                f"modify_data:{action['operation']}:{action['column']}"
            )
            st.session_state.pending_confirmation = None
            st.rerun()
    with col2:
        if st.button("❌ Cancel"):
            st.session_state.pending_confirmation = None
            st.info("Operation cancelled.")
            st.rerun()

with st.sidebar:
    st.subheader("Session memory")
    st.write(st.session_state.session_memory["actions_taken"])
