"""
app_subset_choices.py — Streamlit app for filtering stimuli out of a choice file.

Run locally:
    cd ~/Downloads/rs-software
    streamlit run app_subset_choices.py
"""

import sys
import os
import io
import tempfile
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.rs_py.utils.util import load_choices
from rs_tools.subset_stimuli import subset_choice_file, save_choice_file

st.set_page_config(page_title="Subset Stimuli", layout="wide", initial_sidebar_state="expanded")

CUSTOM_CSS = """
<style>
html, body { font-family: "Helvetica Neue", Inter, -apple-system, sans-serif; }

.block-container { padding-top: 2.2rem; max-width: 900px; }

.hero {
    background: linear-gradient(135deg, #6C5CE7 0%, #4834D4 100%);
    border-radius: 18px;
    padding: 2rem 2.2rem;
    color: white;
    margin-bottom: 1.6rem;
    box-shadow: 0 10px 30px rgba(108, 92, 231, 0.25);
}
.hero h1 { margin: 0 0 0.35rem 0; font-size: 1.9rem; font-weight: 700; color: white; }
.hero p { margin: 0; opacity: 0.92; font-size: 0.98rem; }

.steps { display: flex; gap: 0.6rem; margin-bottom: 1.4rem; flex-wrap: wrap; }
.step {
    flex: 1; min-width: 150px;
    background: #FFFFFF; border: 1px solid #E7E5F5;
    border-radius: 12px; padding: 0.75rem 1rem;
    display: flex; align-items: center; gap: 0.6rem;
}
.step .num {
    background: #EFECFD; color: #4834D4;
    width: 26px; height: 26px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 0.85rem; flex-shrink: 0;
}
.step .label { font-size: 0.87rem; color: #1B1B2F; font-weight: 600; }
.step.done { border-color: #6C5CE7; }
.step.done .num { background: #6C5CE7; color: white; }
.step.pending { opacity: 0.5; }

.card {
    background: #FFFFFF; border: 1px solid #E7E5F5;
    border-radius: 16px; padding: 1.5rem 1.6rem; margin-bottom: 1.2rem;
    box-shadow: 0 2px 10px rgba(27, 27, 47, 0.04);
}
.card h3 { margin-top: 0; font-size: 1.08rem; color: #1B1B2F; }
.card p.subtitle { color: #6B7280; font-size: 0.9rem; margin-top: -0.5rem; }

.metric-row { display: flex; gap: 0.9rem; flex-wrap: wrap; }
.metric-box {
    flex: 1; min-width: 160px;
    background: #EFECFD; border-radius: 14px;
    padding: 1rem 1.1rem; text-align: left;
}
.metric-box .value { font-size: 1.65rem; font-weight: 800; color: #4834D4; line-height: 1.1; }
.metric-box .label { font-size: 0.82rem; color: #6B7280; margin-top: 0.25rem; }
.metric-box.excluded { background: #FDECEC; }
.metric-box.excluded .value { color: #C0392B; }
.metric-box.kept { background: #E9F9EE; }
.metric-box.kept .value { color: #1E8449; }

.pill-list { display: flex; flex-wrap: wrap; gap: 0.4rem; margin-top: 0.6rem; }
.pill {
    background: #EFECFD; color: #4834D4;
    border-radius: 999px; padding: 0.25rem 0.75rem; font-size: 0.82rem; font-weight: 600;
}
.pill.more { background: transparent; color: #6B7280; font-weight: 500; }

div[data-testid="stSidebar"] { background: #FAFAFE; border-right: 1px solid #E7E5F5; }
div.stButton > button, div.stDownloadButton > button {
    border-radius: 10px; font-weight: 600; border: none;
}
div.stButton > button[kind="primary"], div.stDownloadButton > button {
    background: #6C5CE7; box-shadow: 0 4px 14px rgba(108, 92, 231, 0.35);
}
div.stButton > button[kind="primary"]:hover, div.stDownloadButton > button:hover {
    background: #4834D4;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

st.markdown(
    """
    <div class="hero">
        <h1>Subset Stimuli</h1>
        <p>Keep or remove specific stimuli from a choice file before running analysis —
        works on both triadic and tetradic files.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.expander("New here? What does this do?", expanded=False):
    st.markdown(
        "Upload a choice file, pick which stimuli to keep or drop, and download a "
        "smaller version with just those stimuli.\n\n"
        "Any trial that mentions a removed stimulus gets dropped too, and the "
        "remaining stimuli are renumbered from 1, with no gaps."
    )

st.sidebar.title("Subset Stimuli")
st.sidebar.caption("Filter a choice file down to a chosen set of stimuli.")
st.sidebar.markdown("---")

uploaded = st.sidebar.file_uploader("Choice file (.mat)", type="mat")


def step_badges(uploaded_done, selected_done, run_done):
    def cls(done, active):
        if done:
            return "step done"
        return "step pending" if not active else "step"
    st.markdown(
        f"""
        <div class="steps">
            <div class="{cls(uploaded_done, True)}"><div class="num">1</div><div class="label">Upload file</div></div>
            <div class="{cls(selected_done, uploaded_done)}"><div class="num">2</div><div class="label">Choose stimuli</div></div>
            <div class="{cls(run_done, selected_done)}"><div class="num">3</div><div class="label">Run &amp; download</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


if uploaded is None:
    step_badges(False, False, False)
    st.markdown(
        '<div class="card"><h3>Get started</h3>'
        '<p class="subtitle">Upload a .mat choice file in the sidebar to begin.</p></div>',
        unsafe_allow_html=True,
    )
    st.stop()

with tempfile.NamedTemporaryFile(suffix=".mat", delete=False) as tmp:
    tmp.write(uploaded.read())
    tmp_path = tmp.name

try:
    resp, rep, metadata, stim_list = load_choices(tmp_path)
except Exception as e:
    st.error(f"Could not load file: {e}\n\nMake sure this is a **choice** file, not a coordinates file.")
    st.stop()
finally:
    os.unlink(tmp_path)

st.sidebar.markdown("---")
st.sidebar.subheader("Selection")
mode = st.sidebar.radio(
    "How do you want to select stimuli?",
    ["Keep only these (include)", "Remove these (exclude)", "Match a pattern (regex)"],
)

include = exclude = regex = None
regex_mode = "include"

if mode == "Keep only these (include)":
    include = st.sidebar.multiselect("Stimuli to keep", options=stim_list)
elif mode == "Remove these (exclude)":
    exclude = st.sidebar.multiselect("Stimuli to remove", options=stim_list)
else:
    regex = st.sidebar.text_input("Regex pattern", placeholder="e.g. ^b for anything starting with b")
    regex_mode = st.sidebar.radio("Pattern matches should be...", ["include", "exclude"], horizontal=True)

alphabetize = st.sidebar.checkbox("Alphabetize the output stimulus list", value=False)

st.sidebar.markdown("---")
run_btn = st.sidebar.button("Run", type="primary", use_container_width=True)

selection_made = bool(include or exclude or regex)

st.markdown(
    f'<div class="card"><h3>Loaded file</h3>'
    f'<p class="subtitle">{uploaded.name}</p>'
    f'<div class="metric-row">'
    f'<div class="metric-box"><div class="value">{len(stim_list)}</div><div class="label">Stimuli</div></div>'
    f'<div class="metric-box"><div class="value">{len(resp)}</div><div class="label">Trial types</div></div>'
    f'</div></div>',
    unsafe_allow_html=True,
)

if not run_btn:
    step_badges(True, selection_made, False)
    st.markdown(
        '<div class="card"><h3>Set your selection</h3>'
        '<p class="subtitle">Choose stimuli in the sidebar, then click <b>Run</b>.</p></div>',
        unsafe_allow_html=True,
    )
    st.stop()

if mode == "Keep only these (include)" and not include:
    st.error("Select at least one stimulus to keep.")
    st.stop()
if mode == "Remove these (exclude)" and not exclude:
    st.error("Select at least one stimulus to remove.")
    st.stop()
if mode == "Match a pattern (regex)" and not regex:
    st.error("Enter a regex pattern.")
    st.stop()

try:
    new_resp, new_rep, new_stims = subset_choice_file(
        stim_list, resp, rep, include=include, exclude=exclude,
        regex=regex, regex_mode=regex_mode, alphabetize=alphabetize)
except ValueError as e:
    st.error(str(e))
    st.stop()

step_badges(True, True, True)

n_excluded_stim = len(stim_list) - len(new_stims)
n_dropped_trials = len(resp) - len(new_resp)

pills = "".join(f'<span class="pill">{name}</span>' for name in new_stims[:24])
more = f'<span class="pill more">+{len(new_stims) - 24} more</span>' if len(new_stims) > 24 else ""

st.markdown(
    f"""
    <div class="card">
        <h3>Result</h3>
        <div class="metric-row">
            <div class="metric-box kept">
                <div class="value">{len(new_stims)} / {len(stim_list)}</div>
                <div class="label">Stimuli kept</div>
            </div>
            <div class="metric-box excluded">
                <div class="value">{n_excluded_stim}</div>
                <div class="label">Stimuli excluded</div>
            </div>
            <div class="metric-box excluded">
                <div class="value">{n_dropped_trials} / {len(resp)}</div>
                <div class="label">Trials dropped</div>
            </div>
        </div>
        <div class="pill-list">{pills}{more}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

if not new_resp:
    st.warning(
        "No trials remain after filtering, so there's nothing to download. "
        "This can happen with tetradic files if the stimuli you kept never "
        "appear together in the same trial -- try keeping a larger set."
    )
    st.stop()

buf = io.BytesIO()
with tempfile.NamedTemporaryFile(suffix=".mat", delete=False) as tmp_out:
    save_choice_file(tmp_out.name, new_resp, new_rep, new_stims)
    with open(tmp_out.name, "rb") as f:
        buf.write(f.read())
os.unlink(tmp_out.name)

out_name = uploaded.name.replace(".mat", "_subset.mat")
st.download_button("Download subset .mat", data=buf.getvalue(),
                   file_name=out_name, mime="application/octet-stream")
