# Speeding up `pyspellchecker`'s distance-2 lookup

**Project**: [barrust/pyspellchecker](https://github.com/barrust/pyspellchecker)
**License**: MIT (unchanged) · **Baseline commit**: `14ec8657` (v0.9.1)
**Changed file**: `spellchecker/spellchecker.py` (only)
**Upstream test suite**: 59 passed before, 59 passed after

---

## 1. The defect

`SpellChecker.candidates(word)` tries, in order:

1. the word itself — if it is in the dictionary, return it;
2. every string one edit away (delete / transpose / substitute / insert) — if any
   of them is in the dictionary, return those;
3. otherwise, every string **two** edits away.

Step 3 is where the time goes. It is implemented as a second, full expansion of
the edit-distance-one neighbourhood:

```python
def __edit_distance_alt(self, words):
    tmp = [w if self._case_sensitive else w.lower() for w in words if self._check_if_should_check(w)]
    return [e2 for e1 in tmp for e2 in self.known(self.edit_distance_1(e1))]
```

For the English dictionary (160,572 words, 45 distinct characters) the
edit-distance-one neighbourhood of a 10-letter word is **943 strings**. Growing
each of those a second time means building and dictionary-testing

```
943 × 943 ≈ 8.9 × 10^5   strings, for that one input word
```

and instrumenting 150 real two-edit typos gives an average of **6.0 × 10^5**
strings constructed per query. Measured directly on this machine:

| input                  | len | \|E1\| | `__edit_distance_alt` | candidates found |
| ---------------------- | --- | -----: | --------------------: | ---------------: |
| `"accomodate"`         | 10  |    943 | 578.3 ms              | 98               |
| `"recieve"`            | 7   |    675 | 325.2 ms              | 106              |
| `"maintainance"`       | 12  |  1,125 | 886.4 ms              | 6                |
| `"questionaire"`       | 12  |  1,125 | 828.7 ms              | 100              |

**A single misspelled word costs between a third of a second and a full second.**
Correcting a document is therefore unusable in practice.

### Which distance is it, really?

The candidate set is `{ w : d(word, w) ≤ 2 }`, but `d` is **not** Levenshtein and
**not** OSA. Because the two edits are generated layer by layer, a delete may be
followed by a transposition of two characters that were *not* adjacent in the
original word — exactly the case OSA forbids:

```
alot -> aot (delete 'l') -> oat (transpose 'a','o')     # 2 edits, OSA says 3
```

Verified against the upstream code: `"oat"` **is** returned as a candidate for
`"alot"`. So the distance is unrestricted **Damerau-Levenshtein**. Any
replacement has to match this, or it silently loses candidates.

## 2. The fix

A delete-variant reverse index (`WordFrequency._get_delete_index`):

- every dictionary word `w` is indexed under `w` itself, and under each
  `w[:i] + w[i+1:]`;
- reading `index[t]` therefore answers *"which dictionary words are one insertion
  away from `t`?"* in O(1).

The key fact that makes this exact rather than approximate:

> If two strings are at Damerau-Levenshtein distance ≤ 1, their sets of
> "at most one deletion" variants intersect.

So for every one-edit variant `e1`, the words at distance ≤ 1 from `e1` are
exactly the union of `index[t]` over `t ∈ deletes≤1(e1)`. Step 3 becomes:

```python
for e1 in edit_distance_1(word):
    hits |= index[e1]                       # every entry is at most one insertion away
    for t in deletes_of(e1):
        hits |= {w for w in index[t] if within_one_edit(e1, w)}
```

`within_one_edit` is a linear O(n) test (single substitution, adjacent
transposition, or single insertion/deletion) — not a DP — and it is only run on
the handful of entries the index actually returns.

Cost per query: `|E1| × (L+1)` ≈ **8,136** index lookups instead of
`|E1|²` ≈ **6×10^5** string constructions.

Two implementation choices worth noting:

- **Only one deletion is indexed**, not two. A two-delete index would cut the
  query side from ~8,000 lookups to a few dozen, but it needs 7,678,646 entries
  — 4.9× the 1-delete index, i.e. on the order of half a gigabyte of RAM at the
  density measured below (102.6 MB × 4.9). That is not an acceptable price for a
  pure-Python spell checker. Hopping through `edit_distance_1` first buys the
  same completeness for 1,369,364 entries.
- **A bucket stores a bare string while only one word maps to it** and only
  becomes a list on the second word. That halves the index's memory
  (+102.6 MB vs +201.6 MB) and builds it faster (0.79 s vs 1.20 s).

The index is built lazily on the first distance-2 query and dropped whenever the
dictionary is modified (`load_words`, `add`, `remove`, …).

## 3. Measurements

Environment: Windows, CPython 3.13.14, English dictionary from the package
(160,572 words). Nothing below is estimated — every number is a measurement.

### 3.1 Wall clock, whole batch (2,100 queries, one process per implementation)

| query class                    | n   | upstream  | optimized | speed-up |
| ------------------------------ | --- | --------- | --------- | -------- |
| already-correct words          | 300 | 0.62 ms   | 0.66 ms   | ~1×      |
| 1-edit typos                   | 600 | 305.9 ms  | 298.0 ms  | ~1×      |
| 2-edit typos                   | 800 | 415.96 s  | 3.97 s    | **105×** |
| random letter strings          | 400 | 92.92 s   | 0.92 s    | **101×** |
| **total**                      |2100 | 509.19 s  | 5.18 s    | **98×**  |

Per word, the distance-2 case drops from **519.9 ms to 4.96 ms**.

### 3.2 Wall clock, interleaved A/B (fresh process per run, order reversed on odd rounds)

40 distance-2 queries, 7 rounds:

| | upstream (median) | optimized (median) | ratio |
| --- | --- | --- | --- |
| ms per round | 15,573 | 146.5 | **106.5×** (min 94.4×, max 181.1×) |

Noise floor — the *same* optimised code measured against itself in the same
harness: **median 1.003× (0.956× – 1.140×)**. The effect is three orders of
magnitude above the noise.

Round 0 of upstream was 26.0 s vs ~15 s later (cold caches); the median is used
precisely so that this does not inflate the ratio.

### 3.3 Work counters (deterministic, not a stopwatch)

150 distance-2 queries, instrumented by wrapping `edit_distance_1`,
`known()` and `_check_if_should_check`:

| counter                                     | upstream    | optimized | ratio  |
| ------------------------------------------- | ----------- | --------- | ------ |
| `edit_distance_1` calls                     | 99,040      | 145       | 683×   |
| strings built through `edit_distance_1`     | 90,445,606  | 115,717   | 782×   |
| index keys built (≈ lookups)                | —           | 1,220,336 | —      |
| **strings constructed in total**            | ~90.4 M     | ~1.34 M   | **68×**|
| `_check_if_should_check` calls              | 201,176     | 1,015     | 198×   |

### 3.4 Cost of the fix

| | value |
| --- | --- |
| index build (one-off, first distance-2 query) | 0.79 s |
| index size                                    | 1,369,364 entries |
| resident memory 43.4 MB → 145.9 MB            | **+102.6 MB** |
| memory if a list were stored per entry        | +201.6 MB (rejected) |
| cost for already-correct / 1-edit words       | none — index is never built |

The trade-off is explicit: ~100 MB of memory and a one-off 0.8 s build buy a
100× reduction on the path that used to cost half a second per word.

## 4. Equivalence — this returns *exactly* the same candidates

### 4.1 Real dictionary, 2,100 queries

Same seed-generated inputs (300 correct, 600 one-edit, 800 two-edit, 400 random),
each implementation in its own process, results compared element by element:

```
correct  300/300 identical
dist1    600/600 identical
dist2    800/800 identical
junk     400/400 identical
TOTAL   2100/2100 identical, 0 differences
```

### 4.2 Exhaustive sweeps on a small dictionary

Exhaustive is stronger than sampling: on a 13–21 word dictionary the harness
feeds *every* string over the alphabet up to length 6–7 to both implementations.

| configuration                                   | queries | differences |
| ----------------------------------------------- | ------: | ----------: |
| alphabet `abcd`, len 0–7, distance 2            |  21,845 |           0 |
| alphabet `abcd`, len 0–7, case-sensitive        |  21,845 |           0 |
| alphabet `abcde`, len 0–6, distance 2           |  19,531 |           0 |
| alphabet `abcd`, len 0–6, **distance 1**        |   5,461 |           0 |
| alphabet `abcd1`, len 0–6, numeric/punct. words |  19,531 |           0 |
| alphabet `abcd`, len 0–6, numeric/punct. words  |   5,461 |           0 |
| **total**                                       |**71,829**|     **0**  |

### 4.3 The comparison itself was poison-tested

An equivalence harness that always passes proves nothing. Disabling the
"at most one edit" verification in the optimised build (accepting every index
hit) makes the same harness report **hundreds of mismatches**, e.g.
`bda → ['abab', 'abc', 'abcd', 'dabc']` that upstream never returns. The
0-difference results above are therefore meaningful.

### 4.4 Upstream checks

- `pytest tests` — 59 passed on the baseline, 59 passed on the modified tree.
- `ruff check` and `ruff format --check` (the upstream Ruff workflow) — clean.

## 5. Reproducing

```bash
pip install pytest psutil ruff

# upstream vs optimised tests
cd upstream   && pytest tests -q     # 59 passed
cd ../optimized && pytest tests -q   # 59 passed

# determinism / equivalence
python bench/gen_words.py bench/words.json
python bench/run_queries.py <upstream dir>   bench/words.json bench/res_upstream.json
python bench/run_queries.py <optimized dir>  bench/words.json bench/res_optimized.json
python bench/compare.py

# exhaustive sweep on a small dictionary (add --poison to see it catch a bug)
python bench/exhaustive.py --alpha abcd --maxlen 7

# interleaved timing with a noise floor
python bench/drive.py dist2 7 40

# deterministic work counters
python bench/count_ops.py <pkg dir> bench/words.json dist2 150
```
