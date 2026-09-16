"""
app_matnpy.py — Streamlit app for .mat → NumPy conversion.

Run locally:
    cd ~/Downloads/rs-software
    streamlit run app_matnpy.py
"""

import sys
import os
import io
import tempfile
import numpy as np
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

st.set_page_config(page_title=".mat → NumPy", layout="centered")
st.title(".mat → NumPy Converter")
st.caption(
    "Part of the rs-software toolkit — converts a MATLAB/Octave `.mat` file "
    "into a NumPy format, so the same data can be used in Python without MATLAB."
)

with st.expander("New here? What is this, and what file do I need?", expanded=False):
    st.markdown(
        "This lab's data comes out of MATLAB/Octave as `.mat` files. To work with that data "
        "in Python (e.g. with our other conversion/analysis tools), you need it in a "
        "NumPy-friendly format first — that's what this tool does. It doesn't change any "
        "values, just repackages the same data.\n\n"
        "**What file do I need?** Either a **choices** file — raw pairwise judgments "
        "(filenames often look like `..._choices_..._sess01_10.mat`) — or a **coordinates** "
        "file — the output of a model fit (filenames often look like `..._coords_....mat`). "
        "The tool figures out which one you gave it automatically."
    )

conv_file = st.file_uploader("Upload .mat file (choices or coordinates)", type=["mat"])

if conv_file is not None:
    with tempfile.NamedTemporaryFile(suffix=".mat", delete=False) as tmp:
        tmp.write(conv_file.read())
        tmp_path = tmp.name
    try:
        from convert_mat_to_numpy import mat_file_kind, mat_to_numpy, coords_to_numpy

        kind = mat_file_kind(tmp_path)

        if kind == 'choices':
            st.markdown("Detected a **choices** file — converting to a 5-column NumPy array.")
            st.info(
                "**Output columns:** `ref, s1, s2, N(s1 chosen), N_repeats` (1-indexed)\n\n"
                "**Example row:** `[3, 7, 12, 8, 10]` reads as: with stimulus 3 as reference, "
                "out of 10 trials comparing stimulus 7 vs. stimulus 12, stimulus 7 was picked "
                "as more similar to the reference 8 times."
            )

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
            buf = io.BytesIO()
            np.save(buf, arr)
            st.download_button("Download .npy file", data=buf.getvalue(),
                               file_name=out_name, mime="application/octet-stream")

        elif kind == 'coords':
            st.markdown("Detected a **coordinates** file — converting to a NumPy array.")

            coords_by_dim, stim_list = coords_to_numpy(tmp_path)
            available_dims = sorted(coords_by_dim.keys())

            st.success(f"Loaded: **{len(stim_list)} stimuli**, fitted dimensionalities: "
                       f"**{', '.join(str(d) for d in available_dims)}**")

            if len(available_dims) > 1:
                chosen_dim = st.selectbox("Which dimensionality's coordinates do you want?",
                                          available_dims)
            else:
                chosen_dim = available_dims[0]

            arr = coords_by_dim[chosen_dim]
            st.markdown(f"**{chosen_dim}D coordinates** — shape `{arr.shape}` (rows=stimuli, columns=dimensions)")

            preview = {"stimulus": stim_list}
            for d in range(chosen_dim):
                preview[f"dim{d+1}"] = arr[:, d]
            st.dataframe(preview, use_container_width=True, height=300)

            out_name = conv_file.name.replace(".mat", f"_dim{chosen_dim}.npy")
            buf = io.BytesIO()
            np.save(buf, arr)
            st.download_button("Download .npy file", data=buf.getvalue(),
                               file_name=out_name, mime="application/octet-stream")

        else:
            st.error(
                "Couldn't tell whether this is a choices file or a coordinates file — "
                "it doesn't have the fields either format expects (`responses` for choices, "
                "`dimN` for coordinates)."
            )

    except Exception as e:
        st.error(f"Conversion failed: {e}")
    finally:
        os.unlink(tmp_path)
else:
    st.info("Upload a .mat file above to get started (choices or coordinates).")
