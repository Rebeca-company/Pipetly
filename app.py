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
        padding-top: 1rem !important;
        padding-bottom: 2rem;
        max-width: 100%;
    }}

    /* ── Header card ── */
    .prunia-header {{
        background: {DARK_NAVY};
        border-radius: 14px;
        padding: 1rem 1.8rem;
        display: flex;
        align-items: center;
        gap: 1.2rem;
        margin-bottom: 1.4rem;
    }}
    .header-logo-wrap {{
        background: {BROKEN_WHITE};
        border-radius: 10px;
        padding: 5px 8px;
        display: flex;
        align-items: center;
    }}
    .prunia-wordmark {{
        font-size: 1.7rem;
        font-weight: 800;
        color: {BROKEN_WHITE};
        letter-spacing: -0.02em;
        margin: 0;
        line-height: 1;
    }}
    .prunia-tagline {{
        font-size: 0.78rem;
        color: rgba(253,252,245,0.50);
        margin: 0.15rem 0 0 0;
        font-weight: 400;
    }}

    /* ── Section headings in config panel ── */
    .config-section {{
        font-size: 0.68rem;
        font-weight: 700;
        letter-spacing: 0.10em;
        text-transform: uppercase;
        color: {RED};
        margin-top: 1.6rem;
        margin-bottom: 0.4rem;
        padding-bottom: 0.25rem;
        border-bottom: 1px solid rgba(209,35,43,0.2);
    }}

    /* ── Config panel: left column background ── */
    [data-testid="column"]:first-child {{
        background: {DARK_NAVY};
        border-radius: 14px;
        padding: 1.2rem 1.1rem 1.4rem 1.1rem;
    }}
    [data-testid="column"]:first-child label,
    [data-testid="column"]:first-child p,
    [data-testid="column"]:first-child span,
    [data-testid="column"]:first-child .stMarkdown,
    [data-testid="column"]:first-child .stSlider label {{
        color: {BROKEN_WHITE} !important;
    }}
    [data-testid="column"]:first-child [data-testid="stTextInput"] input,
    [data-testid="column"]:first-child [data-testid="stNumberInput"] input {{
        background: rgba(255,255,255,0.08) !important;
        border: 1px solid rgba(209,35,43,0.40) !important;
        border-radius: 7px !important;
        color: {BROKEN_WHITE} !important;
    }}
    [data-testid="column"]:first-child [data-testid="stTextInput"] input:focus {{
        border-color: {RED} !important;
        box-shadow: 0 0 0 2px rgba(209,35,43,0.18) !important;
    }}

    /* ── Main inputs (right column) ── */
    [data-testid="stTextArea"] textarea {{
        background: #ffffff !important;
        border: 1.5px solid rgba(209,35,43,0.25) !important;
        border-radius: 10px !important;
        color: {DARK_NAVY} !important;
        font-size: 0.95rem;
    }}
    [data-testid="stTextArea"] textarea:focus {{
        border-color: {RED} !important;
        box-shadow: 0 0 0 3px rgba(209,35,43,0.12) !important;
    }}

    /* ── Labels ── */
    label {{
        color: {DARK_NAVY} !important;
        font-weight: 500;
    }}

    /* ── Generate button ── */
    .stButton > button {{
        background: linear-gradient(135deg, {RED} 0%, #a01920 100%);
        color: {BROKEN_WHITE};
        border: none;
        border-radius: 9px;
        font-weight: 700;
        font-size: 0.95rem;
        padding: 0.6rem 2rem;
        letter-spacing: 0.03em;
        transition: all 0.22s ease;
        box-shadow: 0 4px 18px rgba(209,35,43,0.30);
        width: 100%;
    }}
    .stButton > button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 7px 24px rgba(209,35,43,0.50);
        background: linear-gradient(135deg, #e02530 0%, {RED} 100%);
    }}
    .stButton > button:active {{ transform: translateY(0); }}

    /* ── Step progress chips ── */
    .step-bar {{
        display: flex; gap: 0.35rem; margin: 0.8rem 0; flex-wrap: wrap;
    }}
    .step-chip {{
        padding: 0.25rem 0.65rem; border-radius: 6px; font-size: 0.70rem;
        font-weight: 600; border: 1px solid rgba(47,60,77,0.18);
        color: rgba(47,60,77,0.45); background: rgba(209,35,43,0.04);
        transition: all 0.25s;
    }}
    .step-chip.active {{ background: rgba(209,35,43,0.12); border-color: {RED}; color: {RED}; font-weight: 700; }}
    .step-chip.done   {{ background: rgba(46,204,113,0.12); border-color: #27ae60; color: #1e8449; }}
    .step-chip.error  {{ background: rgba(209,35,43,0.15); border-color: {RED}; color: {RED}; }}

    /* ── KPI metric cards ── */
    .kpi-card {{
        background: #ffffff;
        border: 1px solid rgba(47,60,77,0.12);
        border-radius: 10px;
        padding: 0.75rem 1rem;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.02);
    }}
    .kpi-card .kpi-num {{
        font-size: 1.4rem;
        font-weight: 800;
        color: {DARK_NAVY};
        line-height: 1.1;
    }}
    .kpi-card .kpi-label {{
        font-size: 0.68rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: rgba(47,60,77,0.55);
        margin-top: 0.2rem;
    }}

    /* ── Step details card ── */
    .step-detail-card {{
        background: #ffffff;
        border-left: 4px solid {RED};
        border-radius: 8px;
        padding: 0.75rem 1rem;
        margin-bottom: 0.6rem;
        box-shadow: 0 2px 10px rgba(0,0,0,0.03);
    }}
    .step-detail-title {{
        font-size: 0.82rem;
        font-weight: 700;
        color: {DARK_NAVY};
        margin-bottom: 0.25rem;
    }}
    .step-detail-body {{
        font-size: 0.76rem;
        color: rgba(47,60,77,0.85);
        line-height: 1.4;
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
# TWO-COLUMN BODY
# =============================================================================
col_config, col_main = st.columns([1, 2], gap="large")

# ── LEFT: Configuration panel ─────────────────────────────────────────────────
with col_config:
    st.markdown('<div class="config-section">Model</div>', unsafe_allow_html=True)
    llm_model = st.text_input(
        "OpenRouter Model ID",
        value="deepseek/deepseek-v4-flash",
        help="Any model on openrouter.ai, e.g. google/gemini-2.5-flash",
        key="llm_model",
        label_visibility="visible",
    )

    st.markdown('<div class="config-section">Pipeline Parameters</div>', unsafe_allow_html=True)
    top_k_protocols = st.slider(
        "Top-K Protocols", 1, 10, 3, 1,
        help="Number of top-scored protocols in the final report.",
        key="top_k",
    )
    max_papers = st.slider(
        "Max Papers per Source", 1, 20, 3, 1,
        help="Maximum papers fetched from each search API.",
        key="max_papers",
    )
    max_depth = st.slider(
        "Max Citation Recursion Depth", 0, 5, 2, 1,
        help="Depth of the recursive citation investigator (0 = no recursion).",
        key="max_depth",
    )

    st.markdown('<div class="config-section">API Keys</div>', unsafe_allow_html=True)
    openrouter_key = st.text_input(
        "OpenRouter API Key (required)",
        type="password",
        placeholder="sk-or-...",
        help="https://openrouter.ai/keys",
        key="openrouter_key",
    )

    with st.expander("Optional API Keys", expanded=False):
        elsevier_key    = st.text_input("Elsevier API Key", type="password",
                              placeholder="Leave blank to skip", key="elsevier_key")
        elsevier_token  = st.text_input("Elsevier Inst. Token", type="password",
                              placeholder="Leave blank to skip", key="elsevier_token")
        semantic_key    = st.text_input("Semantic Scholar API Key", type="password",
                              placeholder="Leave blank to skip", key="semantic_key")
        unpaywall_email = st.text_input("Unpaywall Email",
                              placeholder="you@institution.edu", key="unpaywall_email")
        ncbi_key        = st.text_input("NCBI (PubMed) API Key", type="password",
                              placeholder="Leave blank to skip", key="ncbi_key")

    st.markdown(
        f'<p style="font-size:0.65rem;color:rgba(253,252,245,0.35);margin-top:1.2rem;">'
        f'Keys are session-only and never persisted.</p>',
        unsafe_allow_html=True,
    )


# ── RIGHT: Prompt + Results ───────────────────────────────────────────────────
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
        height=140,
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
        chips.append(f'<div class="step-chip {cls}">Step {i+1}: {name}</div>')
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
    """Clear cached settings and rebuild with UI values."""
    import config as cfg_module
    cfg_module.get_settings.cache_clear()
    inject_env_vars()
    s = cfg_module.get_settings()
    s.llm_model_general     = st.session_state.get("llm_model", s.llm_model_general)
    s.top_k_protocols       = st.session_state.get("top_k", s.top_k_protocols)
    s.max_papers_per_source = st.session_state.get("max_papers", s.max_papers_per_source)
    s.max_citation_depth    = st.session_state.get("max_depth", s.max_citation_depth)
    import main as main_module
    main_module._s = s


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
# RUN PIPELINE
# =============================================================================
if run_button:
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
    progress_placeholder = st.empty()
    step_bar_placeholder = st.empty()
    metrics_placeholder  = st.empty()
    details_placeholder  = st.empty()
    log_placeholder      = st.empty()
    result_placeholder   = st.empty()

    # Initial UI state
    status_placeholder.markdown(
        f'<span class="badge-running">RUNNING</span>'
        f'<span style="margin-left:0.75rem;color:rgba(47,60,77,0.65);font-size:0.88rem;">'
        f'Starting pipeline...</span>',
        unsafe_allow_html=True,
    )
    progress_placeholder.progress(0.0)
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
        steps_done_cnt = done_step_idx + 1 if done_step_idx >= 0 else 0
        progress_val = min(1.0, max(0.05, steps_done_cnt / len(STEPS)))

        curr_step_name = STEPS[active_step_idx] if 0 <= active_step_idx < len(STEPS) else "Processing..."

        status_placeholder.markdown(
            f'<span class="badge-running">RUNNING</span>'
            f'<span style="margin-left:0.75rem;color:rgba(47,60,77,0.75);font-size:0.88rem;">'
            f'Step {active_step_idx + 1} / {len(STEPS)} &nbsp;&mdash;&nbsp; <b>{curr_step_name}</b> '
            f'&nbsp;&middot;&nbsp; ⏱️ {elapsed:.1f}s</span>',
            unsafe_allow_html=True,
        )
        progress_placeholder.progress(progress_val)
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
                for d in step_details[-4:]
            ])
            details_placeholder.markdown(details_html, unsafe_allow_html=True)

        # Render live log console
        visible_logs = log_lines[-16:]
        log_text = "\n".join(visible_logs)
        log_placeholder.markdown(
            f"<details><summary style='color:{RED};font-weight:600;"
            f"cursor:pointer;font-size:0.82rem;'>Live Execution Logs ({len(log_lines)} entries)</summary>"
            f"<pre style='background:#f7f6ef;border:1px solid rgba(209,35,43,0.15);"
            f"border-radius:8px;padding:0.75rem;font-size:0.68rem;color:{DARK_NAVY};"
            f"max-height:220px;overflow-y:auto;white-space:pre-wrap;word-break:break-all;'>"
            f"{log_text}</pre></details>",
            unsafe_allow_html=True,
        )

        time.sleep(0.15)

    # Clean up handler
    root_logger.removeHandler(queue_handler)

    elapsed_total = time.time() - start_time
    output_path = thread_result.get("output_path")
    error_msg = thread_result.get("error")

    if error_msg:
        err_step_idx = min(done_step_idx + 1, len(STEPS) - 1)
        step_bar_placeholder.markdown(
            render_step_bar(done_up_to=done_step_idx, error_at=err_step_idx),
            unsafe_allow_html=True,
        )
        status_placeholder.markdown(
            f'<span class="badge-error">ERROR</span>'
            f'<span style="margin-left:0.75rem;color:rgba(47,60,77,0.75);font-size:0.88rem;">'
            f'Pipeline failed at Step {err_step_idx + 1} ({STEPS[err_step_idx]}) &nbsp;&middot;&nbsp; ⏱️ {elapsed_total:.1f}s</span>',
            unsafe_allow_html=True,
        )
        result_placeholder.markdown(
            f"<div class='result-box' style='border-color:rgba(209,35,43,0.45);'>"
            f"<p style='font-weight:700;color:{RED};margin-bottom:0.5rem;'>Pipeline Error Details</p>"
            f"<pre style='font-size:0.72rem;color:{DARK_NAVY};"
            f"white-space:pre-wrap;word-break:break-word;'>{error_msg}</pre></div>",
            unsafe_allow_html=True,
        )
    else:
        progress_placeholder.progress(1.0)
        step_bar_placeholder.markdown(render_step_bar(done_up_to=len(STEPS)-1), unsafe_allow_html=True)
        status_placeholder.markdown(
            f'<span class="badge-done">DONE</span>'
            f'<span style="margin-left:0.75rem;color:rgba(47,60,77,0.75);font-size:0.88rem;">'
            f'All 9 steps completed successfully! &nbsp;&middot;&nbsp; ⏱️ Total time: {elapsed_total:.1f}s</span>',
            unsafe_allow_html=True,
        )

        if output_path and Path(output_path).exists():
            report_text = Path(output_path).read_text(encoding="utf-8")
            st.markdown("---")
            tab_report, tab_raw = st.tabs(["📄 Protocol Report", "📝 Raw Markdown"])

            with tab_report:
                st.markdown(f'<div class="result-box">{report_text}</div>', unsafe_allow_html=True)

            with tab_raw:
                st.code(report_text, language="markdown")

            st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)
            st.download_button(
                label="📥 Download Protocol Report (.md)",
                data=report_text.encode("utf-8"),
                file_name=Path(output_path).name,
                mime="text/markdown",
                key="download_report_btn",
            )
        else:
            result_placeholder.info("Pipeline completed, but output file was not found.")

# -- Footer --------------------------------------------------------------------
st.markdown("<br><hr>", unsafe_allow_html=True)
st.markdown(
    f'<p style="text-align:center;font-size:0.68rem;color:rgba(47,60,77,0.30);">'
    f'Prunia &nbsp;&middot;&nbsp; Biomedical Protocol Extractor &nbsp;&middot;&nbsp;'
    f' Built on the Pipetly pipeline</p>',
    unsafe_allow_html=True,
)
