"""
app_matnpy.py — Streamlit app for .mat → NumPy conversion.

Run locally:
    cd ~/Downloads/rs-software
    streamlit run app_matnpy.py
"""

import sys
import os
import tempfile
import numpy as np
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

st.set_page_config(page_title=".mat → NumPy", layout="centered")
st.title(".mat → NumPy Converter")
st.caption(
    "Part of the rs-software toolkit — converts a MATLAB/Octave `.mat` choice file "
    "into a NumPy format, so the same data can be used in Python without MATLAB."
)

with st.expander("New here? What is this, and what file do I need?", expanded=False):
    st.markdown(
        "This lab's data comes out of MATLAB/Octave as `.mat` files. To work with that data "
        "in Python (e.g. with our other conversion/analysis tools), you need it in a "
        "NumPy-friendly format first — that's what this tool does. It doesn't change any "
        "values, just repackages the same data.\n\n"
        "**What file do I need?** A **choices** file — raw pairwise judgments (someone "
        "picking which of two stimuli looked more similar to a reference). Filenames often "
        "look like `..._choices_..._sess01_10.mat`. If your file is the *output* of a model "
        "fit (coordinates, not raw judgments), this tool isn't the right one for it."
    )

st.markdown(
    "Convert a `.mat` triadic choice file to a 5-column NumPy array."
)
st.info(
    "**Output columns:** `ref, s1, s2, N(s1 chosen), N_repeats` (1-indexed)\n\n"
    "**Example row:** `[3, 7, 12, 8, 10]` reads as: with stimulus 3 as reference, "
    "out of 10 trials comparing stimulus 7 vs. stimulus 12, stimulus 7 was picked "
    "as more similar to the reference 8 times."
)

conv_file = st.file_uploader("Upload .mat choices file", type=["mat"])

if conv_file is not None:
    with tempfile.NamedTemporaryFile(suffix=".mat", delete=False) as tmp:
        tmp.write(conv_file.read())
        tmp_path = tmp.name
    try:
        from convert_mat_to_numpy import mat_to_numpy
        arr, stim_list = mat_to_numpy(tmp_path)

        st.success(f"Loaded: **{arr.shape[0]} trials**, **{len(stim_list)} stimuli**")
        st.markdown(f"**Stimuli:** {', '.join(stim_list[:10])}{'...' if len(stim_list) > 10 else ''}")

        st.dataframe(
            {"ref": arr[:,0].astype(int), "s1": arr[:,1].astype(int),
             "s2": arr[:,2].astype(int), "n_s1_chosen": arr[:,3].astype(int),
             "n_repeats": arr[:,4].astype(int)},
            use_container_width=True, height=300
        )

        out_name = conv_file.name.replace(".mat", ".npy")
        import io
        buf = io.BytesIO()
        np.save(buf, arr)
        st.download_button("Download .npy file", data=buf.getvalue(),
                           file_name=out_name, mime="application/octet-stream")

    except Exception as e:
        st.error(f"Conversion failed: {e}")
    finally:
        os.unlink(tmp_path)
else:
    st.info("Upload a .mat choices file above to get started.")
