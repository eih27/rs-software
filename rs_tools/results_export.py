"""
results_export -- save a surrogate MDS comparison as a machine-readable file.

One result record describes one comparison of two datasets: the settings used, the real
disparity and log-likelihoods, every surrogate disparity, and the p-value. The same record
is written by the Surrogate MDS app (Download results buttons) and by the batch script
(rs_tools/run_comparison.py), so results from either can be collected into one table.

Formats (chosen by file extension):
    .json   readable anywhere; arrays are lists
    .mat    MATLAB / Octave; fields are variables
    .npz    NumPy; each field is an array (load with allow_pickle=False)

Collect many runs into one table:
    python -m rs_tools.results_export summarize results/*.json --csv all_runs.csv

p-values: `p_value` is the fraction of surrogates with disparity >= the real disparity, as
the app shows it. With n surrogates it can only take values k/n, so 0 means "none of the n
surrogates reached the real value", not "impossible". `p_value_plus_one` = (k + 1) / (n + 1)
is the conservative estimate that is never 0.
"""

import csv
import datetime
import io
import json
import math
import os
import subprocess
import sys

import numpy as np

SCALAR_FIELDS = [
    "source", "created_utc", "software_version", "git_commit",
    "dataset1", "dataset2", "file1", "file2",
    "dim", "n_surrogates", "max_iterations_real", "max_iterations_surrogate",
    "learning_rate", "resample_method", "warm_start", "seed_mode",
    "n_shared_stimuli", "n_triads1", "n_triads2",
    "real_disparity", "real_ll1", "real_ll2",
    "surrogate_mean", "surrogate_std", "n_surrogates_ge_real",
    "p_value", "p_value_plus_one",
]
ARRAY_FIELDS = ["surrogate_disparities", "surrogate_ll1", "surrogate_ll2"]
SUMMARY_COLUMNS = [
    "dataset1", "dataset2", "dim", "n_surrogates", "max_iterations_real",
    "max_iterations_surrogate", "resample_method", "real_disparity", "surrogate_mean",
    "surrogate_std", "p_value", "p_value_plus_one", "real_ll1", "real_ll2", "source",
    "created_utc",
]


def _git_commit():
    try:
        here = os.path.dirname(os.path.abspath(__file__))
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=here,
                             capture_output=True, text=True, timeout=5)
        return out.stdout.strip() or None
    except Exception:
        return None


def _software_version():
    try:
        from . import __version__
        return __version__
    except Exception:
        return None


def build_record(*, source, dataset1, dataset2, dim, n_surrogates, real_disparity,
                 surrogate_disparities, real_ll1=None, real_ll2=None,
                 surrogate_ll1=None, surrogate_ll2=None, file1=None, file2=None,
                 max_iterations_real=None, max_iterations_surrogate=None,
                 learning_rate=None, resample_method=None, warm_start=None,
                 seed_mode=None, n_shared_stimuli=None, n_triads1=None, n_triads2=None):
    """Assemble one result record. Fields that do not apply may be left as None."""
    disparities = np.asarray(surrogate_disparities, dtype=float).ravel()
    n_ge = int(np.sum(disparities >= real_disparity))
    n = len(disparities)
    record = {
        "source": source,
        "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "software_version": _software_version(),
        "git_commit": _git_commit(),
        "dataset1": dataset1, "dataset2": dataset2, "file1": file1, "file2": file2,
        "dim": int(dim), "n_surrogates": int(n_surrogates),
        "max_iterations_real": max_iterations_real,
        "max_iterations_surrogate": max_iterations_surrogate,
        "learning_rate": learning_rate, "resample_method": resample_method,
        "warm_start": None if warm_start is None else bool(warm_start),
        "seed_mode": seed_mode, "n_shared_stimuli": n_shared_stimuli,
        "n_triads1": n_triads1, "n_triads2": n_triads2,
        "real_disparity": float(real_disparity),
        "real_ll1": None if real_ll1 is None else float(real_ll1),
        "real_ll2": None if real_ll2 is None else float(real_ll2),
        "surrogate_mean": float(disparities.mean()) if n else None,
        "surrogate_std": float(disparities.std()) if n else None,
        "n_surrogates_ge_real": n_ge,
        "p_value": float(n_ge / n) if n else None,
        "p_value_plus_one": float((n_ge + 1) / (n + 1)) if n else None,
        "surrogate_disparities": disparities,
        "surrogate_ll1": None if surrogate_ll1 is None else np.asarray(surrogate_ll1, dtype=float).ravel(),
        "surrogate_ll2": None if surrogate_ll2 is None else np.asarray(surrogate_ll2, dtype=float).ravel(),
    }
    return record


def _json_safe(value):
    if isinstance(value, np.ndarray):
        return [_json_safe(v) for v in value.tolist()]
    if isinstance(value, (np.floating, float)):
        return None if (math.isnan(value) or math.isinf(value)) else float(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    return value


def record_bytes(record, fmt):
    """Serialize a record to bytes for fmt in {'json', 'mat', 'npz'}."""
    fmt = fmt.lower().lstrip(".")
    present = {k: v for k, v in record.items() if v is not None}
    if fmt == "json":
        text = json.dumps({k: _json_safe(v) for k, v in record.items()}, indent=2)
        return text.encode("utf-8")
    buf = io.BytesIO()
    if fmt == "npz":
        np.savez(buf, **{k: np.asarray(v) for k, v in present.items()})
    elif fmt == "mat":
        from scipy.io import savemat
        data = {k: (np.asarray(v, dtype=float).reshape(-1, 1) if k in ARRAY_FIELDS
                    else (int(v) if isinstance(v, bool) else v))
                for k, v in present.items()}
        savemat(buf, data, do_compression=True)
    else:
        raise ValueError(f"Unknown format {fmt!r}; use json, mat or npz.")
    return buf.getvalue()


def save_record(record, path):
    """Write a record to path; the extension (.json, .mat, .npz) picks the format."""
    fmt = os.path.splitext(str(path))[1]
    with open(path, "wb") as f:
        f.write(record_bytes(record, fmt))


def load_record(path):
    """Read a record written by save_record back into a dict (arrays as numpy arrays)."""
    ext = os.path.splitext(str(path))[1].lower()
    if ext == ".json":
        with open(path) as f:
            raw = json.load(f)
        return {k: (np.array(v, dtype=float) if k in ARRAY_FIELDS and v is not None else v)
                for k, v in raw.items()}
    if ext == ".npz":
        with np.load(path, allow_pickle=False) as z:
            return {k: (z[k] if k in ARRAY_FIELDS else z[k].item()) for k in z.files}
    if ext == ".mat":
        from scipy.io import loadmat
        raw = loadmat(path, squeeze_me=True)
        return {k: (np.atleast_1d(v) if k in ARRAY_FIELDS else (v.item() if hasattr(v, "item") else v))
                for k, v in raw.items() if not k.startswith("__")}
    raise ValueError(f"Unknown file type {ext!r}; use .json, .mat or .npz.")


def summarize(paths, csv_path=None):
    """One row per result file, with the columns in SUMMARY_COLUMNS. Optionally write a CSV."""
    rows = []
    for p in paths:
        rec = load_record(p)
        row = {c: rec.get(c) for c in SUMMARY_COLUMNS}
        row["file"] = os.path.basename(p)
        rows.append(row)
    if csv_path:
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["file"] + SUMMARY_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
    return rows


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(prog="python -m rs_tools.results_export")
    sub = parser.add_subparsers(dest="command", required=True)
    s = sub.add_parser("summarize", help="collect result files into one table")
    s.add_argument("files", nargs="+")
    s.add_argument("--csv", help="write the table to this CSV file")
    args = parser.parse_args(argv)
    rows = summarize(args.files, args.csv)
    for r in rows:
        print(f"{r['file']}: {r['dataset1']} vs {r['dataset2']}  {r['dim']}D  "
              f"disparity {r['real_disparity']:.4f}  p={r['p_value']:.4f}  "
              f"(p+1={r['p_value_plus_one']:.4f}, {r['n_surrogates']} surrogates)")
    if args.csv:
        print(f"Wrote {args.csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
