# CMS-style plotting with hist + mplhep

Read this reference when making CMS-style plots: experiment labels, stacked
MC with data, ratio panels, 2D histograms, or when plotting code behaves
differently between CMSSW and a pip environment. Tested with mplhep 0.3.47
(CMSSW_15_0_21) and 1.1.3 (pip), on CMS Open Data NanoAOD.

## Contents

1. [Versions](#versions)
2. [CMS label](#cms-label)
3. [Stack + data + ratio](#stack--data--ratio)
4. [2D histograms](#2d-histograms)
5. [Saving](#saving)

## Versions

| Environment   | hist  | boost-histogram | mplhep | matplotlib | `histtype` values                          |
| ------------- | ----- | --------------- | ------ | ---------- | ------------------------------------------ |
| CMSSW_15_0_21 | 2.7.2 | 1.4.1           | 0.3.47 | 3.8.4      | `fill, step, errorbar, band`               |
| pip (2026-10) | 2.9.2 | 1.6.1           | 1.1.3  | 3.9.4      | `fill, step, errorbar, band, bar, barstep` |

Write code that uses only the common set to run in both.

## CMS label

```python
plt.style.use(hep.style.CMS)
hep.cms.label("Preliminary", data=True, lumi=16.8, com=13, ax=ax)   # "CMS Preliminary", "16.8 fb^-1 (13 TeV)"
hep.cms.label("Open Data", data=False, com=13, ax=ax)               # "CMS Simulation Open Data", "(13 TeV)"
```

- `data=False` adds "Simulation". `lumi` is in fb⁻¹, and `com` is √s in TeV
  (13.6 for Run 3).
- The first argument is the extra text ("Preliminary", "Work in progress",
  "Private work"). Follow your group's rules for what may be shown.

## Stack + data + ratio

```python
fig, (ax, rax) = plt.subplots(2, 1, sharex=True, gridspec_kw={"height_ratios": [3, 1]})
mc = [h[:, "SR", p, "nominal"] for p in ["ttbar", "DY"]]
hep.histplot(mc, ax=ax, stack=True, histtype="fill", label=["ttbar", "DY"])
hep.histplot(h_data, ax=ax, histtype="errorbar", color="black", label="Data")
hep.cms.label("Preliminary", data=True, lumi=16.8, com=13, ax=ax)
ax.legend()

ax.set_xlabel("")                                   # x title only on the ratio panel

tot = sum(x.values() for x in mc)
d = h_data.values()
ok = (tot > 0) & (d > 0)
ratio = np.divide(d, tot, out=np.full_like(d, np.nan, dtype=float), where=ok)
err = np.divide(np.sqrt(d), tot, out=np.full_like(d, np.nan, dtype=float), where=ok)
rax.errorbar(h_data.axes[0].centers, ratio, yerr=err, fmt="o", color="black")
rax.axhline(1, ls="--", color="gray")
rax.set_ylabel("Data / MC")
rax.set_xlabel(h_data.axes[0].label)
```

- `hep.histplot` accepts a list of histograms with `stack=True`.
- Use NaN (not 0) for bins with no data or no MC. NaN points aren't drawn,
  whereas 0 shows up as a misleading point at the bottom of the ratio panel.

## 2D histograms

```python
h2 = Hist.new.Reg(50, 0, 200, name="pt", label=r"$p_{T}$ [GeV]").Reg(48, -2.4, 2.4, name="eta", label=r"$\eta$").Weight()
h2.fill(pt=pt_flat, eta=eta_flat, weight=w_flat)
fig, ax = plt.subplots()
hep.hist2dplot(h2, ax=ax)
```

Note the module name: with `import mplhep as hep`, call `hep.hist2dplot`, not
`mplhep.hist2dplot`.

## Saving

```python
fig.savefig("plot.png")          # and/or .pdf for papers/notes
plt.close(fig)                   # free memory in loops
```

Use `matplotlib.use("Agg")` (before importing pyplot) in batch jobs or ssh
sessions without a display.
