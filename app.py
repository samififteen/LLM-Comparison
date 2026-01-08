import streamlit as st
import pandas as pd
import time
import os

from dotenv import load_dotenv
load_dotenv()

try:
    from auth import login
    from utils.router import choose_models
    from utils.parallel import run_parallel
    from utils.rate_limiter import check_limit
    from utils.report import generate_report
except Exception as e:
    st.error(e)
    st.stop()


# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="LLM Nexus | Enterprise AI Router",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ---------------- CUSTOM UI ----------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* App Background */
.stApp {
    background: radial-gradient(circle at top left, #0f172a, #020617);
    color: #e5e7eb;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #020617, #0f172a);
    border-right: 1px solid #1e293b;
}

/* Headings */
.main-title {
    font-size: 3rem;
    font-weight: 800;
    background: linear-gradient(90deg, #38bdf8, #22d3ee);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.subtitle {
    color: #94a3b8;
    margin-bottom: 2rem;
}

/* Glass Card */
.glass {
    background: rgba(15, 23, 42, 0.6);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(148, 163, 184, 0.15);
    border-radius: 16px;
    padding: 20px;
}

/* Inputs */
.stTextArea textarea,
div[data-baseweb="select"] > div {
    background-color: #020617;
    border-radius: 12px;
    border: 1px solid #1e293b;
    color: #e5e7eb;
}

/* Button */
div.stButton > button {
    background: linear-gradient(90deg, #38bdf8, #22d3ee);
    color: #020617;
    border-radius: 12px;
    padding: 0.8rem;
    font-weight: 700;
    width: 100%;
    border: none;
}

div.stButton > button:hover {
    box-shadow: 0 0 20px rgba(56, 189, 248, 0.6);
    transform: translateY(-1px);
}

/* Chat bubble */
.chat-box {
    background: rgba(2, 6, 23, 0.85);
    border-radius: 14px;
    padding: 16px;
    margin-top: 12px;
    border-left: 4px solid #38bdf8;
}

.model-badge {
    font-size: 0.75rem;
    color: #38bdf8;
    font-weight: 700;
    letter-spacing: 1px;
}

/* Metrics */
div[data-testid="metric-container"] {
    background: rgba(15, 23, 42, 0.7);
    border-radius: 14px;
    padding: 14px;
    border: 1px solid #1e293b;
}
</style>
""", unsafe_allow_html=True)


# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.title("⚙️ Controls")

    if "user" in st.session_state:
        st.info(f"👤 Logged in as **{st.session_state.user}**")

    st.markdown("---")

    st.subheader("Configuration")
    model_temp = st.slider("Creativity (Temperature)", 0.0, 1.0, 0.7)
    max_tokens = st.number_input("Max Tokens", value=1024, step=256)

    st.markdown("---")
    st.caption("v3.0.0 | LLM Nexus Enterprise")


# ---------------- MAIN APP ----------------
def main():
    login()
    if "user" not in st.session_state:
        st.stop()

    st.markdown('<div class="main-title">LLM Nexus</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subtitle">Enterprise-grade AI routing, benchmarking & cost intelligence.</div>',
        unsafe_allow_html=True
    )

    col1, col2 = st.columns([1, 3])

    with col1:
        st.markdown('<div class="glass">', unsafe_allow_html=True)
        task = st.selectbox(
            "🎯 Target Objective",
            ["General", "Coding", "Fast Response", "Cost Saving"]
        )
        st.metric("Active Models", "3 Online", "Stable")
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="glass">', unsafe_allow_html=True)
        prompt = st.text_area(
            "💬 Enter your prompt",
            height=160,
            placeholder="Ask anything..."
        )
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    run_btn = st.button("⚡ Execute Query")

    if run_btn:
        if not check_limit(st.session_state.user):
            st.error("🚫 Rate limit exceeded.")
            st.stop()

        if not prompt.strip():
            st.warning("⚠️ Please enter a prompt.")
            st.stop()

        with st.status("🔄 Processing request...", expanded=True):
            models = choose_models(task)
            start = time.time()
            responses = run_parallel(prompt, models)
            elapsed = round(time.time() - start, 2)

        st.markdown("## 📊 Results")

        tab1, tab2, tab3, tab4 = st.tabs([
            "💬 Model Responses",
            "🧾 Raw Output",
            "💰 Cost Report",
            "📈 Performance"
        ])

        with tab1:
            for model_name, response in responses.items():
                st.markdown(f"""
                <div class="chat-box">
                    <div class="model-badge">{model_name}</div>
                    <br>
                    {response}
                </div>
                """, unsafe_allow_html=True)

        with tab2:
            st.json(responses)

        with tab3:
            generate_report(prompt, responses)
            col_a, col_b = st.columns(2)
            col_a.metric("Estimated Cost", "$0.0042", "-12%")
            col_b.metric("Avg Latency", f"{elapsed}s", "Fast")

        with tab4:
            metrics_file = "data/metrics/metrics.csv"
            if not os.path.exists(metrics_file):
                st.warning("No performance data available.")
            else:
                df = pd.read_csv(metrics_file)
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")

                st.subheader("⏱ Avg Latency per Model")
                st.bar_chart(df.groupby("model")["latency"].mean())

                st.subheader("📏 Avg Response Length")
                st.bar_chart(df.groupby("model")["response_length"].mean())

                st.subheader("📊 Requests Over Time")
                st.line_chart(
                    df.set_index("timestamp")
                    .resample("1min")
                    .count()["model"]
                )


if __name__ == "__main__":
    main()