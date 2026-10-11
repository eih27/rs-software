"""
app_subset_choices.py — entry point for the Subset Stimuli app.

This is a thin router: it just declares the app's pages and shows them as a
top navigation bar, then hands off to whichever page is selected. The actual
page content lives in pages/Choice_Subset.py and pages/OOO_Subset.py.

Run locally:
    cd ~/Downloads/rs-software
    streamlit run app_subset_choices.py
"""

import streamlit as st

st.set_page_config(page_title="Subset Stimuli", layout="wide", initial_sidebar_state="expanded")

choice_page = st.Page("pages/Choice_Subset.py", title="Filter choice file (triadic / tetradic)", default=True)
ooo_page = st.Page("pages/OOO_Subset.py", title="Filter choice file (odd-one-out)")

pg = st.navigation([choice_page, ooo_page], position="top")
pg.run()
