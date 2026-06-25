---
name: nature-electrochem-figures
description: Use this skill when generating publication-quality scientific figures, especially electrochemistry figures, from MicroHySeeker, CHI, or generic CSV data. It defines Nature-like visual habits: palette selection, typography, line weights, marker usage, axes, legends, figure sizing, export settings, and specialized rules for CV, LSV, i-t, ADT, before/after comparisons, and general time-series/scatter/summary plots.
---

# Nature Electrochemistry Figures

## Goal

Create clean, publication-quality scientific figures that match the MicroHySeeker Nature-like style. This is a plotting style and habit guide, not only an ADT recipe.

Core visual habits:

- White background.
- Thin black axes.
- No default grid; use subtle reference lines only when they carry meaning.
- Low-saturation colors, never neon or default matplotlib blue/orange.
- Small, consistent typography.
- Compact, frameless legends.
- Thin lines with occasional open markers when the trace would otherwise look too plain.
- Explicit physical units in every axis label.
- Save at publication resolution, usually 300 dpi.
- Keep charts legible when embedded in a paper column, not only when viewed full screen.

Specialized electrochemistry habits:

- Open-circle markers for CV, LSV, i-t, and before/after comparisons.
- Long horizontal layout for long ADT/time-series program and response plots.
- For ADT response, current uses the left y-axis and potential uses the right y-axis, with both axes sharing the same visual zero level.

## Inputs

Use this skill for CSV files with one of these layouts.

CV or LSV:

```text
Potential/V, Current/A
```

i-t:

```text
Time/sec, Current/A
```

ADT:

```text
time(s), potential(V), current(A), cycle, phase, set_current(A), set_potential(V)
```

For ADT, `phase=0` means cathodic CP constant-current segment. `phase=1` means anodic CA constant-potential segment.

Ignore metadata comment lines beginning with `#`.

## Units

Always convert current from A to mA for plotting.

- Potential axis: `Potential (V)`
- Current axis: `Current (mA)`
- Time axis: `Time (s)`

Do not plot raw current in A unless the user explicitly asks.

## Default Style Constants

Use these defaults as the baseline. The exact colors may be changed using the palette rules below, but the line weights, font sizes, spacing, and axis habits should remain consistent.

```python
BLUE = "#3C9BC9"
RED = "#FC757B"
DARK = "#222222"
FIG_DPI = 300
SINGLE_SIZE = (3.45, 2.75)
ADT_SIZE = (8.2, 2.7)
SUMMARY_SIZE = (10.6, 3.15)
LINEWIDTH = 0.9
ADT_LINEWIDTH = 0.75
MARKER_SIZE = 2.5
MARKER_EDGE_WIDTH = 0.65
TITLE_SIZE = 7.5
LABEL_SIZE = 7.0
TICK_SIZE = 6.2
AXIS_WIDTH = 0.7
```

Matplotlib figure setup:

```python
fig = Figure(figsize=SINGLE_SIZE, dpi=FIG_DPI, facecolor="white")
```

Use `FigureCanvasAgg` for headless generation.

## Palette System

Use the P15 Summer Coast palette by default. This skill intentionally keeps only one stable color family so later figure generation stays consistent and does not drift into unrelated palette groups.

The default palette assets are saved at:

```text
skills/nature-electrochem-figures/assets/p15_palette_card.png
skills/nature-electrochem-figures/assets/p15_palette.csv
skills/nature-electrochem-figures/assets/p15_palette.json
```

Use these stable color numbers when the user specifies colors by index:

| ID | Name | HEX | RGB | Recommended use |
|---|---|---:|---:|---|
| P15-01 | Coral red | `#FC757B` | `rgb(252, 117, 123)` | current, after, highlight |
| P15-02 | Warm orange-red | `#F97F5F` | `rgb(249, 127, 95)` | adjacent warm category |
| P15-03 | Soft orange | `#FAA26F` | `rgb(250, 162, 111)` | non-electrical contrast |
| P15-04 | Peach | `#FDCD94` | `rgb(253, 205, 148)` | light fill or soft category |
| P15-05 | Light yellow | `#FEE199` | `rgb(254, 225, 153)` | pale highlight or background band |
| P15-06 | Soft green | `#B0D6A9` | `rgb(176, 214, 169)` | materials, chemistry, soft fill |
| P15-07 | Teal | `#65BDBA` | `rgb(101, 189, 186)` | non-electrical contrast |
| P15-08 | Blue | `#3C9BC9` | `rgb(60, 155, 201)` | potential, before, reference |

Tint notation:

- `P15-xx-100` means the base color at 100 percent strength.
- `P15-xx-80`, `P15-xx-60`, `P15-xx-40`, and `P15-xx-20` mean progressively lighter tints.
- Tint formula: `tinted_rgb = base_rgb * level + white_rgb * (1 - level)`.
- Example: `P15-01-60` means 60 percent `P15-01` mixed with 40 percent white.
- Use darker tints such as `P15-01-100` or `P15-08-100` for main traces.
- Use lighter tints such as `P15-01-40` or `P15-08-20` for replicates, uncertainty bands, background traces, or same-family gradients.

When a user specifies only `P15-01`, interpret it as `P15-01-100`.

Recommended pairings:

- `P15-08 + P15-01`: default before/after or potential/current comparison.
- `P15-03 + P15-07`: orange/teal contrast when red/blue would imply current/potential but the data are not current/potential.
- `P15-01 + P15-03 + P15-06 + P15-08`: four-category plots.
- `P15-04`, `P15-05`, and `P15-06`: soft fills, bands, panel annotations, or background context.

Default comparison palette:

```python
PALETTE_DEFAULT = {
    "blue": "#3C9BC9",
    "red": "#FC757B",
    "dark": "#222222",
    "gray": "#B8B8B8",
}
```

Use this for before/after, current/potential, and most two-trace electrochemistry figures.

Teal/orange palette:

```python
PALETTE_TEAL_ORANGE = {
    "teal": "#65BDBA",
    "orange": "#FAA26F",
    "dark": "#222222",
}
```

Use this when red/blue would imply current/potential but the data are not current/potential.

Categorical palette:

```python
PALETTE_CATEGORICAL = [
    "#FC757B",
    "#F97F5F",
    "#FAA26F",
    "#FDCD94",
    "#FEE199",
    "#B0D6A9",
    "#65BDBA",
    "#3C9BC9",
]
```

Monochrome plus highlight:

```python
PALETTE_MONO_HIGHLIGHT = {
    "gray": "#B8B8B8",
    "dark_gray": "#5A5A5A",
    "highlight": "#FC757B",
    "dark": "#222222",
}
```

Use this when most traces are context and one trace is the main result.

Multi-series categorical palette, maximum 8 traces:

```python
PALETTE_MULTI = [
    "#FC757B",  # coral red
    "#F97F5F",  # warm orange-red
    "#FAA26F",  # soft orange
    "#FDCD94",  # peach
    "#FEE199",  # light yellow
    "#B0D6A9",  # soft green
    "#65BDBA",  # teal
    "#3C9BC9",  # blue
]
```

If there are more than 8 traces, do not keep adding colors blindly. Prefer grouping, faceting, transparency, or plotting only representative traces plus a shaded range.

Semantic color rules:

- Current vs potential: current is red, potential is blue.
- Before vs after: before is blue, after is red.
- Negative/cathodic vs positive/anodic: cathodic/negative is red if it is a current setpoint; potential is blue.
- Reference/control vs treatment: reference is blue or gray, treatment is red/orange.
- Many comparable samples: use `PALETTE_MULTI` in a stable order and keep the same color mapping across all related figures.
- If color carries no meaning, use one color only and rely on labels, line style, or panels.

## Marker And Highlight Rules

Use markers as visual language, not decoration. Markers should either reveal sampling, compare discrete observations, or identify the key result.

Default line markers:

- Use open-circle markers for sampled electrochemistry traces, before/after comparisons, and long time-series where the sampling rhythm matters.
- Keep marker fill white and marker edge the same color as the line.
- Use `markevery` so markers are visible but not dense; aim for 25-40 visible markers per trace.
- Do not place a marker on every raw point for dense CHI data.

```python
mark_step = max(1, len(x) // 34)
ax.plot(
    x, y,
    color=BLUE,
    linewidth=0.9,
    marker="o",
    markevery=mark_step,
    markersize=2.5,
    markerfacecolor="white",
    markeredgecolor=BLUE,
    markeredgewidth=0.65,
)
```

Highlight markers:

- Use a filled star, filled circle, or slightly larger outlined circle only for the main result, best sample, selected condition, or "this work" point.
- Use at most 1-3 highlight markers in a normal panel.
- Use `P15-01` for the primary highlight unless another semantic color is already established.
- Keep highlight size modest: roughly 1.5-2.2 times the open-circle marker size.
- If a highlight marker appears on a line, keep the line thin and let the marker carry the emphasis.

```python
ax.scatter(
    [x_key], [y_key],
    marker="*",
    s=42,
    facecolor=RED,
    edgecolor=RED,
    linewidth=0.5,
    zorder=4,
    label="This work",
)
```

For literature or benchmark comparison plots, use small open circles for literature points and one filled star or filled circle for the current work. Add direct labels only when there are few points; otherwise use a compact legend.

## General Figure Types

Use the same style for non-ADT figures.

Single time-series:

```python
ax.plot(t, y, color=BLUE, linewidth=0.9)
```

Use markers only when the number of points is small or the sampling should be visible:

```python
mark_step = max(1, len(x) // 34)
ax.plot(x, y, color=BLUE, linewidth=0.9,
        marker="o", markevery=mark_step, markersize=2.5,
        markerfacecolor="white", markeredgewidth=0.65)
```

Scatter:

```python
ax.scatter(x, y, s=12, facecolors="white", edgecolors=BLUE,
           linewidths=0.7, alpha=0.95)
```

Mean with uncertainty:

```python
ax.plot(x, mean, color=BLUE, linewidth=0.9)
ax.fill_between(x, lo, hi, color=BLUE, alpha=0.18, linewidth=0)
```

Bar charts should be rare. If needed:

```python
ax.bar(x, y, color=BLUE, edgecolor="#222222", linewidth=0.5, width=0.72)
```

For grouped comparisons, prefer point-plus-errorbar over heavy bars:

```python
ax.errorbar(x, y, yerr=err, fmt="o", markersize=3.0,
            markerfacecolor="white", markeredgecolor=BLUE,
            ecolor=BLUE, elinewidth=0.75, capsize=2.0, color=BLUE)
```

Multi-panel summary figures:

- Use a horizontal row for 2-3 related panels.
- Use `constrained_layout=True` for summary figures.
- Do not add panel letters unless the user asks.
- Use one shared legend only when possible.
- Visually inspect the rightmost panel; tight bounding boxes can hide or compress it.

## Axis Rules

Apply this styling to normal single-axis plots:

```python
ax.set_title(title, fontsize=7.5, pad=3.0)
ax.set_xlabel(xlabel, fontsize=7.0, labelpad=2.0)
ax.set_ylabel(ylabel, fontsize=7.0, labelpad=2.0)
ax.tick_params(axis="both", which="major", labelsize=6.2,
               width=0.6, length=2.8, direction="out", pad=1.5)
ax.tick_params(axis="both", which="minor", width=0.45,
               length=1.6, direction="out")
ax.minorticks_on()
ax.grid(False)

for side in ("top", "right"):
    ax.spines[side].set_visible(False)
for side in ("left", "bottom"):
    ax.spines[side].set_linewidth(0.7)
    ax.spines[side].set_color("#222222")
```

Set y-limits from finite data with 8 percent padding:

```python
finite_y = np.asarray(y)[np.isfinite(y)]
if finite_y.size:
    y_min, y_max = float(np.min(finite_y)), float(np.max(finite_y))
    pad = max(abs(y_max - y_min) * 0.08, 0.5)
    ax.set_ylim(y_min - pad, y_max + pad)
```

## CV, LSV, and i-t Single Plots

Use one blue trace with open circle markers:

```python
mark_step = max(1, len(x) // 34)
ax.plot(
    x, y_ma,
    color=BLUE, linewidth=0.9,
    marker="o", markevery=mark_step, markersize=2.5,
    markerfacecolor="white", markeredgewidth=0.65,
)
```

Titles:

- CV: `CV`
- LSV: `LSV`
- i-t: `i-t`

Save with tight bounding box:

```python
fig.tight_layout(pad=0.35)
fig.savefig(out_path, facecolor="white", bbox_inches="tight")
```

## When Not To Use ADT Rules

Do not apply ADT-specific rules to unrelated data.

- Do not use twin y-axes unless the two quantities have genuinely different units and must be compared on the same time base.
- Do not force zero alignment unless zero has physical meaning in both axes.
- Do not use the categorical `-1, 0, 1` ADT program axis for normal time-series data.
- Do not split data into cathodic/anodic phases unless the CSV has explicit phase information or the experiment design requires it.
- Do not use current/potential color semantics for unrelated variables. Use the palette system instead.

For generic data, first identify the figure type:

- Single trace: one color, one axis.
- Two comparable traces: before/after or control/treatment palette.
- Many traces: categorical palette, reduced opacity, or selected representative traces.
- Different units on same x-axis: twin y-axis only if it clarifies the story.
- Distribution or replicate statistics: point-plus-errorbar or mean band, not heavy bars by default.

## Before/After ADT Comparison Plots

Use blue for before ADT and red for after ADT:

```python
def markevery(x):
    return max(1, len(x) // 28)

ax.plot(x_pre, y_pre_ma, color=BLUE, linewidth=0.9,
        marker="o", markevery=markevery(x_pre), markersize=2.6,
        markerfacecolor="white", markeredgewidth=0.65,
        label="Before ADT")
ax.plot(x_post, y_post_ma, color=RED, linewidth=0.9,
        marker="o", markevery=markevery(x_post), markersize=2.6,
        markerfacecolor="white", markeredgewidth=0.65,
        label="After ADT")
```

Legend:

```python
ax.legend(frameon=False, fontsize=5.9, loc="best",
          handlelength=1.4, borderaxespad=0.2, labelspacing=0.3)
```

For a summary figure, use one horizontal row of CV, LSV, and i-t panels:

```python
fig = Figure(figsize=(10.6, 3.15), dpi=300, facecolor="white",
             constrained_layout=True)
axes = fig.subplots(1, 3, squeeze=False)[0]
```

Do not add panel labels such as `a`, `b`, or `c` unless the user asks.

## ADT Program Plot

ADT program is a categorical waveform plot, not a normal numeric dual-axis plot.

Required behavior:

- Plot CP set-current on the lower half at y = -1.
- Plot CA set-potential on the upper half at y = 1.
- Draw a zero baseline at y = 0.
- Use red for CP current and blue for CA potential.
- Use a long horizontal figure: `(8.2, 2.7)` at 300 dpi.

Implementation pattern:

```python
current_level = np.where(np.isfinite(set_current), -1.0, np.nan)
potential_level = np.where(np.isfinite(set_potential), 1.0, np.nan)

plot_finite_segments(ax, t, current_level,
                     color=RED, linewidth=0.95, drawstyle="steps-post")
plot_finite_segments(ax, t, potential_level,
                     color=BLUE, linewidth=0.95, drawstyle="steps-post")

ax.axhline(0, color=DARK, linewidth=0.65, alpha=0.65)
ax.set_title("ADT program", fontsize=7.8, pad=3.0)
ax.set_xlabel("Time (s)", fontsize=7.0, labelpad=2.0)
ax.set_ylim(-1.35, 1.35)
ax.set_yticks([-1, 0, 1])
ax.set_yticklabels([current_label, "0", potential_label])
```

Example labels:

- `-250 mA CP`
- `0`
- `1.5 V CA`

If the CA potential is 0 V, label it as `0 V CA`; keep the middle tick as `0` for the baseline.

## ADT Response Plot

ADT response uses two y-axes:

- Left y-axis: CA current response in mA, red.
- Right y-axis: CP potential response in V, blue.
- Both axes must have the zero tick at the same screen height.

Only plot measured current during CA segments and measured potential during CP segments. Do not connect across missing phase gaps.

Implementation pattern:

```python
fig = Figure(figsize=(8.2, 2.7), dpi=300, facecolor="white")
ax_i = fig.add_subplot(111)
ax_e = ax_i.twinx()

plot_masked_segments(ax_i, t, current * 1000.0, ca_mask,
                     color=RED, linewidth=0.75)
plot_masked_segments(ax_e, t, potential, cp_mask,
                     color=BLUE, linewidth=0.75)

ax_i.axhline(0, color=DARK, linewidth=0.65, alpha=0.65)
ax_i.set_title("ADT response", fontsize=7.8, pad=3.0)
ax_i.set_xlabel("Time (s)", fontsize=7.0, labelpad=2.0)
ax_i.set_ylabel("Current (mA)", color=RED, fontsize=7.0, labelpad=2.0)
ax_e.set_ylabel("Potential (V)", color=BLUE, fontsize=7.0, labelpad=2.0)
```

Zero alignment:

```python
def align_twin_zero(ax_left, ax_right):
    left_min, left_max = ax_left.get_ylim()
    right_min, right_max = ax_right.get_ylim()
    left_span = max(abs(left_min), abs(left_max), 1e-12)
    right_span = max(abs(right_min), abs(right_max), 1e-12)
    ax_left.set_ylim(-left_span, left_span)
    ax_right.set_ylim(-right_span, right_span)
```

Style both y-axes:

```python
ax_i.tick_params(axis="both", which="major", labelsize=6.2,
                 width=0.6, length=2.8, direction="out", pad=1.5)
ax_e.tick_params(axis="y", which="major", labelsize=6.2,
                 width=0.6, length=2.8, direction="out", pad=1.5)
ax_i.tick_params(axis="y", colors=RED)
ax_e.tick_params(axis="y", colors=BLUE)
ax_i.grid(False)
ax_i.spines["top"].set_visible(False)
ax_e.spines["top"].set_visible(False)
ax_i.spines["left"].set_color(RED)
ax_e.spines["right"].set_color(BLUE)
ax_i.spines["bottom"].set_color(DARK)
ax_i.spines["left"].set_linewidth(0.7)
ax_i.spines["bottom"].set_linewidth(0.7)
ax_e.spines["right"].set_linewidth(0.7)
```

## Segment Plotting Helpers

Use these helpers to avoid drawing false connections across phase gaps:

```python
def plot_finite_segments(ax, x, y, **kwargs):
    finite = np.isfinite(y)
    start = None
    for idx, ok in enumerate(finite):
        if ok and start is None:
            start = idx
        if start is not None and (not ok or idx == len(finite) - 1):
            end = idx if not ok else idx + 1
            if end - start > 0:
                ax.plot(x[start:end], y[start:end], **kwargs)
            start = None

def plot_masked_segments(ax, x, y, mask, **kwargs):
    start = None
    for idx, ok in enumerate(mask):
        if ok and start is None:
            start = idx
        if start is not None and (not ok or idx == len(mask) - 1):
            end = idx if not ok else idx + 1
            if end - start > 1:
                ax.plot(x[start:end], y[start:end], **kwargs)
            elif end - start == 1:
                ax.scatter(x[start:end], y[start:end], s=8,
                           color=kwargs.get("color"))
            start = None
```

## Quality Checklist

Before returning the figure:

- Confirm current is plotted in mA.
- Confirm ADT response zero is aligned on both y-axes.
- Confirm no phase-gap connections are drawn in ADT.
- Confirm there is no grid.
- Confirm top and right spines are hidden for single-axis plots.
- Confirm default colors are `#3C9BC9` and `#FC757B`, or another explicitly requested P15 color.
- Confirm figures are saved at 300 dpi.
- Confirm summary plots do not use panel letters unless requested.
- Visually inspect the PNG if possible, especially the rightmost panel in summary figures.
