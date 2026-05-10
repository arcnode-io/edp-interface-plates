---
name: generate-gdt
description: Add GD&T manufacturing annotations (dims, tolerances, view labels, surface finish, notes) to FreeCAD TechDraw drawings for the plate fleet. One invocation per (plate_id, deployment_context) pair. Compounds learnings as new plates are processed.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent
---

# Generate GD&T Manufacturing Annotations — Plate Fleet

Adds dimensions, tolerances, view labels, notes block, and detail views to existing TechDraw drawings exported by `cad/drawing/export_plate_drawing.py`. Single invocation per `(plate_id, deployment_context)` pair.

## Scope

| Plate fleet | CG, BG-AC, BG-DC, CD |
|---|---|
| Geometry | 640 × 840 × 6mm (commercial) or × 10mm (defense), 8-bolt perimeter pattern |
| Slot mitigation (ADR-015) | 4 corners + 2 long-axis midpoints slotted 13mm × Ø11; short-axis midpoints round Ø11 |
| Penetrations | per `cad/specs/{plate_id}/spec.yaml::penetration_schedule`; CG=3, BG-AC=4, BG-DC=4, CD=4 |
| Per-context drawings | `plate.dxf` (commercial) + `plate-defense.dxf` (defense) emitted separately — no alt-note hedging |

## Prerequisites

- `uv run poe build --plate-id {ID}` (cadquery STEP) and `uv run poe build-defense` for defense variant
- `uv run poe generate-plate-{id}` runs FreeCAD TechDraw pipeline — produces views on page
- `cad/specs/{plate_id}/spec.yaml` defines outer dims, penetrations, mounting bolts, deployment contexts
- `sim/{plate_id}/constants.py` defines material constants (used for inspection callouts)

## Design contract (locked PM 2026-05-09)

**Views (4):** TOP (primary, dominant), FRONT (6/10mm thickness sliver), ISO (context), DETAIL (2:1 corner slot).

**Tolerances:**
| Feature | Tolerance | Reason |
|---|---|---|
| General | ISO 2768-m | per ADR-015 |
| Bolt holes Ø11 | H9 | bolt-to-slot-side bearing |
| Slot length 13mm | ISO 2768-m (±0.2) | sliding clearance, thermal headroom 0.751mm |
| Slot width 11mm | H9 | matches round bolt holes |
| Penetrations | H10 | clearance fit for hub installation; doesn't bias seal toward leakage |

**Datums:** A = plate face (back of FRONT view, controls thickness); B = horizontal centerline; C = vertical centerline.

**Position dims:** ordinate from centerlines (B/C). Plate is symmetric → centerlines natural. Avoids chained tolerance stack.

**Notes block** (left of title block):
1. MATERIAL PER TITLE BLOCK
2. ANODIZE PER TITLE BLOCK (AFTER MACHINING)
3. DEBURR ALL EDGES; BREAK SHARP CORNERS 0.3mm × 45°
4. GENERAL TOLERANCE PER TITLE BLOCK
5. GROUND STUD: TAP M10 (commercial) / M12 (defense) PER TITLE BLOCK
6. (defense only) APPLY EPDM SECONDARY SEAL PER MIL-DTL-XXXX [⚠ flag for spec lookup before drawing release; do NOT ship TBD spec number]

**Title block** (read from spec.yaml + deployment_context):
- `surface_finish`: `deployment_contexts.{ctx}.finish` (e.g. "Type II anodize 15-25 μm (MIL-A-8625)")
- `material`: `deployment_contexts.{ctx}.material` (e.g. "6061-T6 aluminum (ASTM B209)")
- `general_tolerance`: "ISO 2768-m"
- `part_number`: `ARC-PLT-{id}-{rev}` + "-D" suffix for defense
- `revision`: `default_params.revision` (e.g. "001")

**Detail view:** anchor at corner bolt slot (e.g. position (+260, +360)), 2:1 scale, shows 13mm × Ø11 slot with radial arrow toward pattern center. Single annotation **"TYP 6 PLACES (4 corners + 2 long-axis midpoints, slot oriented radially toward pattern center)"**.

## Phase 1: Deterministic dim placement

Lives in `cad/drawing/plate_dimensions.py`. Operates on plain dicts (loaded from spec.yaml YAML) — does NOT depend on cadquery so it can run inside FreeCAD's bundled Python.

### 1. Edge matching strategy

After `doc.recompute()`, match edges by **curve type + length** to known dims from `spec.yaml`. This is deterministic for a given plate geometry.

```python
edges = view.getVisibleEdges()
for i, edge in enumerate(edges):
    curve_type = type(edge.Curve).__name__
    # Line edge → match length to outer dim or slot length
    # Circle edge → match radius to bolt Ø/2 or penetration Ø/2
```

### 2. Known edge map per plate (TOP view, normal +Z)

| Edge kind | Match key | Source |
|---|---|---|
| Outer width | Line, length = `outer_dims_mm.W` (640) | spec.yaml |
| Outer length | Line, length = `outer_dims_mm.L` (840) | spec.yaml |
| Bolt hole | Circle, radius = `mounting_bolts.diameter_mm / 2` (5.5) | spec.yaml |
| Slot side | Line, length ≤ `slot_length_mm - diameter_mm` (≤ 2mm) | spec.yaml |
| Slot end-cap | Circle, radius = `diameter_mm / 2` (5.5) | spec.yaml |
| Penetration | Circle, radius from `_resolve_diameter(pen, params, ctx) / 2` | spec.yaml + params |

**IMPORTANT:**
- Edge indices are HLR-dependent — always match by geometry, never hardcoded index
- `getVisibleEdges()` returns model-space lengths, NOT scaled. Match raw spec values
- HLR runs async — call `Gui.updateGui()` + `time.sleep(0.3)` × 10 after `doc.recompute()` before accessing edges
- Slot edges: a 13×11 slot has 2 short Line sides (length = slot_length − diameter = 2mm) + 2 semicircle end-caps (radius = bolt_clearance_radius = 5.5mm). The end-cap radius **collides** with bolt-hole radius — disambiguate by checking position (slots are at corners + long-axis midpoints; round bolts are at short-axis midpoints).

### 3. Dimensions to add (per plate)

**TOP view:**
1. **Outer width** → `DistanceX` on outer edge, format `%.0f`
2. **Outer length** → `DistanceY` on outer edge, format `%.0f`
3. **Per-penetration position** → 2 ordinate dims (X/Y from centerline), format `%.0f`
4. **Per-penetration diameter** → `Diameter` on penetration circle, format depends on pen.id:
   - power/data conduit: `⌀%.1f H10 ({pen.id})`
   - ground_stud: `⌀%.1f M{ground_stud_size} TAP THRU` (per context)
5. **Bolt diameter** → `Diameter` on bolt circle, format `8X ⌀%.1f H9` (one callout, TYP all bolts)
6. **Bolt pattern positions** → ordinate dims at one corner + one short-axis midpoint, with TYP note
7. **Slot length** → `Distance` between slot end-cap centers, format `%.0f` + note "13 SLOT"
8. **Slot orientation arrow** → manual annotation pointing radially toward pattern center

**FRONT view:**
9. **Plate thickness** → `DistanceY` on edge thickness, format `%.0f` (6mm commercial / 10mm defense, from `deployment_contexts.{ctx}.thickness_mm`)

**DETAIL view (2:1 scale at corner slot):**
10. **Slot length** 13mm → `DistanceX` on slot, format `%.0f` + tolerance note "ISO 2768-m"
11. **Slot width** Ø11 → `Diameter` on end-cap, format `⌀%.1f H9`
12. **TYP annotation** → manual text "TYP 6 PLACES (4 CORNERS + 2 LONG-AXIS MIDPOINTS)"

### 4. Tolerances applied to dim properties

```python
# H9 hole (M10 clearance, 6-30mm range, +0.036/+0)
dim.OverTolerance = 0.036
dim.UnderTolerance = 0.0
dim.FormatSpec = "⌀%.1f H9"

# H10 hole (M73 conduit hub, 30-80mm range, +0.120/+0)
dim.OverTolerance = 0.120  # ISO 286-2 H10 for 50-80mm range
dim.UnderTolerance = 0.0
dim.FormatSpec = "⌀%.1f H10"

# ISO 2768-m on general dims (handled by title block, no per-dim tol)
dim.FormatSpec = "%.0f"
```

ISO 286-2 H9/H10 ranges by nominal diameter (mm):

| Range | H9 (+) | H10 (+) |
|---|---|---|
| 6-10 | 0.036 | 0.058 |
| 10-18 | 0.043 | 0.070 |
| 18-30 | 0.052 | 0.084 |
| 30-50 | 0.062 | 0.100 |
| 50-80 | 0.074 | 0.120 |
| 80-120 | 0.087 | 0.140 |

### 5. View labels

`DrawViewAnnotation` X/Y must be set **AFTER** `page.addView(anno)`, then `doc.recompute()`. Setting before `addView` gets overwritten to page center. Ordering requirement, not bug.

```python
anno = doc.addObject("TechDraw::DrawViewAnnotation", "LabelTop")
anno.Text = ["TOP"]
anno.TextSize = 5.0
page.addView(anno)
anno.X = top_cx
anno.Y = top_cy - 30
doc.recompute()
```

Labels needed: `TOP`, `FRONT`, `ISO`, `DETAIL A` (with detail bubble on TOP).

### 6. Notes block (left of title block)

`DrawViewAnnotation` with multi-line text:
```python
notes = doc.addObject("TechDraw::DrawViewAnnotation", "Notes")
notes.Text = [
    "NOTES:",
    "1. MATERIAL PER TITLE BLOCK",
    "2. ANODIZE PER TITLE BLOCK (AFTER MACHINING)",
    "3. DEBURR ALL EDGES; BREAK SHARP CORNERS 0.3mm x 45 deg",
    "4. GENERAL TOLERANCE PER TITLE BLOCK",
    "5. GROUND STUD: TAP PER TITLE BLOCK (COMMERCIAL M10 / DEFENSE M12)",
]
if deployment_context != "commercial":
    notes.Text.append("6. APPLY EPDM SECONDARY SEAL PER MIL-DTL-XXXX")  # ⚠ TBD lookup
notes.TextSize = 3.0
page.addView(notes)
notes.X = -180  # left side of A3 sheet
notes.Y = -100
```

## Phase 2: Visual review loop (max 5 iterations per plate)

Phase 1 places correct dims on correct edges; auto-placement defaults often produce mediocre presentation. This phase refines.

### Iteration cycle

1. **Run pipeline:**
   ```bash
   uv run poe generate-plate-{id}
   ```
2. **Export PNG for review:**
   ```bash
   rsvg-convert -w 2400 /tmp/{ID}_sheet.svg -o /tmp/drawing_review.png
   ```
3. **Read + inspect PNG** for:
   - Dim lines overlapping views or each other
   - Leader lines crossing
   - Labels clipped by sheet border or title block
   - Tolerances illegible at print scale
   - Missing dims on critical features (slot length most commonly missed)
   - Ordinate dim chains not clean (origin baseline visible?)
   - Detail bubble positioned wrong (should be on TOP at the detail's source edge)
4. **If issues:** adjust offsets in `plate_dimensions.py`, re-run from step 1
5. **If clean:** proceed to next plate

After CG converges, **before BG-AC**: update this skill file with edge-match recipes that worked + layout offsets that converged + gotchas hit.

### Chug-along gate

Skill is "done" when the next plate (after CG) runs clean in ≤2 iterations. If iter 3 still has layout issues on a non-CG plate, the skill needs another refinement pass before it's considered self-driving.

## Phase 3: Final export

Run full pipeline:
```bash
uv run poe generate-plate-{id}            # commercial
uv run poe generate-plate-{id}-defense    # defense (if added)
```

Produces:
- `output/drawings/{ID}_drawing.pdf` — full drawing with dims
- `output/drawings/{ID}.dxf` — DXF with dim entities

Per-context drawings emit separately: `plate.dxf`/`plate.pdf` for commercial, `plate-defense.dxf`/`plate-defense.pdf` for defense (no alt-note hedging — each drawing is unambiguous).

## Iteration order

CG → BG-AC → BG-DC → CD. AC before DC surfaces parametric differences before DC isolation callouts.

## Compounding learnings (filled in as plates converge)

### CG (commercial) — converged 2026-05-09 (iter 17)

**Edge map worked:** `_find_circles_by_radius(view, target_r)` with `target_scaled = target_r * scale` matches reliably. View `ScaleType="Custom"` is REQUIRED — default `"Page"` ignores `view.Scale` and breaks length matching.

**Sheet:** A1 landscape (841 × 594mm). A3 too tight for 4 views + dims + notes.

**View positions on A1:**
- TOP: (220, 320) — left half
- FRONT: (600, 480) — top-right thickness sliver
- ISO: (620, 300) — mid-right
- ISO scale = 0.6 × main scale (so it fits in remaining space)

**View source order matters:** set `v.Source / v.Direction / v.ScaleType / v.Scale` BEFORE `page.addView(v)`. Adding view first makes HLR initialize with empty source → only ~13 edges visible later instead of full ~30+.

**Dim placement gotcha (THE big one):**

`DrawViewDimension.X / .Y` is OFFSET from default placement. **Default is the VIEW CENTER, not the feature.** So `X=Y=0` puts ALL dim text at the view center → texts pile, leaders fan out radially (long arrows).

For short arrows + non-piling text:
```python
# Set X/Y ≈ feature's view-relative position, plus small bump in clear direction.
# Page Y axis points UP (model +y → page +y, no inversion).
feat_x = pen.x_mm * scale
feat_y = pen.y_mm * scale
bump = max(30.0, radius * scale + 30.0)  # text-center clears hole edge + half text width
dim.X = feat_x + bump   # bump direction picks the clear quadrant
dim.Y = feat_y + bump
```

For bolt callout (8X TYP), can't pick a target bolt by position because they all match radius. Read matched edge's curve center directly:
```python
matched_edge = view.getVisibleEdges()[int(longest[4:])]
center = matched_edge.Curve.Center  # already in render-space
dim.X = center.x + bolt_radius * scale + 25.0
dim.Y = center.y + bolt_radius * scale + 25.0
```

**Bump direction per pen quadrant:** check if the bump puts text on top of an unrelated feature (e.g. SW bump from a BL ground stud collides with the BL corner bolt). Flip direction toward plate interior in that case.

**Outer dim placement:** position OUTSIDE plate body so text lands in margin:
```python
half_w = wide_dim / 2 * scale
half_h = long_dim / 2 * scale
DimWidth (DistanceX): X=0,            Y=-half_h - 25  # below plate
DimHeight (DistanceY): X=half_w + 25, Y=0             # right of plate
```

**Annotation placement (Notes / SlotNote / view labels):** these are page-absolute mm and **center-anchored on text**. Notes block at X=120 (not 50) so 80mm-wide text doesn't clip past sheet edge.

**cadquery `.center()` accumulates** — never use it in a chained loop. Use `.pushPoints([(x, y)])` for absolute positioning. (Bit us hard: penetrations got drilled at wrong positions because `.center()` accumulated the offset across the loop.)

**Iteration count:** converged at iter 17. Most iters were chasing the dim-placement-default mystery before identifying view-center default. Once that was understood, 3 more iters to dial bumps + flip ground stud direction.

### CG (defense) — converged with commercial pipeline (no extra iters)

Defense path = same code, `--deployment-context defense_forward`. Picks `plate-defense.step` + appends `-D` to part number + adds note 6 (EPDM seal MIL-DTL-XXXX placeholder, flagged "[SPEC TBD]").

### BG-AC / BG-DC / CD — converged 2026-05-09 (zero per-plate iters needed)

Once skill knew the universal rules, BG-AC/BG-DC/CD produced clean drawings on first run. Confirms chug-along gate.

**Pen-id agnostic dim placement (key for multi-pen-per-quadrant plates):**

BG-AC has `power_conduit_left` / `power_conduit_right` (mirrored at Y=200, X=±150). Hardcoding bumps per-id ("if pen.id == 'power_conduit'") fails for these. Use position-driven rule instead:

```python
if pen["id"] == "ground_stud":
    sx, sy = 1.0, 1.0  # NE override (clears typical BL corner bolt)
else:
    sx = 1.0 if feat_x >= 0 else -1.0   # X outward → mirrored pairs diverge
    sy = -1.0 if feat_y > 0 else (1.0 if feat_y < 0 else -1.0)  # Y toward center
```

Outward X bump diverges mirrored pairs cleanly. Inward Y bump keeps text inside plate body (not in narrow top/bottom margin where corner bolts sit).

**Position block in margin, NOT on plate face:**

Consolidated text annotation listing all penetration + bolt positions ("FROM DATUM B/C") goes in the **bottom-center page margin** (X=470, Y=70 on A1) — between DETAIL view and title block. Earlier attempts on the plate body (X=120, Y=240 / Y=420) collide with features depending on plate variant. The margin spot is universal and clear.

**Title block field names (gotcha):**

A1_Landscape_EWAI.svg uses `identification_number` for the drawing-number field, **not** `drawing_number`. Setting the wrong key silently leaves the placeholder "DN" in the rendered output.

**Slot length dim removal:**

DETAIL view's slot side line measures `slot_length - bolt_diameter` = 2mm (not the 13mm total length). TechDraw FormatSpec doesn't do arithmetic, can't add bolt_diameter back. Solution: drop the buggy dim; carry "13×Ø11 H9" via the slot_note (right-of-TOP) and TYP block under DETAIL. Keep DimSlotWidth (Ø11 H9 ± 0.04) — that one measures correctly.

**TechDraw circle-circle DistanceX/Y is NOT center-to-center:**

Empirical: dimming X distance between penetration circle and a "datum bolt" (long-axis-midpoint at x=0) gave values 9-26mm off from spec. TechDraw appears to use tangent-based measurement for circle pairs. No reliable workaround without cosmetic-vertex API. Position block carries spec-exact text instead — correct value, just no measured leader.

## Reference: TechDraw dimension API

```python
import TechDraw

# DistanceX/Y — for outer + ordinate position dims
dim = doc.addObject("TechDraw::DrawViewDimension", "DimWidth")
dim.Type = "DistanceX"
dim.References2D = [(view, "Edge5")]
dim.FormatSpec = "%.0f"
page.addView(dim)
dim.X = 0  # set position AFTER addView
dim.Y = -long/2 - 30

# Diameter on a circle — penetration or bolt
dim = doc.addObject("TechDraw::DrawViewDimension", "DimHole")
dim.Type = "Diameter"
dim.References2D = [(view, "Edge11")]
dim.FormatSpec = "⌀%.1f H10"
dim.OverTolerance = 0.120
dim.UnderTolerance = 0.0
page.addView(dim)
```

## Reference: per-spec dim mapping

Map from `spec.yaml` → drawing dims:

| spec.yaml key | Dim | View | Tolerance |
|---|---|---|---|
| `outer_dims_mm.W` | DistanceX outer | TOP | ISO 2768-m |
| `outer_dims_mm.L` | DistanceY outer | TOP | ISO 2768-m |
| `deployment_contexts.{ctx}.thickness_mm` | DistanceY thickness | FRONT | ISO 2768-m |
| `mounting_bolts.diameter_mm` | Diameter on bolt circle | TOP | H9 |
| `mounting_bolts.slot_length_mm` | Distance slot length | TOP + DETAIL | ISO 2768-m |
| `penetration_schedule[*].x_mm` | DistanceX position | TOP | ISO 2768-m |
| `penetration_schedule[*].y_mm` | DistanceY position | TOP | ISO 2768-m |
| `_resolve_diameter(pen, params, ctx)` | Diameter on pen circle | TOP | H10 (or special tap callout for ground_stud) |

## Reference: dim positioning offsets (starting point)

For an A3 landscape sheet (420 × 297mm, title block 58mm at bottom):
- TOP view center: (110, 180)
- FRONT view center: (320, 235)
- ISO view center: (320, 130)
- DETAIL view center: (340, 50)
- Notes block: (-180, -100) [left side]
- Title block: bottom-right (auto-placed by template)

Outer dim offsets (TOP view):
- Width dim: y = -L/2 - 30 (below view)
- Length dim: x = -W/2 - 30 (left of view)
- Position ordinate stack: x = +W/2 + 30 + 8*i (right side, 8mm spacing)

Adjust during Phase 2 visual review; whatever values converge become defaults here.
