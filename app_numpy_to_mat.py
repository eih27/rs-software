"""
app_numpy_to_mat.py — Streamlit app for NumPy → .mat conversion (the reverse of app_matnpy.py).

Run locally:
    cd ~/Downloads/rs-software
    streamlit run app_numpy_to_mat.py
"""

import sys
import os
import io
import tempfile
import numpy as np
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

st.set_page_config(page_title="NumPy → .mat", layout="centered")
st.title("NumPy → .mat Converter")
st.caption(
    "Part of the rs-software toolkit — converts a 5-column NumPy choice array "
    "back into a MATLAB/Octave `.mat` choice file."
)

with st.expander("New here? What is this, and what do I need?", expanded=False):
    st.markdown(
        "This is the reverse of the **.mat → NumPy** converter — it takes a NumPy array "
        "(the format produced by that tool, or built yourself in Python) and turns it back "
        "into a `.mat` choice file MATLAB/Octave can read.\n\n"
        "**What you need:** a `.npy` file with 5 columns, in this exact order: "
        "`ref, s1, s2, N(s1 chosen), N_repeats` (all 1-indexed).\n\n"
        "**Stimulus names are optional.** If you don't provide them, the output file will "
        "use generic names (`stim_01`, `stim_02`, ...) instead of your real stimulus names — "
        "still valid, just less readable."
    )

npy_file = st.file_uploader("Upload .npy choice array", type=["npy"])

st.markdown("**Stimulus names (optional)**")
stim_input_mode = st.radio(
    "How to provide names", ["Skip (use generic names)", "Type comma-separated", "Upload a text file (one name per line)"],
    horizontal=False
)

stim_list = None
if stim_input_mode == "Type comma-separated":
    raw = st.text_input("Stimulus names, comma-separated", placeholder="s01c01, s02c01, s03c01, ...")
    if raw.strip():
        stim_list = [s.strip() for s in raw.split(",") if s.strip()]
elif stim_input_mode == "Upload a text file (one name per line)":
    stim_file = st.file_uploader("Stimulus names file (.txt)", type=["txt"])
    if stim_file is not None:
        stim_list = [line.decode().strip() for line in stim_file.readlines() if line.strip()]

if npy_file is not None:
    try:
        # allow_pickle=True: some .npy files (e.g. saved as a tuple with a
        # stimulus name list alongside the array) need it to load at all.
        # Safe here since this is a lab-internal tool -- the app already
        # trusts whatever .mat file a user uploads unconditionally too.
        array = np.load(io.BytesIO(npy_file.read()), allow_pickle=True)

        if array.dtype == object or array.ndim != 2 or array.shape[1] != 5:
            st.error(
                f"This doesn't look like the 5-column choices array this tool expects "
                f"(ref, s1, s2, N(s1 chosen), N_repeats). Got shape {array.shape}, "
                f"dtype {array.dtype}.\n\n"
                f"If this file came from a script that saved *both* the array and a "
                f"stimulus name list together (e.g. `np.save(path, (array, stim_list))`), "
                f"try re-saving just the array on its own -- `np.save(path, array)`."
            )
        else:
            n_stim = int(array[:, :3].max())
            st.success(f"Loaded: **{array.shape[0]} trials**, **{n_stim} stimuli** (inferred from max index)")

            if stim_list and len(stim_list) < n_stim:
                st.warning(f"You provided {len(stim_list)} names but the data needs {n_stim} — "
                           f"the rest will be auto-filled with generic names.")

            st.dataframe(
                {"ref": array[:, 0].astype(int), "s1": array[:, 1].astype(int),
                 "s2": array[:, 2].astype(int), "n_s1_chosen": array[:, 3].astype(int),
                 "n_repeats": array[:, 4].astype(int)},
                use_container_width=True, height=300
            )

            from convert_numpy_to_mat import numpy_to_mat
            with tempfile.NamedTemporaryFile(suffix=".mat", delete=False) as tmp:
                out_path = tmp.name
            numpy_to_mat(array, stim_list=stim_list, out_path=out_path)
            with open(out_path, "rb") as f:
                mat_bytes = f.read()
            os.unlink(out_path)

            out_name = npy_file.name.replace(".npy", ".mat")
            st.download_button("Download .mat file", data=mat_bytes,
                               file_name=out_name, mime="application/octet-stream")

    except Exception as e:
        st.error(f"Conversion failed: {e}")
else:
    st.info("Upload a .npy choice array above to get started.")
