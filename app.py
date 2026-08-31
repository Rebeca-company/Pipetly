"""
Prunia – Biomedical Protocol Extractor
Streamlit front-end for the Pipetly pipeline.
"""

from __future__ import annotations

import asyncio
import base64
import logging
import os
import queue
import sys
import threading
import time
import traceback
from pathlib import Path

import streamlit as st

# ── Ensure pipetly package directory is on sys.path ───────────────────────────
pipetly_dir = str(Path(__file__).parent.resolve())
if pipetly_dir not in sys.path:
    sys.path.insert(0, pipetly_dir)

# ── Page config ---------------------------------------------------------------
st.set_page_config(
    page_title="Prunia – Biomedical Protocol Extractor",
    page_icon="assets/prunia_logo.png",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Brand palette -------------------------------------------------------------
BROKEN_WHITE = "#FDFCF5"
DARK_NAVY    = "#2F3C4D"
RED          = "#D1232B"
GOLD         = "#C1A063"

# ── Global CSS ----------------------------------------------------------------
st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    html {{
        font-size: 17px;
    }}
    html, body, [class*="css"] {{
        font-family: 'Inter', sans-serif;
    }}

    /* Hide default sidebar toggle and collapsed sidebar */
    [data-testid="collapsedControl"] {{ display: none; }}
    [data-testid="stSidebar"] {{ display: none; }}

    /* App background */
    .stApp {{
        background: {BROKEN_WHITE};
        color: {DARK_NAVY};
    }}

    /* Hide Streamlit's own top toolbar / header */
    header[data-testid="stHeader"],
    [data-testid="stToolbar"] {{
        display: none !important;
    }}

    /* Remove default top padding */
    .block-container,
    [data-testid="stMainBlockContainer"] {{
        padding-top: 0.5rem !important;
        padding-bottom: 2rem;
        max-width: 100%;
    }}

    /* ── Header card ── */
    .prunia-header {{
        background: #2F3C4D;
        border-radius: 12px;
        padding: 0.6rem 1.2rem;
        display: flex;
        align-items: center;
        gap: 1.2rem;
        margin-bottom: 0.5rem;
    }}
    .header-logo-wrap {{
        background: #FDFCF5;
        border-radius: 8px;
        padding: 4px 6px;
        display: flex;
        align-items: center;
    }}
    .prunia-wordmark {{
        font-size: 1.5rem;
        font-weight: 800;
        color: #FDFCF5;
        letter-spacing: -0.02em;
        margin: 0;
        line-height: 1;
    }}
    .prunia-tagline {{
        font-size: 0.72rem;
        color: rgba(253,252,245,0.60);
        margin: 0.1rem 0 0 0;
        font-weight: 400;
    }}

    /* ── Section headings in config panel ── */
    .config-section {{
        font-size: 0.65rem;
        font-weight: 700;
        letter-spacing: 0.10em;
        text-transform: uppercase;
        color: #D1232B;
        margin-top: 1.0rem;
        margin-bottom: 0.3rem;
        padding-bottom: 0.2rem;
        border-bottom: 1px solid rgba(209,35,43,0.2);
    }}

    /* ── Config panel: left column background ── */
    [data-testid="column"]:first-child {{
        background: #2F3C4D;
        border-radius: 12px;
        padding: 1.0rem 1rem 1.0rem 1rem;
    }}
    [data-testid="column"]:first-child label,
    [data-testid="column"]:first-child p,
    [data-testid="column"]:first-child span,
    [data-testid="column"]:first-child .stMarkdown,
    [data-testid="column"]:first-child .stSlider label {{
        color: #FDFCF5 !important;
    }}
    [data-testid="column"]:first-child [data-testid="stTextInput"] input,
    [data-testid="column"]:first-child [data-testid="stNumberInput"] input {{
        background: rgba(255,255,255,0.08) !important;
        border: 1px solid rgba(209,35,43,0.40) !important;
        border-radius: 7px !important;
        color: #FDFCF5 !important;
    }}
    [data-testid="column"]:first-child [data-testid="stTextInput"] input:focus {{
        border-color: #D1232B !important;
        box-shadow: 0 0 0 2px rgba(209,35,43,0.18) !important;
    }}

    /* ── Main inputs (right column) ── */
    [data-testid="stTextArea"] textarea {{
        background: #ffffff !important;
        border: 1.5px solid rgba(209,35,43,0.25) !important;
        border-radius: 8px !important;
        color: #2F3C4D !important;
        font-size: 0.90rem;
        padding: 0.5rem !important;
    }}
    [data-testid="stTextArea"] textarea:focus {{
        border-color: #D1232B !important;
        box-shadow: 0 0 0 3px rgba(209,35,43,0.12) !important;
    }}

    /* ── Labels ── */
    label {{
        color: #2F3C4D !important;
        font-weight: 500;
        margin-bottom: 0.2rem !important;
    }}

    /* ── Generate button ── */
    .stButton > button {{
        background: linear-gradient(135deg, #D1232B 0%, #a01920 100%);
        color: #FDFCF5;
        border: none;
        border-radius: 8px;
        font-weight: 700;
        font-size: 0.90rem;
        padding: 0.4rem 1rem;
        letter-spacing: 0.03em;
        transition: all 0.22s ease;
        box-shadow: 0 4px 12px rgba(209,35,43,0.30);
        width: 100%;
        margin-top: 0.2rem;
    }}
    .stButton > button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 6px 18px rgba(209,35,43,0.50);
        background: linear-gradient(135deg, #e02530 0%, #D1232B 100%);
    }}
    .stButton > button:active {{ transform: translateY(0); }}

    /* ── Step progress chips ── */
    .step-bar {{
        display: flex; gap: 0.20rem; margin: 0.3rem 0; flex-wrap: wrap;
    }}
    .step-chip {{
        padding: 0.15rem 0.35rem; border-radius: 4px; font-size: 0.68rem;
        font-weight: 600; border: 1px solid rgba(47,60,77,0.18);
        color: rgba(47,60,77,0.45); background: rgba(209,35,43,0.04);
        transition: all 0.25s; text-align: center; line-height: 1.2;
    }}
    .step-chip.active {{ background: rgba(209,35,43,0.12); border-color: #D1232B; color: #D1232B; font-weight: 700; }}
    .step-chip.done   {{ background: rgba(46,204,113,0.12); border-color: #27ae60; color: #1e8449; }}
    .step-chip.error  {{ background: rgba(209,35,43,0.15); border-color: #D1232B; color: #D1232B; }}

    /* ── KPI metric cards ── */
    .kpi-card {{
        background: #ffffff;
        border: 1px solid rgba(47,60,77,0.12);
        border-radius: 8px;
        padding: 0.5rem 0.5rem;
        text-align: center;
        box-shadow: 0 1px 4px rgba(0,0,0,0.02);
    }}
    .kpi-card .kpi-num {{
        font-size: 1.25rem;
        font-weight: 800;
        color: #2F3C4D;
        line-height: 1.1;
    }}
    .kpi-card .kpi-label {{
        font-size: 0.65rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: rgba(47,60,77,0.55);
        margin-top: 0.15rem;
    }}

    /* ── Step details card ── */
    .step-detail-card {{
        background: #ffffff;
        border-left: 4px solid #D1232B;
        border-radius: 6px;
        padding: 0.5rem 0.8rem;
        margin-bottom: 0.3rem;
        box-shadow: 0 1px 6px rgba(0,0,0,0.03);
    }}
    .step-detail-title {{
        font-size: 0.78rem;
        font-weight: 700;
        color: #2F3C4D;
        margin-bottom: 0.15rem;
    }}
    .step-detail-body {{
        font-size: 0.72rem;
        color: rgba(47,60,77,0.85);
        line-height: 1.3;
    }}

    /* ── Status badges ── */
    .badge-running {{
        display: inline-block;
        background: linear-gradient(90deg, {RED}, #a01920);
        color: {BROKEN_WHITE}; font-weight: 700; font-size: 0.72rem;
        padding: 0.2rem 0.75rem; border-radius: 999px;
        animation: pulse 1.5s infinite;
    }}
    .badge-done {{
        display: inline-block;
        background: linear-gradient(90deg, #2ecc71, #27ae60);
        color: white; font-weight: 700; font-size: 0.72rem;
        padding: 0.2rem 0.75rem; border-radius: 999px;
    }}
    .badge-error {{
        display: inline-block;
        background: linear-gradient(90deg, {RED}, #a01920);
        color: white; font-weight: 700; font-size: 0.72rem;
        padding: 0.2rem 0.75rem; border-radius: 999px;
    }}
    @keyframes pulse {{
        0%   {{ opacity: 1; }}
        50%  {{ opacity: 0.6; }}
        100% {{ opacity: 1; }}
    }}

    /* ── Result / error boxes ── */
    .result-box {{
        background: #ffffff;
        border: 1.5px solid rgba(193,160,99,0.35);
        border-radius: 12px; padding: 1.4rem; margin-top: 1rem;
        box-shadow: 0 2px 14px rgba(193,160,99,0.10);
    }}

    /* ── Divider ── */
    hr {{ border-color: rgba(209,35,43,0.15) !important; margin: 1.2rem 0; }}

    /* ── Scrollbar ── */
    ::-webkit-scrollbar {{ width: 5px; }}
    ::-webkit-scrollbar-track {{ background: transparent; }}
    ::-webkit-scrollbar-thumb {{ background: rgba(209,35,43,0.30); border-radius: 3px; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# =============================================================================
# HEADER BAR
# =============================================================================
LOGO_PATH = Path(__file__).parent / "docs" / "prunia_logo.png"

logo_html = ""
if LOGO_PATH.exists():
    logo_b64 = base64.b64encode(LOGO_PATH.read_bytes()).decode()
    logo_html = (
        f'<div class="header-logo-wrap">'
        f'<img src="data:image/png;base64,{logo_b64}" width="38" style="display:block;"/>'
        f'</div>'
    )

st.markdown(
    f"""
    <div class="prunia-header">
        {logo_html}
        <div>
            <p class="prunia-wordmark">Prunia</p>
            <p class="prunia-tagline">Biomedical Protocol Extractor &nbsp;&middot;&nbsp; Multi-source academic search + LLM extraction</p>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)

# =============================================================================
# PIPELINE STEPS DEFINITION & UI HELPERS
# =============================================================================
STEPS = [
    "Query Expansion", "Paper Search", "Metadata Filter",
    "Full-Text Retrieval", "Text Extraction", "Post-Extraction Filter",
    "Protocol Extraction", "Protocol Scoring", "Final Formatting",
]


def render_step_bar(active: int = -1, done_up_to: int = -1, error_at: int = -1) -> str:
    chips = []
    for i, name in enumerate(STEPS):
        if error_at == i:
            cls = "error"
        elif i <= done_up_to:
            cls = "done"
        elif i == active:
            cls = "active"
        else:
            cls = ""
        chips.append(f'<div class="step-chip {cls}">Step {i+1}:<br>{name}</div>')
    return f'<div class="step-bar">{"".join(chips)}</div>'


def render_kpi_cards(metrics: dict) -> str:
    return f"""
    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.6rem; margin: 0.8rem 0;">
        <div class="kpi-card">
            <div class="kpi-num">{metrics.get('queries', 0)}</div>
            <div class="kpi-label">Queries</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-num">{metrics.get('raw_papers', 0)}</div>
            <div class="kpi-label">Papers Found</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-num">{metrics.get('full_text_papers', 0)}</div>
            <div class="kpi-label">Full Text</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-num">{metrics.get('protocols_extracted', 0)}</div>
            <div class="kpi-label">Protocols</div>
        </div>
    </div>
    """


# =============================================================================
# EXECUTION & THREAD-SAFE LOGGING HELPERS
# =============================================================================
def inject_env_vars() -> None:
    env_map = {
        "OPENROUTER_API_KEY":       st.session_state.get("openrouter_key", ""),
        "ELSEVIER_API_KEY":         st.session_state.get("elsevier_key", ""),
        "ELSEVIER_INST_TOKEN":      st.session_state.get("elsevier_token", ""),
        "SEMANTIC_SCHOLAR_API_KEY": st.session_state.get("semantic_key", ""),
        "UNPAYWALL_EMAIL":          st.session_state.get("unpaywall_email", ""),
        "NCBI_API_KEY":             st.session_state.get("ncbi_key", ""),
    }
    for k, v in env_map.items():
        if v:
            os.environ[k] = v
        else:
            os.environ.pop(k, None)


def patch_settings() -> None:
    """Update cached settings with UI values in-place."""
    import config as cfg_module
    inject_env_vars()
    
    # We do NOT clear the cache. We mutate the existing singleton so that all modules
    # that did `_s = get_settings()` at import time see the new values.
    s = cfg_module.get_settings()
    
    # API Keys
    s.openrouter_api_key       = st.session_state.get("openrouter_key", s.openrouter_api_key)
    s.elsevier_api_key         = st.session_state.get("elsevier_key", s.elsevier_api_key)
    s.elsevier_inst_token      = st.session_state.get("elsevier_token", s.elsevier_inst_token)
    s.semantic_scholar_api_key = st.session_state.get("semantic_key", s.semantic_scholar_api_key)
    s.unpaywall_email          = st.session_state.get("unpaywall_email", s.unpaywall_email)
    s.ncbi_api_key             = st.session_state.get("ncbi_key", s.ncbi_api_key)

    # Pipeline parameters
    s.llm_model_general     = st.session_state.get("llm_model", s.llm_model_general)
    s.top_k_protocols       = st.session_state.get("top_k", s.top_k_protocols)
    s.max_papers_per_source = st.session_state.get("max_papers", s.max_papers_per_source)
    s.max_citation_depth    = st.session_state.get("max_depth", s.max_citation_depth)



class ThreadQueueHandler(logging.Handler):
    """Thread-safe logging handler that puts records into a Queue."""
    def __init__(self, log_queue: queue.Queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            self.log_queue.put(msg)
        except Exception:
            self.handleError(record)


# =============================================================================
# TWO-COLUMN BODY
# =============================================================================
col_config, col_main = st.columns([1, 2.8], gap="large")

# ── LEFT: Configuration panel ─────────────────────────────────────────────────
with col_config:
    import config as cfg_module
    try:
        def_cfg = cfg_module.get_settings()
    except Exception:
        def_cfg = None

    def_model          = def_cfg.llm_model_general if def_cfg else "deepseek/deepseek-v4-flash"
    def_top_k          = def_cfg.top_k_protocols if def_cfg else 3
    def_max_papers     = def_cfg.max_papers_per_source if def_cfg else 3
    def_max_depth      = def_cfg.max_citation_depth if def_cfg else 2

    def_openrouter_key = def_cfg.openrouter_api_key if def_cfg else ""
    def_elsevier_key   = def_cfg.elsevier_api_key if def_cfg else ""
    def_elsevier_token = def_cfg.elsevier_inst_token if def_cfg else ""
    def_semantic_key   = def_cfg.semantic_scholar_api_key if def_cfg else ""
    def_unpaywall_email= def_cfg.unpaywall_email if def_cfg else ""
    def_ncbi_key       = def_cfg.ncbi_api_key if def_cfg else ""

    st.markdown('<div class="config-section">Model</div>', unsafe_allow_html=True)
    PRESET_MODELS = [
        "deepseek/deepseek-v4-flash",
        "google/gemini-2.5-flash",
        "xiaomi/mimo-v2.5",
        "google/gemini-3-flash-preview",
        "anthropic/claude-3.5-haiku",
        "openai/gpt-4o-mini",
        "Otro (ID personalizado)...",
    ]

    default_idx = PRESET_MODELS.index(def_model) if def_model in PRESET_MODELS else len(PRESET_MODELS) - 1
    selected_model_option = st.selectbox(
        "Select LLM Model",
        options=PRESET_MODELS,
        index=default_idx,
        help="Select a recommended model or enter a custom OpenRouter model ID.",
        key="model_select_preset",
    )

    if selected_model_option == "Otro (ID personalizado)...":
        llm_model = st.text_input(
            "Custom OpenRouter Model ID",
            value=def_model if def_model not in PRESET_MODELS[:-1] else "meta-llama/llama-3.3-70b-instruct",
            help="Full OpenRouter model string (e.g. meta-llama/llama-3.3-70b-instruct)",
            key="llm_model",
        )
    else:
        llm_model = selected_model_option
        st.session_state["llm_model"] = selected_model_option

    st.markdown('<div class="config-section">Pipeline Parameters</div>', unsafe_allow_html=True)
    top_k_protocols = st.slider(
        "Top-K Protocols", 1, 10, def_top_k, 1,
        help="Number of top-scored protocols in the final report.",
        key="top_k",
    )
    max_papers = st.slider(
        "Max Papers per Source", 1, 20, def_max_papers, 1,
        help="Maximum papers fetched from each search API.",
        key="max_papers",
    )
    max_depth = st.slider(
        "Max Citation Recursion Depth", 0, 5, def_max_depth, 1,
        help="Depth of the recursive citation investigator (0 = no recursion).",
        key="max_depth",
    )

    st.markdown('<div class="config-section">API Keys</div>', unsafe_allow_html=True)
    openrouter_key = st.text_input(
        "OpenRouter API Key (required)",
        value=def_openrouter_key,
        type="password",
        placeholder="sk-or-...",
        help="https://openrouter.ai/keys (auto-loaded from .env if available)",
        key="openrouter_key",
    )

    with st.expander("Optional API Keys", expanded=False):
        elsevier_key    = st.text_input("Elsevier API Key", value=def_elsevier_key, type="password",
                              placeholder="Leave blank to skip", key="elsevier_key")
        semantic_key    = st.text_input("Semantic Scholar API Key", value=def_semantic_key, type="password",
                              placeholder="Leave blank to skip", key="semantic_key")
        unpaywall_email = st.text_input("Unpaywall Email", value=def_unpaywall_email,
                              placeholder="you@institution.edu", key="unpaywall_email")
        ncbi_key        = st.text_input("NCBI (PubMed) API Key", value=def_ncbi_key, type="password",
                              placeholder="Leave blank to skip", key="ncbi_key")

    st.markdown(
        f'<p style="font-size:0.65rem;color:rgba(253,252,245,0.35);margin-top:0.4rem;">'
        f'Keys loaded from .env when present. Session changes are temporary.</p>',
        unsafe_allow_html=True,
    )


# ── RIGHT: Prompt + Execution & Results ───────────────────────────────────────
with col_main:
    st.markdown(
        f'<p style="font-size:0.72rem;font-weight:700;letter-spacing:0.10em;'
        f'text-transform:uppercase;color:{RED};margin-bottom:0.4rem;">'
        f'Protocol Request</p>',
        unsafe_allow_html=True,
    )

    user_prompt = st.text_area(
        label="Protocol request",
        label_visibility="collapsed",
        placeholder=(
            "Describe the protocol you need. "
            "e.g. Protocol for CRISPR-Cas9 gene editing in human iPSC cell lines "
            "with electroporation delivery..."
        ),
        height=75,
        key="user_prompt",
    )

    col_btn, col_hint = st.columns([1, 2])
    with col_btn:
        run_button = st.button("Generate Protocol", use_container_width=True, key="run_btn")
    with col_hint:
        st.markdown(
            f'<p style="color:rgba(47,60,77,0.45);font-size:0.80rem;padding-top:0.6rem;">'
            f'Searches multiple academic databases, extracts and scores protocols, '
            f'and writes a Markdown report.</p>',
            unsafe_allow_html=True,
        )

    # Placeholders for execution progress and results inside right column
    exec_container = st.container()

    if run_button:
        with exec_container:
            prompt_text = st.session_state.get("user_prompt", "").strip()
            api_key     = st.session_state.get("openrouter_key", "").strip()

            if not prompt_text:
                st.error("Please enter a protocol description before running.")
                st.stop()
            if not api_key:
                st.error("An OpenRouter API Key is required. Enter it in the configuration panel.")
                st.stop()

            patch_settings()

            st.markdown("<hr>", unsafe_allow_html=True)
            status_placeholder   = st.empty()
            step_bar_placeholder = st.empty()
            metrics_placeholder  = st.empty()
            details_placeholder  = st.empty()
            result_placeholder   = st.empty()

            # Initial UI state
            status_placeholder.markdown(
                f'<span class="badge-running">RUNNING</span>'
                f'<span style="margin-left:0.75rem;color:rgba(47,60,77,0.65);font-size:0.88rem;">'
                f'Starting pipeline...</span>',
                unsafe_allow_html=True,
            )
            step_bar_placeholder.markdown(render_step_bar(active=0), unsafe_allow_html=True)

            metrics = {
                "queries": 0,
                "raw_papers": 0,
                "unique_papers": 0,
                "full_text_papers": 0,
                "plain_text_papers": 0,
                "filtered_papers": 0,
                "protocols_extracted": 0,
                "protocols_scored": 0,
            }
            metrics_placeholder.markdown(render_kpi_cards(metrics), unsafe_allow_html=True)

            # Thread-safe log queue and handler setup
            log_queue: queue.Queue[str] = queue.Queue()
            queue_handler = ThreadQueueHandler(log_queue)
            queue_handler.setFormatter(
                logging.Formatter("%(asctime)s [%(levelname)s] %(name)s | %(message)s", datefmt="%H:%M:%S")
            )
            root_logger = logging.getLogger()
            root_logger.addHandler(queue_handler)

            # Dictionary to hold output / error from worker thread
            thread_result: dict[str, str | Path | None] = {"output_path": None, "error": None}

            def worker() -> None:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    import utils.logger as logger_module
                    logger_module.setup_logging()
                    import main as main_module
                    output = loop.run_until_complete(main_module.run_pipeline(prompt_text))
                    thread_result["output_path"] = output
                except Exception as exc:
                    thread_result["error"] = f"{type(exc).__name__}: {exc}\n\n{traceback.format_exc()}"
                finally:
                    loop.close()

            pipeline_thread = threading.Thread(target=worker, daemon=True)
            start_time = time.time()
            pipeline_thread.start()

            log_lines: list[str] = []
            step_details: list[dict[str, str]] = []
            active_step_idx = 0
            done_step_idx = -1

            # Main monitoring loop running on Streamlit's script thread
            while pipeline_thread.is_alive() or not log_queue.empty():
                # Drain log queue
                updated = False
                while not log_queue.empty():
                    try:
                        line = log_queue.get_nowait()
                        log_lines.append(line)
                        updated = True

                        # Parse Step progress and details from logs
                        for step_num in range(1, 10):
                            if f"[Step {step_num}] START" in line:
                                active_step_idx = step_num - 1
                            if f"[Step {step_num}] DONE" in line:
                                done_step_idx = step_num - 1

                        # Parse specific metrics from log lines
                        if "concept_queries=" in line:
                            try:
                                q_cnt = int(line.split("concept_queries=")[1].split()[0])
                                metrics["queries"] = q_cnt
                                step_details.append({
                                    "title": "Step 1: Query Expansion Complete",
                                    "body": f"Extracted research intent and generated {q_cnt} targeted concept queries."
                                })
                            except Exception:
                                pass
                        if "raw_records=" in line:
                            try:
                                r_cnt = int(line.split("raw_records=")[1].split()[0])
                                metrics["raw_papers"] = r_cnt
                                step_details.append({
                                    "title": "Step 2: Database Search Complete",
                                    "body": f"Retrieved {r_cnt} raw paper records across configured academic search APIs."
                                })
                            except Exception:
                                pass
                        if "[Step 3] DONE" in line and "output=" in line:
                            try:
                                u_cnt = int(line.split("output=")[1].split()[0])
                                metrics["unique_papers"] = u_cnt
                                step_details.append({
                                    "title": "Step 3: Metadata Filter Complete",
                                    "body": f"Deduplicated and validated DOIs. Kept {u_cnt} unique papers."
                                })
                            except Exception:
                                pass
                        if "[Step 4] DONE" in line and "output=" in line:
                            try:
                                ft_cnt = int(line.split("output=")[1].split()[0])
                                metrics["full_text_papers"] = ft_cnt
                                step_details.append({
                                    "title": "Step 4: Full-Text Retrieval Complete",
                                    "body": f"Fetched full-text body (PDF/XML/HTML) for {ft_cnt} papers."
                                })
                            except Exception:
                                pass
                        if "[Step 5] DONE" in line and "output=" in line:
                            try:
                                pt_cnt = int(line.split("output=")[1].split()[0])
                                metrics["plain_text_papers"] = pt_cnt
                                step_details.append({
                                    "title": "Step 5: Text Extraction Complete",
                                    "body": f"Parsed {pt_cnt} papers into normalized plain text."
                                })
                            except Exception:
                                pass
                        if "[Step 6] DONE" in line and "output=" in line:
                            try:
                                fl_cnt = int(line.split("output=")[1].split()[0])
                                metrics["filtered_papers"] = fl_cnt
                                step_details.append({
                                    "title": "Step 6: Post-Extraction Filter Complete",
                                    "body": f"{fl_cnt} papers satisfied text length constraints (10k - 200k chars)."
                                })
                            except Exception:
                                pass
                        if "[Step 7] DONE" in line and "output=" in line:
                            try:
                                pr_cnt = int(line.split("output=")[1].split()[0])
                                metrics["protocols_extracted"] = pr_cnt
                                step_details.append({
                                    "title": "Step 7: Recursive Protocol Extraction Complete",
                                    "body": f"Extracted and resolved {pr_cnt} protocol intervals and inherited citations."
                                })
                            except Exception:
                                pass
                        if "[Step 8] DONE" in line and "output=" in line:
                            try:
                                sc_cnt = int(line.split("output=")[1].split()[0])
                                metrics["protocols_scored"] = sc_cnt
                                step_details.append({
                                    "title": "Step 8: Protocol Scoring Complete",
                                    "body": f"Evaluated and re-scored {sc_cnt} extracted protocols."
                                })
                            except Exception:
                                pass

                    except queue.Empty:
                        break
                elapsed = time.time() - start_time
                curr_step_name = STEPS[active_step_idx] if 0 <= active_step_idx < len(STEPS) else "Processing..."

                status_placeholder.markdown(
                    f'<span class="badge-running">RUNNING</span>'
                    f'<span style="margin-left:0.75rem;color:rgba(47,60,77,0.75);font-size:0.88rem;">'
                    f'Step {active_step_idx + 1} / {len(STEPS)} &nbsp;&mdash;&nbsp; <b>{curr_step_name}</b> '
                    f'&nbsp;&middot;&nbsp; ⏱️ {elapsed:.1f}s</span>',
                    unsafe_allow_html=True,
                )
                if updated:
                    step_bar_placeholder.markdown(
                        render_step_bar(active=active_step_idx, done_up_to=done_step_idx),
                        unsafe_allow_html=True,
                    )
                    metrics_placeholder.markdown(render_kpi_cards(metrics), unsafe_allow_html=True)
    
                    # Render live step output stream
                    if step_details:
                        details_html = "".join([
                            f'<div class="step-detail-card">'
                            f'<div class="step-detail-title">{d["title"]}</div>'
                            f'<div class="step-detail-body">{d["body"]}</div>'
                            f'</div>'
                            for d in step_details[-1:]
                        ])
                        details_placeholder.markdown(details_html, unsafe_allow_html=True)
    


                time.sleep(0.25)

            # Clean up handler
            root_logger.removeHandler(queue_handler)

            elapsed_total = time.time() - start_time
            output_path = thread_result.get("output_path")
            error_msg = thread_result.get("error")

            if error_msg:
                st.session_state.pipeline_error = error_msg
                st.session_state.err_step_idx = min(done_step_idx + 1, len(STEPS) - 1)
                st.session_state.pipeline_done = True
                st.session_state.elapsed_total = elapsed_total
            else:
                st.session_state.pipeline_error = None
                st.session_state.output_path = output_path
                st.session_state.report_text = None
                if output_path and Path(output_path).exists():
                    st.session_state.report_text = Path(output_path).read_text(encoding="utf-8")
                st.session_state.pipeline_done = True
                st.session_state.elapsed_total = elapsed_total

            # Forcing a rerun so the results render outside the if run_button block
            st.rerun()

    if st.session_state.get("pipeline_done"):
        with exec_container:
            st.markdown("<hr>", unsafe_allow_html=True)
            if st.session_state.get("pipeline_error"):
                err_step_idx = st.session_state.err_step_idx
                st.markdown(
                    render_step_bar(done_up_to=err_step_idx-1, error_at=err_step_idx),
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<span class="badge-error">ERROR</span>'
                    f'<span style="margin-left:0.75rem;color:rgba(47,60,77,0.75);font-size:0.88rem;">'
                    f'Pipeline failed at Step {err_step_idx + 1} ({STEPS[err_step_idx]}) &nbsp;&middot;&nbsp; ⏱️ {st.session_state.elapsed_total:.1f}s</span>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"<div class='result-box' style='border-color:rgba(209,35,43,0.45);'>"
                    f"<p style='font-weight:700;color:{RED};margin-bottom:0.5rem;'>Pipeline Error Details</p>"
                    f"<pre style='font-size:0.72rem;color:{DARK_NAVY};"
                    f"white-space:pre-wrap;word-break:break-word;'>{st.session_state.pipeline_error}</pre></div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(render_step_bar(done_up_to=len(STEPS)-1), unsafe_allow_html=True)
                st.markdown(
                    f'<span class="badge-done">DONE</span>'
                    f'<span style="margin-left:0.75rem;color:rgba(47,60,77,0.75);font-size:0.88rem;">'
                    f'All 9 steps completed successfully! &nbsp;&middot;&nbsp; ⏱️ Total time: {st.session_state.elapsed_total:.1f}s</span>',
                    unsafe_allow_html=True,
                )

                report_text = st.session_state.get("report_text")
                if report_text:
                    st.markdown("---")
                    
                    st.download_button(
                        label="📥 Download Protocol Report (.md)",
                        data=report_text.encode("utf-8"),
                        file_name=Path(st.session_state.output_path).name,
                        mime="text/markdown",
                        key="download_report_btn",
                    )
                    st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)
                    
                    tab_report, tab_raw = st.tabs(["📄 Protocol Report", "📝 Raw Markdown"])

                    with tab_report:
                        st.markdown(f'<div class="result-box">{report_text}</div>', unsafe_allow_html=True)

                    with tab_raw:
                        st.code(report_text, language="markdown")
                else:
                    st.info("Pipeline completed, but output file was not found.")

# -- Footer --------------------------------------------------------------------
st.markdown("<br><hr>", unsafe_allow_html=True)
st.markdown(
    f'<p style="text-align:center;font-size:0.68rem;color:rgba(47,60,77,0.30);">'
    f'Prunia &nbsp;&middot;&nbsp; Biomedical Protocol Extractor &nbsp;&middot;&nbsp;'
    f' Built on the Pipetly pipeline</p>',
    unsafe_allow_html=True,
)
