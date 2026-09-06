"""
app_ooo.py — Streamlit app for OOO → Triadic conversion.

Run locally:
    cd ~/Downloads/rs-software
    streamlit run app_ooo.py
"""

import sys
import os
import tempfile
import numpy as np
import streamlit as st
from scipy.io import loadmat

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

st.set_page_config(page_title="OOO → Triadic", layout="centered")
st.title("OOO → Triadic Converter")
st.caption(
    "Part of the rs-software toolkit — converts one experiment format into another "
    "so it can be fed into the same coordinate-fitting tools as everything else."
)

with st.expander("New here? What's an odd-one-out experiment, and why convert it?", expanded=False):
    st.markdown(
        "**Odd-one-out (OOO)** is a judgment task: a subject sees **three** stimuli at once "
        "and picks the one that looks most different from the other two — the \"odd one out.\" "
        "This is a different task design from the lab's more common **triadic** task, where a "
        "subject sees a reference plus two others and picks which of the two is *more similar* "
        "to the reference.\n\n"
        "The two tasks produce different data, but they can both be turned into the same "
        "underlying comparison: \"is A closer to the reference than B?\" This tool does that "
        "conversion — every odd-one-out judgment actually implies two of these standard "
        "triadic comparisons, so it gets split into 2 output rows.\n\n"
        "**Why bother?** So the *rest* of the pipeline (fitting coordinates, running "
        "verification, etc.) only ever has to understand one data format, regardless of which "
        "task originally produced the judgments."
    )

st.info(
    "**Input format:** columns `s1, s2, s3, N(s1 odd), N(s2 odd), N(s3 odd)` (1-indexed)\n\n"
    "**Output format:** columns `ref, s1, s2, N(s1 chosen), N_repeats` (1-indexed)\n\n"
    "**Example:** if stimulus 5 was picked as the odd one out (most different) from "
    "{5, 2, 9} on 6 out of 6 trials, that tells us stimulus 2 and stimulus 9 are the two "
    "*similar* ones — so this produces two rows: one saying \"with 2 as reference, 9 was "
    "closer than 5,\" and one saying \"with 9 as reference, 2 was closer than 5.\""
)

ooo_file = st.file_uploader("Upload OOO .mat file", type=["mat"])

if ooo_file is not None:
    with tempfile.NamedTemporaryFile(suffix=".mat", delete=False) as tmp:
        tmp.write(ooo_file.read())
        ooo_tmp = tmp.name
    try:
        from convert_ooo_to_triadic import ooo_to_triadic
        resp_ooo, rep_ooo, stims_ooo = ooo_to_triadic(ooo_tmp, out_path=None)

        _d = loadmat(ooo_tmp)
        n_input_triplets = _d['responses'].shape[0] if 'responses' in _d else None

        st.success(
            f"Converted: **{n_input_triplets} input triplets** → **{len(resp_ooo)} triadic trials** · **{len(stims_ooo)} stimuli**"
        )
        st.markdown(f"**Stimuli:** {', '.join(stims_ooo[:10])}{'...' if len(stims_ooo) > 10 else ''}")

        import pandas as pd
        rows = []
        for (ref_s1, s1), (_, s2) in list(resp_ooo.keys())[:200]:
            key = ((ref_s1, s1), (ref_s1, s2))
            rows.append({
                "ref": ref_s1 + 1, "s1": s1 + 1, "s2": s2 + 1,
                "n_s1_chosen": resp_ooo[key], "n_repeats": rep_ooo[key],
                "ref_name": stims_ooo[ref_s1], "s1_name": stims_ooo[s1], "s2_name": stims_ooo[s2],
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, height=300)

        with tempfile.NamedTemporaryFile(suffix=".mat", delete=False) as out_tmp:
            out_ooo_path = out_tmp.name
        ooo_to_triadic(ooo_tmp, out_path=out_ooo_path)
        with open(out_ooo_path, "rb") as f:
            ooo_bytes = f.read()
        os.unlink(out_ooo_path)

        out_name = ooo_file.name.replace("ooo", "triadic").replace(".mat", "_triadic.mat")
        if "triadic" not in out_name:
            out_name = ooo_file.name.replace(".mat", "_triadic.mat")
        st.download_button("Download triadic .mat", data=ooo_bytes,
                           file_name=out_name, mime="application/octet-stream")

    except Exception as e:
        st.error(f"Conversion failed: {e}")
    finally:
        os.unlink(ooo_tmp)
else:
    st.info("Upload an OOO .mat file above to get started.")
