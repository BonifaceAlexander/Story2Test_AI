import os
import json
import io
import streamlit as st
import pandas as pd

from openai import OpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
MODEL = "gpt-4o-mini"

def get_api_key():
    return st.session_state.get("openai_api_key") or OPENAI_API_KEY

def call_openai(prompt: str, model: str = MODEL):
    api_key = get_api_key()
    if not api_key:
        raise ValueError("API key not set.")

    client = OpenAI(api_key=api_key)
    
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a QA engineer who outputs JSON only."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=1000,
        temperature=0.0,
    )
    return resp.choices[0].message.content

def extract_json(text: str):
    try:
        return json.loads(text)
    except:
        import re
        m = re.search(r'(\{.*\})', text, re.S)
        if m:
            try:
                return json.loads(m.group(1))
            except:
                pass
    return {"raw_text": text}

PROMPT = """
I will provide acceptance criteria. Produce JSON:
{{
 "positive": [...],
 "negative": [...]
}}
Each test has: id, title, preconditions, steps, expected_result, priority.
Generate 3-6 positive and 3-6 negative tests. JSON only.

Acceptance Criteria:
{ac}
"""

# Set page config at the very beginning
st.set_page_config(
    page_title="Story2Test AI",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .stApp header {visibility: hidden;}
    .main .block-container {padding-top: 2rem;}
    
    /* Button Styling */
    .stButton > button {
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        border: none;
    }
    .stButton > button:hover {
        background-color: #45a049;
        color: white;
        border: none;
    }

    /* Headlines */
    h1 {
        color: #2E86C1;
        font-family: 'Segoe UI', sans-serif;
    }
    h3 {
        color: #555;
    }
</style>
""", unsafe_allow_html=True)

st.title("🧪 Story2Test AI")
st.markdown("### Transform Acceptance Criteria into Comprehensive Test Scenarios")

with st.sidebar:
    st.header("Configuration")
    st.subheader("Test Case Generator")
    key_input = st.text_input("OpenAI API Key", type="password", help="Enter your OpenAI API Key here")
    if key_input:
        st.session_state["openai_api_key"] = key_input
        st.success("✅ API key loaded")
    
    st.markdown("---")

col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.subheader("1. Input Acceptance Criteria")
    ac = st.text_area(
        "Paste your User Story or Acceptance Criteria here:",
        height=300,
        placeholder="Example:\nUser must be able to login with valid email and password.\nPassword must be at least 8 characters...",
        help="The more detailed the criteria, the better the test cases."
    )
    
    generate_btn = st.button("🚀 Generate Test Cases", use_container_width=True)

with col2:
    st.subheader("2. Review Generated Tests")
    
    if generate_btn:
        if not get_api_key():
            st.error("⚠️ Please enter an API key in the sidebar first.")
            st.stop()

        if not ac:
            st.warning("⚠️ Please enter some acceptance criteria first.")
            st.stop()
            
        with st.spinner("🤖 Analyzing requirements & generating logical test scenarios..."):
            prompt = PROMPT.format(ac=ac)
            try:
                raw = call_openai(prompt)
            except Exception as e:
                st.error(f"Error: {e}")
                st.stop()

            parsed = extract_json(raw)

            if "positive" not in parsed and "negative" not in parsed:
                st.error("Could not parse JSON output. Please try again.")
                with st.expander("View Raw Output"):
                    st.text(raw)
                st.stop()

            pos = parsed.get("positive", [])
            neg = parsed.get("negative", [])

            # Helper to create DF
            def to_df(items, kind):
                rows = []
                for t in items:
                    rows.append({
                        "Type": kind,  # Capitalized for display
                        "ID": t.get("id", ""),
                        "Title": t.get("title", ""),
                        "Preconditions": t.get("preconditions", ""),
                        "Steps": "\n".join(t.get("steps", [])),
                        "Expected Result": t.get("expected_result", ""),
                        "Priority": t.get("priority", "Medium") # Default to Medium
                    })
                return pd.DataFrame(rows)

            df_pos = to_df(pos, "Positive")
            df_neg = to_df(neg, "Negative")
            
            # Master DataFrame
            df_all = pd.concat([df_pos, df_neg], ignore_index=True)
            
            # Store in session state to persist after rerun (if we added other interactions)
            st.session_state['last_results'] = df_all
            st.success(f"✅ Generated {len(pos)} positive and {len(neg)} negative test cases!")

    # Display results if they exist
    if 'last_results' in st.session_state:
        results_df = st.session_state['last_results']
        
        tab1, tab2, tab3 = st.tabs(["📋 All Tests", "✅ Positive Scenarios", "❌ Negative Scenarios"])
        
        # Column configuration for professional table
        column_config = {
            "Priority": st.column_config.SelectboxColumn(
                "Priority",
                help="Test Case Priority",
                width="small",
                options=["High", "Medium", "Low"],
                required=True,
            ),
            "Type": st.column_config.TextColumn("Type", width="small"),
            "Steps": st.column_config.TextColumn("Steps", width="large"),
            "Title": st.column_config.TextColumn("Title", width="medium"),
        }

        def style_priority(val):
            color = 'white'
            if val == 'High': color = '#ffcccb' # Light red
            elif val == 'Medium': color = '#ffe5cc' # Light orange
            elif val == 'Low': color = '#ccffcc' # Light green
            return f'background-color: {color}; color: black; border-radius: 4px; padding: 2px;'

        with tab1:
            st.dataframe(
                results_df, 
                use_container_width=True, 
                column_config=column_config,
                hide_index=True
            )
        
        with tab2:
            st.dataframe(
                results_df[results_df["Type"] == "Positive"],
                use_container_width=True,
                column_config=column_config,
                hide_index=True
            )
            
        with tab3:
            st.dataframe(
                results_df[results_df["Type"] == "Negative"],
                use_container_width=True,
                column_config=column_config,
                hide_index=True
            )

        st.markdown("---")
        d_col1, d_col2 = st.columns(2)
        
        # Prepare downloads
        csv = results_df.to_csv(index=False).encode("utf-8")
        
        excel_buf = io.BytesIO()
        with pd.ExcelWriter(excel_buf, engine="xlsxwriter") as w:
            results_df.to_excel(w, index=False, sheet_name="TestCases")
            # Auto-adjust columns width
            worksheet = w.sheets['TestCases']
            for i, col in enumerate(results_df.columns):
                column_len = max(results_df[col].astype(str).map(len).max(), len(col)) + 2
                worksheet.set_column(i, i, column_len)
        excel_buf.seek(0)
        
        with d_col1:
            st.download_button(
                "📄 Download CSV", 
                csv, 
                "story2test_cases.csv", 
                "text/csv", 
                use_container_width=True
            )
        with d_col2:
            st.download_button(
                "📊 Download Excel", 
                excel_buf, 
                "story2test_cases.xlsx", 
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
                use_container_width=True
            )
