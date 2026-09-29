"""
rs_tools — Conversion and analysis utilities for rs-software choice data.

Modules:
    ooo_to_triadic   — convert odd-one-out .mat files to triadic choice format
    mat_to_numpy     — convert triadic choice .mat files to NumPy arrays
    numpy_to_mat     — convert NumPy arrays back to .mat choice files
    compare          — surrogate MDS comparison pipeline
    subset_stimuli   — select a subset of stimuli by index, name, or regex
"""

from .ooo_to_triadic import ooo_to_triadic
from .mat_to_numpy import mat_to_numpy
from .numpy_to_mat import numpy_to_mat
from .subset_stimuli import subset_stimuli

__version__ = "0.1.0"
__all__ = ["ooo_to_triadic", "mat_to_numpy", "numpy_to_mat", "subset_stimuli"]
