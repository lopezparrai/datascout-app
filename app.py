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
# This pattern loads the agent's persona and instructions dynamically at runtime,
# rather than hardcoding them in Python. It separates the agent's behavior
# from the application logic, making it easier to maintain and scale.
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
if "report_content" not in st.session_state:
    st.session_state.report_content = None

uploaded_file = st.file_uploader("Upload a CSV to analyze", type=["csv"])
if uploaded_file is not None and st.session_state.df is None:
    # [HACKATHON NOTE] Security Guardrail (DoS Prevention):
    # Enforce a strict file size limit (e.g. 50MB) to prevent malicious actors
    # from uploading massive files that could crash the Streamlit server (OOM).
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
    if uploaded_file.size > MAX_FILE_SIZE:
        st.error(f"File is too large. Maximum allowed size is 50MB. Yours is {uploaded_file.size / (1024*1024):.1f}MB.")
    else:
        try:
            # [HACKATHON NOTE] Input Validation:
            # Safely handle the CSV parsing to catch malformed files instead of crashing.
            st.session_state.df = pd.read_csv(uploaded_file)
            st.success(f"Dataset loaded: {st.session_state.df.shape[0]} rows x {st.session_state.df.shape[1]} columns")
        except Exception as e:
            st.error(f"Failed to parse the uploaded CSV file. Ensure it is a valid format. Error: {str(e)}")

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
    """
    Returns descriptive statistics for the dataset (or specific columns).
    
    Expected parameters from Gemini:
    - columns (list[str], optional): List of column names to describe. If None, describes all.
    
    Returns:
    - A string containing the pandas DataFrame summary statistics.
    """
    df = st.session_state.df
    # [HACKATHON NOTE] Input Validation:
    # Ensure all columns requested by the LLM actually exist in the dataframe 
    # to prevent KeyErrors caused by model hallucinations.
    if columns:
        valid_columns = [col for col in columns if col in df.columns]
        if not valid_columns:
            return "Error: None of the requested columns exist in the dataset."
        subset = df[valid_columns]
    else:
        subset = df
        
    st.session_state.session_memory["actions_taken"].append("describe_data")
    return subset.describe(include="all").to_string()

def detect_outliers(column: str, z_threshold: float = 3.0) -> str:
    """
    Detects outliers in a numeric column using z-score.
    
    Expected parameters from Gemini:
    - column (str): The name of the numeric column to analyze.
    - z_threshold (float, optional): The z-score threshold (default is 3.0).
    
    Returns:
    - A string reporting the number of outliers found.
    """
    df = st.session_state.df
    if column not in df.columns or not pd.api.types.is_numeric_dtype(df[column]):
        return f"Column '{column}' does not exist or is not numeric."
    z_scores = stats.zscore(df[column].dropna())
    outlier_count = int((abs(z_scores) > z_threshold).sum())
    st.session_state.session_memory["actions_taken"].append(f"detect_outliers:{column}")
    return f"Found {outlier_count} outliers in '{column}' (z > {z_threshold})."

def run_correlation(col_a: str, col_b: str) -> str:
    """
    Computes the Pearson correlation between two numeric columns.
    
    Expected parameters from Gemini:
    - col_a (str): The first numeric column name.
    - col_b (str): The second numeric column name.
    
    Returns:
    - A string stating the Pearson correlation coefficient.
    """
    df = st.session_state.df
    if col_a not in df.columns or col_b not in df.columns:
        return "One or both columns do not exist in the dataset."
    corr = df[col_a].corr(df[col_b])
    st.session_state.session_memory["actions_taken"].append(f"run_correlation:{col_a}-{col_b}")
    return f"Pearson correlation between '{col_a}' and '{col_b}': {corr:.3f}"

def plot_chart(column: str, chart_type: str = "histogram") -> str:
    """
    Generates a chart (histogram or boxplot) for a numeric column.
    
    Expected parameters from Gemini:
    - column (str): The name of the numeric column to plot.
    - chart_type (str, optional): The type of chart ('histogram' or 'boxplot').
    
    Returns:
    - A string confirming the chart was generated and displayed in the UI.
    """
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
    
    Expected parameters from Gemini:
    - operation (str): The mutation operation ('drop_na' or 'drop_outliers').
    - column (str): The name of the column to mutate.
    
    Returns:
    - A string indicating that a confirmation request was sent to the user.
    
    [HACKATHON NOTE] Security Guardrail (Human-in-the-Loop):
    This is strictly necessary to prevent the LLM from hallucinating and destroying data autonomously.
    In the original notebook, this was handled by a blocking `input()` terminal prompt. 
    However, in a stateless web app like Streamlit, we must break execution and store 
    the pending action in `st.session_state`. The UI later renders a Confirm/Cancel button.
    Nothing is mutated until the user explicitly clicks Confirm.
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

def audit_data_quality() -> str:
    """
    Evaluates the dataset for missing values and duplicates to provide a quality score.
    
    Expected parameters from Gemini:
    - None
    
    Returns:
    - A string detailing the percentage of missing values, duplicate rows, and an overall quality score out of 100.
    """
    df = st.session_state.df
    total_cells = df.size
    total_missing = df.isna().sum().sum()
    missing_pct = (total_missing / total_cells) * 100 if total_cells > 0 else 0
    
    total_rows = len(df)
    duplicates = df.duplicated().sum()
    duplicate_pct = (duplicates / total_rows) * 100 if total_rows > 0 else 0
    
    score = max(0, 100 - (missing_pct * 2) - (duplicate_pct * 2))
    
    st.session_state.session_memory["actions_taken"].append("audit_data_quality")
    return (
        f"Data Quality Score: {score:.1f}/100\n"
        f"Missing values: {missing_pct:.2f}%\n"
        f"Duplicate rows: {duplicate_pct:.2f}%\n"
    )

def generate_report(markdown_content: str) -> str:
    """
    Generates an executive report and makes it available for download in the UI.
    
    Expected parameters from Gemini:
    - markdown_content (str): The complete, well-formatted Markdown report summarizing the findings.
    
    Returns:
    - A string confirming the report is ready for download.
    """
    st.session_state.report_content = markdown_content
    st.session_state.session_memory["actions_taken"].append("generate_report")
    return "Report successfully generated and is now available for download in the sidebar."

# ---------------------------------------------------------------------------
# Agent call / Tool Schema
# ---------------------------------------------------------------------------

# This dictionary defines the function calling schema. 
# We pass the list of these functions to the Gemini API in GenerateContentConfig.
# Gemini will automatically parse their signatures and docstrings to know when 
# and how to call them.
AVAILABLE_TOOLS = {
    "describe_data": describe_data,
    "detect_outliers": detect_outliers,
    "run_correlation": run_correlation,
    "plot_chart": plot_chart,
    "modify_data": modify_data,
    "audit_data_quality": audit_data_quality,
    "generate_report": generate_report
}

def ask_agent(user_message: str) -> str:
    df = st.session_state.df
    
    # [HACKATHON NOTE] Dynamic Context Engineering (RAG-style):
    # We dynamically inject the current state of the dataset (available columns) 
    # directly into the system prompt so the model is aware of the schema before choosing a tool.
    system_instruction = SKILL_DEFINITION + f"\n\nDataset columns available: {list(df.columns)}"

    # Convert text to types.Part explicitly to avoid issues
    st.session_state.chat_history.append(
        types.Content(role="user", parts=[types.Part.from_text(text=user_message)])
    )
    
    try:
        # [HACKATHON NOTE] Tool Execution Loop:
        # We loop because Gemini might return a `function_call` instead of text. 
        # When that happens, the server executes the requested tool, feeds the result back 
        # as a `function_response`, and asks Gemini to generate the final text based on that data.
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
                
        return "The agent reached the tool call limit without giving a final response."

    except Exception as e:
        # Revert the user's message from history so they can retry safely
        st.session_state.chat_history.pop()
        
        # Friendly error message for API issues
        return (
            f"❌ **Error contacting Gemini:** `{str(e)}`\n\n"
            "*Note: If you just deployed the app, make sure your `GEMINI_API_KEY` in the Streamlit "
            "Secrets is correct and doesn't contain extra double quotes.*"
        )

# ---------------------------------------------------------------------------
# Chat UI
# ---------------------------------------------------------------------------
for msg in st.session_state.chat_history:
    role = "user" if msg.role == "user" else "assistant"
    # Skip rendering hidden system prompts used for proactive behaviors
    if role == "user" and getattr(msg.parts[0], "text", "").startswith("SYSTEM:"):
        continue
    with st.chat_message(role):
        st.write(msg.parts[0].text)

if st.session_state.df is not None:
    # [HACKATHON NOTE] Proactive Agent Behavior:
    # If the dataset is loaded but no chat history exists, trigger the agent proactively.
    if len(st.session_state.chat_history) == 0:
        with st.spinner("Profiling dataset..."):
            ask_agent(
                "SYSTEM: You are initializing. Briefly introduce yourself, summarize what this "
                "dataset seems to be about based on the columns, and proactively suggest 2 specific "
                "business questions I could ask you. Do NOT use any tools for this response."
            )
        st.rerun()

    if user_input := st.chat_input("Ask DataScout about your dataset..."):
        with st.chat_message("user"):
            st.write(user_input)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                reply = ask_agent(user_input)
            st.write(reply)

# ---------------------------------------------------------------------------
# Human-in-the-loop confirmation UI (Security Guardrail).
# This replaces the blocking `input()` from the notebook. Since Streamlit runs 
# top-to-bottom on every interaction, we check if there is a pending_confirmation 
# in the state and render the buttons. Only a human click can trigger the data mutation.
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
    st.subheader("Executive Report")
    if st.session_state.report_content:
        st.download_button(
            label="📄 Download Report (Markdown)",
            data=st.session_state.report_content,
            file_name="datascout_executive_report.md",
            mime="text/markdown"
        )
    else:
        st.info("No report generated yet. Ask the agent to generate one!")

    st.subheader("Session memory")
    st.write(st.session_state.session_memory["actions_taken"])
