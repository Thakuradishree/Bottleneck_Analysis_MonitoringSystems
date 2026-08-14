import tempfile
from pathlib import Path

import streamlit as st

from parser.log_parser import LogParser
from parser.session_builder import SessionBuilder
from parser.journey_extractor import JourneyExtractor

from dashboard.k6_txt_parser import parse_k6_output
from dashboard.telemetry import (
    estimate_telemetry_from_metrics,
    normalize_real_telemetry,
)
from dashboard.dashboard import render_dashboard

from llm.llm import generate_k6_script
from utils.script_exporter import save_script
from utils.k6_runner import run_k6_script, k6_binary_available
from utils.theme import inject_theme, page_header, pipeline_stepper


# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="PulseAI",
    layout="wide",
)

inject_theme()

STAGES = [
    "1. Upload Logs",
    "2. Journeys",
    "3. Generate Script",
    "4. Execute Test",
    "5. Dashboard",
]

# =====================================================
# SESSION STATE
#
# Everything computed in one step is cached here so moving between
# steps in the sidebar never forces the user to re-upload a file or
# redo work that was already done in this session.
# =====================================================

defaults = {
    "df": None,
    "stats": None,
    "session_df": None,
    "sessions": None,
    "top_journeys": None,
    "journey_json": None,
    "k6_script": None,
    "k6_metrics": None,
    "k6_telemetry": None,
    "k6_raw_output": None,
    "active_stage": STAGES[0],
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# =====================================================
# SIDEBAR — NAVIGATION + PIPELINE STATUS
# =====================================================

with st.sidebar:
    st.markdown("## 🚀 PulseAI")
    
    st.divider()

    completed = {
        STAGES[0]: st.session_state.df is not None,
        STAGES[1]: st.session_state.top_journeys is not None,
        STAGES[2]: st.session_state.k6_script is not None,
        STAGES[3]: st.session_state.k6_metrics is not None,
        STAGES[4]: st.session_state.k6_metrics is not None,
    }

    st.session_state.active_stage = st.radio(
        "Pipeline",
        STAGES,
        index=STAGES.index(st.session_state.active_stage),
        label_visibility="collapsed",
    )

    st.divider()
    st.markdown("**Progress**")
    for stage in STAGES:
        icon = "✅" if completed[stage] else "⬜"
        st.caption(f"{icon} {stage}")

    st.divider()
    if st.button("🔄 Reset pipeline", use_container_width=True):
        for key, value in defaults.items():
            if key != "active_stage":
                st.session_state[key] = value
        st.rerun()


current_index = STAGES.index(st.session_state.active_stage)
page_header(
    "PulseAI — Performance Engineering Assistant",
    "Application logs → real user journeys → k6 load test → bottleneck diagnosis, "
    "in one pipeline.",
)
pipeline_stepper(STAGES, current_index)
st.write("")


# =====================================================
# STAGE 1 — UPLOAD & PARSE LOGS
# =====================================================

if st.session_state.active_stage == STAGES[0]:

    st.subheader("📤 Upload Application Logs")

    uploaded_file = st.file_uploader(
        "Upload Application Logs (.csv)",
        type=["csv"],
        key="application_logs",
    )

    if uploaded_file is not None:
        parser = LogParser()
        df = parser.read_logs(uploaded_file)

        if df is not None:
            if parser.validate_schema():
                parser.clean_logs()
                st.session_state.df = parser.df
                st.session_state.stats = parser.get_statistics()
                st.success("Logs parsed successfully ✅")
            else:
                st.error("❌ Invalid log file schema.")

    if st.session_state.df is not None:
        stats = st.session_state.stats

        st.divider()
        st.subheader("📊 Dataset Statistics")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Logs", stats["Total Logs"])
        c2.metric("Sessions", stats["Unique Sessions"])
        c3.metric("Users", stats["Unique Users"])
        c4.metric("Avg Response", f"{stats['Average Response Time (ms)']} ms")

        c5, c6, c7 = st.columns(3)
        c5.metric("Modules", stats["Modules"])
        c6.metric("Endpoints", stats["Endpoints"])
        c7.metric("Errors", stats["Error Requests"])

        st.divider()
        st.subheader("📄 Uploaded Logs (preview)")
        st.dataframe(st.session_state.df.head(20), use_container_width=True)

        st.divider()
        if st.button("Continue to Journey Extraction →", type="primary"):
            st.session_state.active_stage = STAGES[1]
            st.rerun()
    else:
        st.info("Upload a CSV with columns: timestamp, session_id, user_id, "
                 "persona, module, endpoint, method, status_code, response_time_ms.")


# =====================================================
# STAGE 2 — SESSIONS & JOURNEYS
# =====================================================

elif st.session_state.active_stage == STAGES[1]:

    if st.session_state.df is None:
        st.warning("⚠️ Upload logs first (Step 1).")
    else:
        st.subheader("🔄 Session Reconstruction")

        builder = SessionBuilder(st.session_state.df)
        sessions = builder.build_sessions()
        session_df = builder.sessions_dataframe(sessions)

        st.session_state.sessions = sessions
        st.session_state.session_df = session_df

        st.metric("Sessions Reconstructed", len(session_df))
        st.dataframe(session_df, use_container_width=True, height=280)

        st.divider()
        st.subheader("🧠 Top User Journeys")

        top_n = st.slider("Number of journeys to extract", 3, 10, 5)

        extractor = JourneyExtractor(sessions)
        top_journeys = extractor.top_journeys(top_n)
        st.session_state.top_journeys = top_journeys

        for i, journey in enumerate(top_journeys):
            with st.container(border=True):
                st.markdown(f"**Journey {i + 1}: {journey['journey_name']}**")
                st.write(" ➜ ".join(journey["sample_flow"]))
                col1, col2 = st.columns(2)
                col1.metric("Users", journey["users"])
                col2.metric("Share of traffic", f"{journey['percentage']} %")

        st.divider()
        st.subheader("📦 Journey JSON")

        json_output = extractor.to_json(top_journeys)
        st.session_state.journey_json = json_output

        with st.expander("View JSON"):
            st.code(json_output, language="json")

        st.download_button(
            "⬇ Download Journey JSON",
            data=json_output,
            file_name="journeys.json",
            mime="application/json",
        )

        st.divider()
        if st.button("Continue to Script Generation →", type="primary"):
            st.session_state.active_stage = STAGES[2]
            st.rerun()


# =====================================================
# STAGE 3 — GENERATE K6 SCRIPT
# =====================================================

elif st.session_state.active_stage == STAGES[2]:

    if st.session_state.journey_json is None:
        st.warning("⚠️ Extract journeys first (Step 2).")
    else:
        st.subheader("⚙️ Load Test Configuration")

        c1, c2 = st.columns(2)
        with c1:
            target_url = st.text_input("Target base URL", value="http://localhost:5000")
            max_vus = st.number_input("Max virtual users", min_value=1, value=300, step=10)
        with c2:
            p95_threshold = st.number_input("p(95) threshold (ms)", min_value=50, value=500, step=50)
            ramp_up, hold, ramp_down = st.columns(3)
            ramp_up_val = ramp_up.text_input("Ramp up", value="30s")
            hold_val = hold.text_input("Hold", value="1m")
            ramp_down_val = ramp_down.text_input("Ramp down", value="30s")

        st.divider()
        st.subheader("🤖 Generate k6 Script")

        if st.button("Generate k6 Script", type="primary"):
            with st.spinner("Calling the LLM to generate the k6 script..."):
                try:
                    script = generate_k6_script(
                        st.session_state.journey_json,
                        target_url=target_url,
                        max_vus=int(max_vus),
                        ramp_up=ramp_up_val,
                        hold=hold_val,
                        ramp_down=ramp_down_val,
                        p95_threshold_ms=int(p95_threshold),
                    )
                    save_script(script)
                    st.session_state.k6_script = script
                    st.success("k6 script generated successfully ✅")
                except Exception as e:
                    st.error(f"❌ Script generation failed: {e}")

        if st.session_state.k6_script:
            st.code(st.session_state.k6_script, language="javascript")
            st.download_button(
                "⬇ Download k6 Script",
                data=st.session_state.k6_script,
                file_name="generated_script.js",
                mime="application/javascript",
            )

            st.divider()
            if st.button("Continue to Execute Test →", type="primary"):
                st.session_state.active_stage = STAGES[3]
                st.rerun()


# =====================================================
# STAGE 4 — EXECUTE / IMPORT K6 RESULTS
# =====================================================

elif st.session_state.active_stage == STAGES[3]:

    if st.session_state.k6_script is None:
        st.warning("⚠️ Generate a k6 script first (Step 3).")
    else:
        run_tab, upload_tab = st.tabs(["▶️ Run k6 from this app", "📤 Upload existing results"])

        with run_tab:
            if k6_binary_available():
                st.caption(
                    "Runs `k6 run` as a subprocess on this machine and samples "
                    "**real** CPU / memory / disk / network telemetry once per "
                    "second while the test executes."
                )
                if st.button("▶️ Run k6 Test Now", type="primary"):
                    with st.spinner("Running k6 load test — this can take a few minutes..."):
                        script_path = str(Path(tempfile.gettempdir()) / "loadpilot_script.js")
                        Path(script_path).write_text(st.session_state.k6_script, encoding="utf-8")

                        stdout_text, telemetry, error = run_k6_script(script_path)

                    if error:
                        st.error(f"❌ {error}")
                    else:
                        st.session_state.k6_raw_output = stdout_text
                        st.session_state.k6_metrics = parse_k6_output(stdout_text)
                        st.session_state.k6_telemetry = normalize_real_telemetry(telemetry)
                        st.success("Test complete — live telemetry captured ✅")
            else:
                st.info(
                    "The `k6` binary isn't installed on this machine, so tests "
                    "can't be executed directly from the app. Install k6 "
                    "(https://k6.io/docs/get-started/installation/), or use the "
                    "**Upload existing results** tab instead."
                )

        with upload_tab:
            st.caption(
                "If you ran `k6 run generated_script.js` elsewhere, upload the "
                "text/JSON summary output here. Infra telemetry will be "
                "**estimated** from the k6 metrics themselves, since this app "
                "has no access to the machine that actually ran the test."
            )

            k6_file = st.file_uploader(
                "Upload k6 Results",
                type=["txt", "json"],
                key="k6_results_dashboard",
            )

            if k6_file is not None:
                try:
                    file_content = k6_file.read()
                    if isinstance(file_content, bytes):
                        file_content = file_content.decode("utf-8", errors="ignore")

                    metrics = parse_k6_output(file_content)
                    st.session_state.k6_raw_output = file_content
                    st.session_state.k6_metrics = metrics
                    st.session_state.k6_telemetry = estimate_telemetry_from_metrics(metrics)
                    st.success("k6 results parsed ✅")
                except Exception as e:
                    st.error(f"❌ Unable to parse k6 results: {e}")

        if st.session_state.k6_metrics is not None:
            with st.expander("🔍 Parsed k6 metrics"):
                st.json(st.session_state.k6_metrics)

            st.divider()
            if st.button("Continue to Dashboard →", type="primary"):
                st.session_state.active_stage = STAGES[4]
                st.rerun()


# =====================================================
# STAGE 5 — PERFORMANCE DASHBOARD
# =====================================================

elif st.session_state.active_stage == STAGES[4]:

    if st.session_state.k6_metrics is None:
        st.warning("⚠️ Run or upload a k6 test first (Step 4).")
    else:
        render_dashboard(
            st.session_state.k6_metrics,
            st.session_state.k6_telemetry,
        )
