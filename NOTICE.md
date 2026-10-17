# NOTICE — Modifications to pyspellchecker

## Upstream

- Project: **pyspellchecker** — <https://github.com/barrust/pyspellchecker>
- Upstream commit used as the baseline: `14ec86570f5cebb5ee2f57499493471fe670dadb` (v0.9.1)
- Copyright: Copyright (c) 2018-2021 Tyler Barrus
- License: **MIT** — the original `LICENSE` file is kept byte-for-byte unchanged.

## What was modified

Only one file was changed: `spellchecker/spellchecker.py`.
No files were added to, or removed from, the distributed package, and no
copyright or license headers were altered.

1. `WordFrequency.__slots__` / `WordFrequency.__init__`
   Added a `_delete_index` slot holding the cached reverse index (`None` = not built).

2. `WordFrequency._get_delete_index()` (new)
   Builds the index lazily on first use and returns it. The index maps every
   dictionary word, and every string obtained by deleting exactly one character
   from a dictionary word, back to the dictionary word(s) that produced it.

3. `WordFrequency._update_dictionary()`
   Added one line that drops the cached index whenever the dictionary changes,
   so the index can never go stale.

4. `SpellChecker.__edit_distance_alt()`
   Replaced the quadratic re-expansion of the edit distance one neighbourhood
   with a lookup into the index above, followed by a linear "at most one edit"
   check on the hits.

5. `SpellChecker.__is_within_one_edit()` / `SpellChecker.__is_one_deletion()` (new)
   Helper predicates used by (4).

Everything else — the public API (`candidates`, `correction`, `known`, `unknown`,
`edit_distance_1`, `edit_distance_2`, `word_frequency`, ...), the return types,
and the behaviour for `distance=1`, case-sensitive dictionaries, numeric input
and diacritics — is unchanged.

## Authorship of the modification

The optimisation described above is an independent contribution, released under
the same MIT license as the upstream project. It is offered as-is, with no
warranty, under the terms of the `LICENSE` file shipped with this package.

See `OPTIMIZATION.md` for the analysis, the measurements and the verification.
