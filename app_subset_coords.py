"""
app_subset_coords.py — entry point for the Subset Stimuli app.

This is a thin router: it declares the app's three pages and shows them as a
top navigation bar, then hands off to whichever page is selected. The page
content lives in pages/Choice_Subset.py, pages/OOO_Subset.py and
pages/Coords_Subset.py. Both entry points show the same pages; only the page
that opens first differs.

Run locally:
    cd ~/Downloads/rs-software
    streamlit run app_subset_coords.py
"""

import streamlit as st

st.set_page_config(page_title="Subset Stimuli", layout="wide", initial_sidebar_state="expanded")

choice_page = st.Page("pages/Choice_Subset.py", title="Filter a choice file by stimuli")
ooo_page = st.Page("pages/OOO_Subset.py", title="Filter an odd-one-out choice file by stimuli")
coords_page = st.Page("pages/Coords_Subset.py", title="Filter a coordinate file by stimuli", default=True)

pg = st.navigation([coords_page, choice_page, ooo_page], position="top")
pg.run()
