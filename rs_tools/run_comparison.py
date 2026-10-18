"""
run_comparison -- run surrogate MDS comparisons from the command line and save each one
as a machine-readable result file (see results_export.py for the file contents).

One call can cover several dimensions and resampling methods; each combination becomes
its own file. Re-running skips combinations that already have a file (--overwrite to redo).

Example (JV's pilot: standard vs brightness task, 3D and 4D, three resampling methods):
    python -m rs_tools.run_comparison \\
        --file1 dgea3pt_choices_MC_sess01_10.mat --file2 dgea3pt_choices_MC-br_sess01_10.mat \\
        --dims 3 4 --methods all --surrogates 100 --max-iter 1000 --out-dir results/

Collect the finished runs into one table:
    python -m rs_tools.results_export summarize results/*.json --csv results/all_runs.csv

This uses compare() in rs_tools/compare.py, which is a separate implementation from the
Surrogate MDS web app (app.py): the web app also stores each surrogate's log-likelihood;
these files leave surrogate_ll1/ll2 empty.
"""

import argparse
import os
import sys
import time

from .compare import compare
from .results_export import build_record, save_record

METHODS = ["with_replacement", "without_replacement", "without_replacement_paired"]


def _name(path):
    return os.path.basename(path).replace("_suniyya.mat", "").replace(".mat", "")


def run_one(file1, file2, dim, method, n_surrogates, real_max_iter, surr_max_iter,
            workers, out_dir, formats, overwrite=False, verbose=True):
    from src.rs_py.utils.util import load_choices

    name1, name2 = _name(file1), _name(file2)
    stem = f"{name1}_vs_{name2}_{dim}d_{n_surrogates}surr_{method}_{real_max_iter}it"
    paths = [os.path.join(out_dir, f"{stem}.{fmt}") for fmt in formats]
    if not overwrite and all(os.path.exists(p) for p in paths):
        print(f"skip (already done): {stem}")
        return paths

    resp1, rep1, _, stims1 = load_choices(file1)
    resp2, rep2, _, stims2 = load_choices(file2)
    start = time.time()
    result = compare(resp1, rep1, stims1, resp2, rep2, stims2, dim=dim,
                     n_surrogates=n_surrogates, real_max_iter=real_max_iter,
                     surr_max_iter=surr_max_iter, resample_method=method,
                     n_workers=workers, verbose=verbose)
    record = build_record(
        source="rs_tools.run_comparison (compare)", dataset1=name1, dataset2=name2,
        file1=os.path.basename(file1), file2=os.path.basename(file2), dim=dim,
        n_surrogates=n_surrogates, max_iterations_real=real_max_iter,
        max_iterations_surrogate=surr_max_iter, resample_method=method, warm_start=True,
        n_shared_stimuli=result["n_shared"], n_triads1=sum(rep1.values()), n_triads2=sum(rep2.values()),
        real_disparity=result["real_disp"], real_ll1=result["real_ll1"], real_ll2=result["real_ll2"],
        surrogate_disparities=result["surrogate_disparities"])
    os.makedirs(out_dir, exist_ok=True)
    for p in paths:
        save_record(record, p)
    print(f"done in {time.time() - start:.0f}s: {stem}  disparity {record['real_disparity']:.4f}  "
          f"p={record['p_value']:.4f}")
    return paths


def build_parser():
    p = argparse.ArgumentParser(prog="python -m rs_tools.run_comparison",
                                description="Surrogate MDS comparison, saved as result files.")
    p.add_argument("--file1", required=True, help="first choice file (.mat)")
    p.add_argument("--file2", required=True, help="second choice file (.mat)")
    p.add_argument("--dims", type=int, nargs="+", default=[3], help="dimensions, e.g. --dims 3 4")
    p.add_argument("--methods", nargs="+", default=["with_replacement"],
                   help=f"resampling methods ({', '.join(METHODS)}) or 'all'")
    p.add_argument("--surrogates", type=int, default=100)
    p.add_argument("--max-iter", type=int, default=2000, help="iterations for the real fits")
    p.add_argument("--surr-max-iter", type=int, default=None,
                   help="iterations for surrogate fits (default: same as --max-iter)")
    p.add_argument("--workers", type=int, default=4, help="parallel threads for surrogates")
    p.add_argument("--out-dir", default="results")
    p.add_argument("--formats", nargs="+", default=["json"], choices=["json", "mat", "npz"])
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--quiet", action="store_true")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    methods = METHODS if args.methods == ["all"] else args.methods
    for m in methods:
        if m not in METHODS:
            print(f"error: unknown method {m!r}; use one of {METHODS} or 'all'", file=sys.stderr)
            return 2
    for dim in args.dims:
        for method in methods:
            run_one(args.file1, args.file2, dim, method, args.surrogates, args.max_iter,
                    args.surr_max_iter or args.max_iter, args.workers, args.out_dir,
                    args.formats, args.overwrite, verbose=not args.quiet)
    return 0


if __name__ == "__main__":
    sys.exit(main())
