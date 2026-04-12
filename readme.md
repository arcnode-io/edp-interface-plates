# EDP Interface Plates 🔩📐

![](https://img.shields.io/gitlab/pipeline-status/arcnode-io/edp-interface-plates?branch=main&logo=gitlab)
![](https://gitlab.com/arcnode-io/edp-interface-plates/badges/main/coverage.svg)
![](https://img.shields.io/badge/3.13-gray?logo=python)
![](https://img.shields.io/badge/cad-cadquery-blue)
![](https://img.shields.io/badge/material-6061--T6-gray)

> interface plates that mount to container end walls and organize all inter-module connections


## Architecture Context

```plantuml
rectangle container_a
rectangle container_b
rectangle plate_a
rectangle plate_b
rectangle flexible_assembly

container_a -r- plate_a: receiver frame (welded)
container_b -l- plate_b: receiver frame (welded)
plate_a -r- flexible_assembly: liquid-tight conduit\nM12 connectors\ncooling QDs
flexible_assembly -r- plate_b
```

Containers are placed face-to-face. Plates mate as a pair via flexible assemblies — there is **no hard-dock interface**. Containers tolerate ±25mm horizontal and ±10mm vertical misalignment, absorbed by hose/cable service loops.

## Plate Variants

Six variants cover all module-adjacency combinations. Variant codes follow `[Module A]-[Module B]-[String/Port Count]` where applicable.

| Variant | Used When | Carries | Plate Codes |
|---|---|---|---|
| **BG** | Grid Module present | DC power, grounding, data | `BG-2`, `BG-4`, `BG-8` (per BESS string count) |
| **BB** | `N_BESS > 1` | Data + grounding only (no DC) | `BB` (fixed) |
| **CT** | Always (1:1 Compute:Thermal) | Cooling fluid + sensor data | `CT` (QD port size [OPEN] pending GPU vendor DLC spec) |
| **CG** | Grid Module present | AC feeder + data | `CG` (fixed, conduit sized from sizing engine Module F) |
| **CB** | `grid_connection == 'none'` | Off-grid AC feeder + data | `CB` (variant of CG) |
| **EX** | All deployments | External services on long wall | `EX-T`, `EX-G`, `EX-B`, `EX-C` (per module type) |

See the spec doc for full penetration schedules per variant.

## Material & Finish

| Parameter | Standard | Defense (`deployment_context == defense_forward \| sovereign_government`) |
|---|---|---|
| Outer dimensions | 640mm × 840mm | same |
| Thickness | 6mm | 10mm |
| Material | 6061-T6 aluminum (ASTM B209) | 5083-H116 marine grade (ASTM B209) |
| Finish | Type II anodize 15–25 μm (MIL-A-8625) | Type III hard anodize 40–60 μm |
| IP rating | IP55 | IP65 (verified per MIL-STD-810H Method 506) |
| Secondary seal | none | 10mm closed-cell EPDM backer |
| Fasteners | Zn-plated steel M10 (ASTM F593 G1) | 316 SS M10 (ASTM F593 G2) |

## Output Artifacts

For every plate variant required by a deployment, the implementation outputs:

1. **DXF file** — 2D fabrication drawing with plate outline, all hole/cutout locations dimensioned from plate center, gasket groove cross-section, mounting hole pattern with thread callouts, ARCNODE title block (part number, variant code, revision, material spec, finish spec).
2. **BOM line item** — structured JSON referencing the drawing:
   ```json
   {
     "part_number": "ARC-PLT-BG4-001",
     "description": "Interface Plate, BESS-to-Grid-Module, 4-String",
     "qty": 1,
     "material": "6061-T6 aluminum",
     "finish": "Type II anodize",
     "drawing_ref": "ARC-PLT-BG4-001.dxf",
     "type": "custom_fabrication"
   }
   ```
3. **Penetration schedule** — table of every hole/cutout: penetration ID, X/Y center coordinates from plate origin, diameter or W×H, fitting spec, OTS part number.

## Part Numbering

```
ARC - PLT - [VARIANT CODE] - [REVISION]

Examples:
  ARC-PLT-BG2-001    BESS-Grid, 2-String
  ARC-PLT-BG4-001    BESS-Grid, 4-String
  ARC-PLT-BG8-001    BESS-Grid, 8-String
  ARC-PLT-BB-001     BESS-BESS daisy chain
  ARC-PLT-CT-001     Compute-Thermal           [OPEN: QD port size]
  ARC-PLT-CG-001     Compute-Grid
  ARC-PLT-CB-001     Compute-BESS (off-grid)
  ARC-PLT-EX-T-001   External services, Thermal Module
  ARC-PLT-EX-G-001   External services, Grid Module
  ARC-PLT-EX-B-001   External services, BESS Module

Defense variants append `-D`:
  ARC-PLT-BG4-001-D
```

## Toolchain

The fabrication flow is CadQuery-based:

```
parametric model.py (CadQuery) → STEP → DXF + GD&T drawing → BOM line item + penetration schedule
```

```bash
uv sync
uv run poe build              # CadQuery → STEP per variant
uv run poe validate-model     # BRep validity + bbox vs spec
uv run poe generate-drawings  # DXF + GD&T PDF per variant
uv run poe sim                # IP rating verification fixtures
```

## Open Design Parameters

| # | Parameter | Impact |
|---|---|---|
| 1 | GPU vendor DLC loop architecture | CT plate QD port size and count |
| 2 | Off-grid inverter location | CB variant applicability |
| 3 | 4,160V AC option | CG conduit sizing changes significantly at MV |
| 4 | Dry cooler pipe connection size | EX-T plate flange size |
| 5 | MV grid cable entry | EX-G plate penetration sizing |
