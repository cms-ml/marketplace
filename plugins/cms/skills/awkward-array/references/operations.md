# Awkward operations: exact behaviour

Read this reference when you need the precise result of a reduction, slice,
sort or record operation, or when an awkward call returns `None`s or the
wrong shape. Every output below was produced with awkward 2.6.3 (CMSSW_15_0_21)
and 2.8.12 (pip), with identical results.

## Contents

1. [Reductions and counting](#reductions-and-counting)
2. [argmin / argmax and "best candidate"](#argmin--argmax-and-best-candidate)
3. [Option types and None](#option-types-and-none)
4. [Flattening](#flattening)
5. [Sorting](#sorting)
6. [Records and fields](#records-and-fields)
7. [NumPy interop](#numpy-interop)
8. [Functions that do / don't exist](#functions-that-do--dont-exist)

## Reductions and counting

```python
a = ak.Array([[7, 5, 7], [], [2], [8, 2]])
ak.max(a, axis=1)        # [7, None, 2, 8]   (empty list -> None)
ak.min(a, axis=1)        # [5, None, 2, 2]
ak.sum(a, axis=1)        # [19, 0, 2, 10]
ak.sum(a, axis=None)     # 31   (also the default: ak.sum(a) == 31)

b = ak.Array([[1, None, 3], [], [None]])
ak.num(b, axis=1)        # [3, 0, 1]   slots, like len()
ak.count(b, axis=1)      # [2, 0, 0]   non-None values only
```

- `axis=1` reduces within each event and gives one value per event. `axis=None`
  reduces everything to a scalar. Both are legitimate; choose deliberately.
- Reductions over an empty list give `None` for `max`/`min`/`argmax`, and the
  identity (`0`) for `sum`/`count`.
- Weighted sums of NanoAOD `float32` weights: cast first,
  `ak.sum(ak.values_astype(w, np.float64))`. With 2M entries of 0.1, float32
  gives 200000.47 and float64 gives 200000.003.

## argmin / argmax and "best candidate"

```python
a = ak.Array([[7, 5, 7], [], [2], [8, 2]])
i = ak.argmax(a, axis=1, keepdims=True)   # [[0], [None], [0], [0]]
a[i]                                      # [[7], [None], [2], [8]]
ak.firsts(a[i])                           # [7, None, 2, 8]
```

`keepdims=True` keeps a length-1 list per event so the result can be used as
a jagged index. Strip the extra level with `ak.firsts`. Without `keepdims`,
`a[ak.argmax(a, axis=1)]` would index _events_, not objects. Apply the same
index to a whole record (`muons[i]`) to get the best candidate with all its
fields.

## Option types and None

| Produces `None`                          | Example                                     |
| ---------------------------------------- | ------------------------------------------- |
| `ak.firsts(x)` on an empty list          | leading object when there is none           |
| `ak.pad_none(x, n, axis=1)`              | pad to at least `n` per event, then `[:, k]` |
| `ak.mask(x, cond)`                       | keep length, replace failing entries by None |
| `ak.max` / `ak.argmax` on an empty list  | see above                                   |
| Indexing with an option-type index       | `muons.pt[ak.mask(idx, idx >= 0)]`          |

Handle `None` with `ak.fill_none(x, value)`, `ak.is_none(x, axis=...)`, or
`ak.drop_none(x)`. `x[:, 0]` raises `index out of range` if any list is
empty, whereas `ak.pad_none(x, 1, axis=1)[:, 0]` gives `None` there.

`ak.mask(arr, event_cond)` keeps the array length, which is useful to keep
arrays aligned. Boolean indexing `arr[event_cond]` removes events.

## Flattening

```python
ak.flatten(a, axis=1)     # [7, 5, 7, 2, 8, 2]   remove one level
ak.flatten(a, axis=None)  # same here; removes ALL nesting (and drops None)
```

Always pass `axis` explicitly. Flatten pair-level results (e.g. `mll` from
`ak.combinations`) with `axis=1` before histogramming.

## Sorting

```python
ak.sort(a)                       # [[5, 7, 7], [], [2], [2, 8]]   default axis=-1 (innermost)
ak.sort(a, ascending=False)      # [[7, 7, 5], [], [2], [8, 2]]
order = ak.argsort(muons.pt, axis=1, ascending=False)
muons_sorted = muons[order]      # sort whole records by a field
```

## Records and fields

```python
mu = ak.zip({"pt": pt, "eta": eta})                 # jagged record: var * {pt, eta}
mu = ak.with_field(mu, mu.pt * 2, where="pt_x2")    # returns a new array
mu["pt_x2"] = mu.pt * 2                             # same, rebinding mu
ev = ak.zip({"mu": mu}, depth_limit=1)
ev["mu", "is_hard"] = ev.mu.pt > 50                 # nested field
ak.unzip(pairs)                                     # tuple of field arrays
pairs.fields                                        # ['m1', 'm2']
```

- Arrays are immutable views. `arr.newfield = x` raises
  `AttributeError: only private attributes ... can be set on arrays`.
- `ak.zip` broadcasts its inputs. Zipping collections with different
  per-event lengths fails, so zip each collection separately and combine with
  `depth_limit=1`.

## NumPy interop

- NumPy ufuncs work elementwise on jagged arrays: `np.sqrt`, `np.cosh`,
  `np.abs`, `abs()`, arithmetic, comparisons.
- `np.stack([x, y])` works only when the data are rectangular. Jagged input
  raises `cannot convert to RegularArray`.
- `ak.to_numpy(x)` needs rectangular data. Flatten first:
  `ak.to_numpy(ak.flatten(x, axis=1))`.

## Functions that do / don't exist

| Wanted              | Use                                                              |
| ------------------- | ---------------------------------------------------------------- |
| absolute value      | `abs(x)` or `np.abs(x)` (no `ak.abs`)                            |
| max / min per event | `ak.max(x, axis=1)`, `ak.min(x, axis=1)` (they exist)            |
| constant-like array | `ak.full_like(x, v)`, `ak.zeros_like(x)`, `ak.ones_like(x)` (no `ak.fill_like`) |
| take by index       | jagged integer indexing `x[idx]` (no `ak.take`)                  |
| add a dimension     | `x[:, np.newaxis]` or `ak.singletons` (no `ak.expand_dims`)      |
| stack               | `np.stack` on rectangular data (no `ak.stack`)                   |
