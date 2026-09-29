"""
subset_stimuli — Select a subset of stimuli from a stimulus list, by index, name, or regex.

This is the format-agnostic core of the stimulus filtering feature (JV, meeting
2026-09-23). It only knows about a plain list of stimulus names -- it has no
idea whether those names came from a choice file (`stim_list`) or a
coordinate file (`stim_labels`). The choice-file and coordinate-file specific
logic (renumbering trials, selecting matching rows in dimN arrays, etc.) is
built on top of this as separate wrappers, so both file types share one
selection implementation instead of two.
"""

import re


def subset_stimuli(stim_list, include=None, exclude=None, regex=None,
                    regex_mode="include", alphabetize=False):
    """
    Decide which stimuli to keep from a stimulus list.

    Exactly one of `include`, `exclude`, or `regex` must be given.

    Args:
        stim_list: list of stimulus names, in their original index order (0-indexed)
        include: list of names and/or 0-indexed integer positions to keep
        exclude: list of names and/or 0-indexed integer positions to drop
        regex: a regex pattern string, matched against each stimulus name
        regex_mode: "include" to keep matches (default), "exclude" to drop matches
        alphabetize: if True, sort the kept names alphabetically;
                     if False (default), keep them in their original order

    Returns:
        kept_names: list of stimulus names that were kept, in the chosen order
        kept_indices: list of each kept name's position in the ORIGINAL stim_list
                       (0-indexed) -- callers use this to select the matching
                       rows/columns in whichever file format they're working with
    """
    modes_given = sum(x is not None for x in (include, exclude, regex))
    if modes_given != 1:
        raise ValueError(
            "Give exactly one of `include`, `exclude`, or `regex` (got {}).".format(modes_given))
    if regex_mode not in ("include", "exclude"):
        raise ValueError("regex_mode must be 'include' or 'exclude', got {!r}.".format(regex_mode))

    name_to_index = {name: i for i, name in enumerate(stim_list)}

    def _resolve(items):
        resolved = set()
        for item in items:
            if isinstance(item, str):
                if item not in name_to_index:
                    raise ValueError(f"Stimulus name not found: {item!r}")
                resolved.add(name_to_index[item])
            else:
                if not (0 <= item < len(stim_list)):
                    raise ValueError(f"Stimulus index out of range: {item}")
                resolved.add(item)
        return resolved

    if include is not None:
        keep = _resolve(include)
    elif exclude is not None:
        keep = set(range(len(stim_list))) - _resolve(exclude)
    else:
        pattern = re.compile(regex)
        matched = {i for i, name in enumerate(stim_list) if pattern.search(name)}
        keep = matched if regex_mode == "include" else set(range(len(stim_list))) - matched

    kept_indices = sorted(keep)
    kept_names = [stim_list[i] for i in kept_indices]

    if alphabetize:
        order = sorted(range(len(kept_names)), key=lambda k: kept_names[k])
        kept_names = [kept_names[k] for k in order]
        kept_indices = [kept_indices[k] for k in order]

    if not kept_names:
        raise ValueError("No stimuli left after filtering -- selection removed everything.")

    return kept_names, kept_indices


def _flatten_indices(key):
    """Recursively collect every stimulus index inside a triadic or tetradic trial key.
    Triadic keys look like ((ref, s1), (ref, s2)); tetradic like ((s1, s2), (s3, s4)).
    Both are just nested tuples of ints, so one recursive walk handles either shape."""
    if isinstance(key, tuple):
        indices = []
        for part in key:
            indices.extend(_flatten_indices(part))
        return indices
    return [key]


def _remap_key(key, old_to_new):
    """Rebuild a trial key with the same nested shape, replacing each index with its new number."""
    if isinstance(key, tuple):
        return tuple(_remap_key(part, old_to_new) for part in key)
    return old_to_new[key]


def subset_choice_file(stim_list, resp, rep, include=None, exclude=None, regex=None,
                        regex_mode="include", alphabetize=False):
    """
    Select a subset of stimuli from a choice file's data, dropping any trial that
    references an excluded stimulus and renumbering the survivors 1..N. Works on
    both triadic and tetradic choice files without needing to know which one it is.

    Args:
        stim_list: list of stimulus names, as returned by load_choices (0-indexed order)
        resp: dict {trial_key: n_chosen}, as returned by load_choices
        rep: dict {trial_key: n_repeats}, as returned by load_choices
        include, exclude, regex, regex_mode, alphabetize: selection options,
            passed straight through to subset_stimuli -- see that function for details

    Returns:
        new_resp: dict, same shape as `resp`, renumbered, with dropped trials removed
        new_rep: dict, same shape as `rep`, renumbered, with dropped trials removed
        kept_names: the surviving stimulus names, in their new index order
    """
    kept_names, kept_indices = subset_stimuli(
        stim_list, include=include, exclude=exclude, regex=regex,
        regex_mode=regex_mode, alphabetize=alphabetize)
    old_to_new = {old_index: new_index for new_index, old_index in enumerate(kept_indices)}

    new_resp, new_rep = {}, {}
    n_dropped = 0
    for key in resp:
        if all(i in old_to_new for i in _flatten_indices(key)):
            new_key = _remap_key(key, old_to_new)
            new_resp[new_key] = resp[key]
            new_rep[new_key] = rep[key]
        else:
            n_dropped += 1

    n_excluded_stim = len(stim_list) - len(kept_names)
    print(f"subset_choice_file: excluded {n_excluded_stim} of {len(stim_list)} stimuli; "
          f"dropped {n_dropped} of {len(resp)} trials that referenced an excluded stimulus "
          f"({len(new_resp)} trials remain)")

    return new_resp, new_rep, kept_names


def save_choice_file(out_path, resp, rep, stim_list, readme_note=""):
    """
    Save a resp/rep/stim_list triple (the format load_choices, subset_choice_file, etc.
    all use) to a .mat choice file. Auto-detects triadic vs tetradic from the shape of
    the trial keys and writes the matching column layout.
    """
    import numpy as np
    from scipy.io import savemat

    if not resp:
        raise ValueError(
            "Cannot save an empty choice file -- no trials remain after filtering. "
            "This can happen with tetradic files if the kept stimuli never appear "
            "together in the same trial.")

    # triadic key: ((ref, s1), (ref, s2)) -- the two halves share the same first element (ref)
    sample_key = next(iter(resp))
    is_triadic = sample_key[0][0] == sample_key[1][0]

    rows = []
    if is_triadic:
        for (ref, s1), (_, s2) in resp:
            key = ((ref, s1), (ref, s2))
            rows.append([ref + 1, s1 + 1, s2 + 1, resp[key], rep[key]])
        colnames = ['ref', 's1', 's2', 'N(D(ref, s1) > D(ref, s2))', 'N_Repeats(D(ref, s1) > D(ref, s2))']
    else:
        for (s1, s2), (s3, s4) in resp:
            key = ((s1, s2), (s3, s4))
            rows.append([s1 + 1, s2 + 1, s3 + 1, s4 + 1, resp[key], rep[key]])
        colnames = ['s1', 's2', 's3', 's4',
                    'N(D(s1, s2) > D(s3, s4))', 'N_Repeats(D(s1, s2) > D(s3, s4))']

    arr = np.array(rows, dtype=np.float64)
    max_len = max(len(s) for s in stim_list)
    savemat(out_path, {
        'responses': arr,
        'responses_colnames': colnames,
        'stim_list': np.array(stim_list, dtype=f'S{max_len}'),
        'readme': readme_note or "Subset of a choice file, produced by subset_choice_file.",
    })
    print(f"Saved: {out_path}  ({len(rows)} trials, {len(stim_list)} stimuli)")


def subset_coords_file(stim_list, coords_by_dim, include=None, exclude=None, regex=None,
                        regex_mode="include", alphabetize=False):
    """
    Select a subset of stimuli from a coordinates file's data -- keeps the matching
    row in every dimN array, for every fitted dimensionality at once.

    Args:
        stim_list: list of stimulus names (as returned by coords_to_numpy)
        coords_by_dim: dict {dim: array of shape (n_stimuli, dim)}, as returned by
            coords_to_numpy -- one array per fitted dimensionality
        include, exclude, regex, regex_mode, alphabetize: selection options,
            passed straight through to subset_stimuli

    Returns:
        new_coords_by_dim: dict, same dims, each array's rows filtered/reordered to match kept_names
        kept_names: the surviving stimulus names, in their new index order
    """
    kept_names, kept_indices = subset_stimuli(
        stim_list, include=include, exclude=exclude, regex=regex,
        regex_mode=regex_mode, alphabetize=alphabetize)

    new_coords_by_dim = {dim: arr[kept_indices, :] for dim, arr in coords_by_dim.items()}

    n_excluded_stim = len(stim_list) - len(kept_names)
    print(f"subset_coords_file: excluded {n_excluded_stim} of {len(stim_list)} stimuli "
          f"({len(kept_names)} remain), across {len(coords_by_dim)} fitted dimension(s)")

    return new_coords_by_dim, kept_names


def save_coords_file(out_path, coords_by_dim, stim_list, extra_fields=None):
    """
    Save a coords_by_dim/stim_list pair (the format coords_to_numpy, subset_coords_file,
    etc. all use) to a .mat coordinates file.

    Args:
        out_path: where to save the .mat file
        coords_by_dim: dict {dim: array of shape (n_stimuli, dim)}
        stim_list: list of stimulus names, in the same row order as coords_by_dim
        extra_fields: optional dict of additional fields to carry over from the
            original file (e.g. rawLLs, bestModelLL, biasEstimate). These describe
            the ORIGINAL fit across all stimuli, not this subset, so a note is
            added to the readme explaining that, rather than silently dropping or
            silently passing them off as describing the subset.
    """
    import numpy as np
    from scipy.io import savemat

    if not coords_by_dim:
        raise ValueError("Cannot save an empty coordinates file -- no fitted dimensions given.")

    data = {}
    for dim, arr in coords_by_dim.items():
        data[f"dim{dim}"] = arr

    max_len = max(len(s) for s in stim_list)
    data['stim_labels'] = np.array(stim_list, dtype=f'S{max_len}')

    readme_parts = ["Subset of a coordinates file, produced by subset_coords_file."]
    if extra_fields:
        for key, value in extra_fields.items():
            data[key] = value
        readme_parts.append(
            "Note: " + ", ".join(sorted(extra_fields)) +
            " (if present) describe the ORIGINAL fit across all stimuli, not this subset."
        )
    data['readme'] = " ".join(readme_parts)

    savemat(out_path, data)
    print(f"Saved: {out_path}  ({len(stim_list)} stimuli, dims {sorted(coords_by_dim)})")
