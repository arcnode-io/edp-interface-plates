---
name: generate-gdt
description: Add manufacturing annotations (view labels, dimensions, tolerances, surface finish) to a FreeCAD TechDraw drawing. Two-phase — deterministic edge matching then visual review loop.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent
---

# Generate GD&T Manufacturing Annotations

Add dimensions, tolerances, view labels, and surface finish callouts to an existing TechDraw drawing exported by `export_drawing.py`.

## Prerequisites

- `uv run poe generate-asm` must have run successfully — views must exist on the page
- `cad/layout_spec.yaml` defines sheet size, views, tolerances, and general tolerance class
- `sim/constants.py` defines all bracket geometry constants (used for edge matching)

## Phase 1: Deterministic Dimension Placement

Run `cad/drawing/dimensions.py` inside FreeCAD to add dimensions programmatically.

### 1. Edge Matching Strategy

After `doc.recompute()`, match edges by **curve type + length** to known constants from `sim/constants.py`. This is deterministic for a given part geometry.

```python
edges = view.getVisibleEdges()
for i, edge in enumerate(edges):
    curve = edge.Curve
    length = edge.Length
    # Match Line edges by length to constants
    # Match Circle edges by radius to HOLE_DIAMETER/2
```

**Known edge map for L-bracket (from probing):**

Front view `(0, -1, 0)`:
| Edge | Curve | Length/Radius | Constant |
|------|-------|---------------|----------|
| Edge5 | Line | 80mm | VERTICAL_LEG_HEIGHT |
| Edge6 | Line | 74mm | HORIZ_LEG + THICKNESS |
| Edge2 | Line | 14mm | BRACKET_THICKNESS |
| Edge0 | Line | 52mm | HORIZ_LEG - 2*FILLET_RADIUS (visible portion) |
| Edge1 | Circle | 12.6mm arc | fillet arc (R8) |

Right view `(1, 0, 0)`:
| Edge | Curve | Radius | Constant |
|------|-------|--------|----------|
| Edge4,5 | Circle | 4.25mm | HOLE_DIAMETER/2 (top hole, split) |
| Edge11 | Circle | 4.25mm | HOLE_DIAMETER/2 (bottom hole) |

**IMPORTANT:**
- Edge indices are HLR-dependent. Always match by geometry (type + length/radius), never by hardcoded index. The edge map above is a reference — verify at runtime.
- `getVisibleEdges()` returns **model-space** lengths, NOT scaled. Match against raw constant values (e.g. 80.0, not 80.0 * scale).
- HLR runs asynchronously — must call `Gui.updateGui()` + `time.sleep(0.3)` loop (10 iterations) after `doc.recompute()` before accessing edges. Without this, `getVisibleEdges()` returns empty.

### 2. Dimensions to Add

**Front view:**
1. **Vertical leg height** — DistanceY on Edge5 → 80mm
2. **Total width** — DistanceX on Edge6 → 74mm (or break into 60mm leg + 14mm thickness)
3. **Bracket thickness** — DistanceX on Edge2 → 14mm
4. **Fillet radius** — Radius on Edge1 → R8

**Right view:**
5. **Bolt hole diameter** — Diameter on hole circle → ⌀8.5 H9
6. **Bolt spacing** — Distance between hole centers → 50mm ±0.1
7. **Bracket width** — DistanceX → 50mm

### 3. Tolerances

Read `general_tolerance` from `layout_spec.yaml` (default: `ISO 2768-m`).

| Feature | Tolerance | Source |
|---------|-----------|--------|
| Bolt holes | H9 (+0.036/+0) | ISO 286, clearance fit for M8 |
| Bolt spacing | ±0.1mm | Critical for bolt pattern alignment |
| General dims | ISO 2768-m | All dimensions not specifically toleranced |

Apply via `DrawViewDimension` properties:
```python
dim.FormatSpec = "%.1f"  # or custom format
dim.OverTolerance = 0.036
dim.UnderTolerance = 0.0
```

### 4. View Labels

`DrawViewAnnotation` X/Y works — but **must be set AFTER `page.addView(anno)`**, then `doc.recompute()`. Setting before `addView` gets overwritten to page center. This is an ordering requirement, not a bug.

```python
anno = doc.addObject("TechDraw::DrawViewAnnotation", "LabelFront")
anno.Text = ["FRONT"]
anno.TextSize = 5.0
page.addView(anno)       # adds to page (resets X/Y to center)
anno.X = front_cx        # set AFTER addView
anno.Y = front_cy - 30   # below view
doc.recompute()
```

Labels needed: `FRONT`, `RIGHT`, `TOP`, `ISOMETRIC` — positioned below each view. Already placed by `dimensions.add_view_labels()` in Phase 1.

**Label placement rules:**
- Labels go **below** the view, never overlapping part geometry
- Use `cy - 30` offset (30mm below view center) as starting point
- During visual review, verify no label overlaps any part outline — adjust Y downward if needed
- For isometric views, the part extends further below center — use a larger offset or check visually
- Label text: 5mm, bold, centered horizontally on the view

### 5. Title Block Annotations

Add to title block via `tmpl.EditableTexts`:
- `general_tolerance`: "ISO 2768-m" (or from layout_spec)
- `surface_finish`: "Ra 3.2 (machined) / As-printed (MJF)" for PA12
- Verify material field matches `sim/constants.py`

## Phase 2: Visual Review Loop (max 5 iterations)

Phase 1 places correct dimensions on correct edges, but TechDraw's auto-placement defaults produce mediocre presentation. This phase refines:
- **Dimension leader line angles** — hole callout rotated diagonally, should be horizontal
- **Text size** — too small at print scale
- **Spacing** — dimensions crowded near fillet area, need breathing room
- **Missing dimensions** — bolt spacing (50mm center-to-center) not yet placed
- **Offsets** — arrows sit on edges instead of being spaced out via extension lines

**Iteration cycle:**

1. **Run full export:**
   ```bash
   uv run poe generate-asm
   ```
2. **Export PNG for review:**
   ```bash
   rsvg-convert -w 2400 output/drawings/l_bracket_sheet.svg -o /tmp/drawing_review.png
   ```
3. **Read and inspect the PNG** — look for:
   - Dimension lines overlapping views or each other
   - Leader lines crossing
   - Labels clipped by sheet border or title block
   - Tolerances illegible (too small or overlapping)
   - Dimension text not readable at print scale
   - Missing dimensions on critical features
4. **If issues found:** adjust in `dimensions.py` (offsets, FormatSpec, text size), re-run from step 1
5. **If clean:** proceed to final export

After converging, the adjusted values become the defaults in `dimensions.py`.

## Phase 3: Final Export

Run the full pipeline:
```bash
uv run poe generate-asm
```

This produces:
- `output/drawings/l_bracket.pdf` — full drawing with dimensions
- `output/drawings/l_bracket.dxf` — DXF with dimension entities
- `output/drawings/l_bracket_sheet.svg` — intermediate SVG

Do NOT run `poe generate-asm` during the review loop — it rebuilds views from scratch. Only run `dimensions.py` directly during iteration.

## Reference: TechDraw Dimension API

```python
import TechDraw

# Distance dimension between two edges
dim = doc.addObject("TechDraw::DrawViewDimension", "DimHeight")
dim.Type = "DistanceY"
dim.References2D = [(view, "Edge5")]  # or two edges for between-edges
dim.FormatSpec = "%.0f"
page.addView(dim)

# Diameter dimension on a circle
dim = doc.addObject("TechDraw::DrawViewDimension", "DimHole")
dim.Type = "Diameter"
dim.References2D = [(view, "Edge11")]
dim.FormatSpec = "⌀%.1f H9"
page.addView(dim)

# Radius dimension on an arc
dim = doc.addObject("TechDraw::DrawViewDimension", "DimFillet")
dim.Type = "Radius"
dim.References2D = [(view, "Edge1")]
dim.FormatSpec = "R%.0f"
page.addView(dim)
```

## Reference: ISO 2768-m General Tolerances

| Nominal range (mm) | Tolerance (±mm) |
|---------------------|-----------------|
| 0.5–3 | ±0.1 |
| 3–6 | ±0.1 |
| 6–30 | ±0.2 |
| 30–120 | ±0.3 |
| 120–400 | ±0.5 |

## Reference: For 3D Printed Parts (PA12 MJF)

- ISO 2768-c (coarse) or -v (very coarse) more realistic than -m
- Focus dimensions on functional features only (mating surfaces, hole positions)
- Surface finish callouts not applicable — finish is process-dependent
- Still need all critical dimensions for inspection
- Consider noting "As-printed" surface finish in title block

## Layout Spec Tolerance Fields

```yaml
tolerances:
  general: "ISO 2768-m"
  holes:
    fit_class: "H9"
    over_tolerance: 0.036
    under_tolerance: 0.0
  bolt_spacing:
    tolerance: 0.1
  surface_finish: "As-printed (HP MJF)"
```
