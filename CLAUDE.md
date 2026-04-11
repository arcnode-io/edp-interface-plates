## Methodologies

### Implementation Methodology
When presented with a request YOU MUST:
1. Use context7 mcp server or websearch tool to get the latest related documentation. Understand the API deeply and all of its nuances and options
2. Use TDD Approach: Derive the expected value in `theory.ipynb` first, then write the sim assertion in `run.py` that fails, then build the model until it passes
3. Start with the simplest hand calc — back-of-envelope before simulation
4. See the assertion fail against the notebook's expected value
5. Make the smallest change to the model
6. Check if `uv run poe checks` and `uv run poe cover` pass
7. Repeat steps 5-6 until the assertion passes
8. You MUST NOT move on until assertions pass

### Debugging Methodology

#### Phase I: Information Gathering
1. Understand the error
2. Read the relevant source code: try local `.venv`
3. Look at any relevant github issues for the library

#### Phase II: Testing Hypothesis
4. Develop a hypothesis that resolves the root cause of the problem. Must only chase root cause possible solutions. Think hard to decide if its root cause or NOT.
5. Add debug logs to determine hypothesis
6. If not successful, YOU MUST clean up any artifact or code attempts in this debug cycle. Then repeat steps 1-5

#### Phase III: Weigh Tradeoffs
7. If successful and fix is straightforward. Apply fix
8. If not straightforward, weigh the tradeoffs and provide a recommendation


## Units & Dimensional Analysis — Non-Negotiable

Bare floats are the `Any` of engineering. Every physical value MUST have a pint unit.

- **No bare floats for physical quantities.** `velocity = 3.5` is NEVER ALLOWED. `velocity = 3.5 * ureg.m / ureg.s` is correct.
- **No manual unit conversions.** Let pint `.to()` handle all conversions. Manual conversion factors are the equivalent of `# type: ignore` — they bypass the guardrail.
- **No `float` annotations for physical quantities.** Use `pint.Quantity` in type hints.
  - NOT: `def calc_force(mass: float, accel: float) -> float:`
  - CORRECT: `def calc_force(mass: Quantity, accel: Quantity) -> Quantity:`
- **Use domain-conventional units, not SI base units everywhere.** kA not A for fault current, bar not Pa for hydraulic pressure, AWG not m² for wire gauge. Let pint handle the conversion to SI when computation requires it.


## Uncertainty & Precision

- **No results without uncertainty.** If you can't state the error band, the result is incomplete. Use the `uncertainties` library to propagate error through calculations.
- **No false precision.** If your input is +/-5%, your output cannot have 7 significant figures. Report results to the number of significant figures justified by your inputs.
- **Never round intermediate results.** Carry full precision through the calculation chain. Round only in the final reporting cell.


## Constants & Physical Parameters

Every constant needs a name, a unit, and a source. A magic `0.85` in engineering could be a safety factor, a derating, an efficiency, or a power factor — getting it wrong can mean a fire.

- **All physical constants at module level in SCREAMING_SNAKE_CASE** with `Final` annotation, pint unit, and source comment
  ```python
  FUSE_DERATING: Final = 0.80 * ureg.dimensionless  # UL 248 Table 1
  GRAVITY: Final = 9.80665 * ureg.m / ureg.s**2  # ISO 80000-3
  ```
- **No inline physical constants.** Never write `force = mass * 9.81`. Define it once, name it, source it.
- **Standards references must include edition, table, and clause.** "Per IEEE 1547" is meaningless. "Per IEEE 1547-2018 Table 1, Category III" is a reference.


## Assumptions

AI silently assumes ideal conditions — zero wire resistance, no temperature derating, negligible contact resistance, lossless transmission. Every one of these is an engineering `Any`.

- **Every assumption must be stated explicitly** in the notebook's assumptions cell before any derivation
- **If you can't name the assumption, you can't validate the result**
- **When the sim disagrees with theory, the first place to look is the assumptions cell** — did an assumption break, or did the sim break?
- **No idealized defaults.** Real systems have parasitics, losses, and tolerances. State which you are neglecting and why.


## Notebook Discipline

`theory.ipynb` is a calculation document, not a tutorial.

- **Notebook structure:** Assumptions cell -> Derivation cells -> Expected value cell
- **The expected value cell is your type signature.** It defines what correct looks like before you simulate: `# Peak fault current: 4.2kA +/- 10%`
- **No tutorial-style prose between cells.** Brief `# Reason:` comments for non-obvious steps. The derivation speaks for itself.
- **Every notebook must be re-runnable.** No cells that depend on manual execution order.


## Simulation Validation

Never trust simulation output. Validate it.

### Order-of-Magnitude First
- Before running any sim, the notebook must have a hand calc that gets you within 2-5x of the answer
- If the sim is 10x off from the hand calc, one of them is wrong — figure out which before proceeding
- This is the engineering "see the test fail" step

### Conservation Law Checks
- Energy in = energy out + losses
- Mass flow in = mass flow out
- Current into a node = current out
- If conservation doesn't hold, the model is wrong — not the physics

### Convergence is Not Optional
- **Mesh convergence for FEM** — refine until the result stops changing within tolerance
- **Timestep convergence for transient sims** — halve the timestep and verify the result holds
- **Solver tolerance must be justified, not defaulted.** "It ran without errors" is not validation.


## Derating & Safety Factors

- **Components have temperature derating, altitude derating, aging factors.** These are not optional.
- **Safety factors must be explicit and sourced** — never assumed or buried in a calculation
- **Worst-case analysis is the default.** Nominal-case results are supplementary, not primary.


## Code Structure & Modularity

- **Write the most minimal code to get the job done**
- **Get to root of the problem.** Never write hacky workarounds. You are done when the assertions pass.
- **Never create a file longer than 200 lines of code.** If a file approaches this limit, refactor by splitting it into modules.


## Testing & Reliability

- **Fail fast, fail early.** Detect errors as early as possible and halt execution. Rely on the runtime to handle the error and provide a stack trace. You MUST NOT write random error handling for no good reason.
- **Use AAA (Arrange, Act, Assert) pattern for tests:**
  - **Arrange**: Set up the necessary context and inputs
  - **Act**: Execute the simulation or calculation
  - **Assert**: Verify the outcome matches the notebook's expected value within tolerance
- **Use `pytest.approx` with `rel` tolerance for physical quantity assertions**
  ```python
  assert actual_current.magnitude == pytest.approx(expected_current.magnitude, rel=0.10)
  ```


## Style

- **Constants in code:** Write top level declarations in SCREAMING_SNAKE_CASE with `Final` annotation
- **Use explicit type hints ALWAYS.** No `Any`. No bare `float` for physical quantities.
- **Prefer Pydantic models over dicts for structured data**
- **Use proper logging, not print() debugging**
- **Write concise Google Style Docstrings for an LLM to consume**

## Documentation
 - **Write comments in a terse and casual tone**
- **Comment non-obvious code.** Everything should be understandable to a mid-level d
eveloper.
- **Add an inline `# Reason:` comment** for complex logic — explain the why, not the what.


## AI Behavior Rules

- **Never declare an API broken without research and confirmation.** If something doesn't work as expected, the first assumption is that you're using it wrong. Before concluding "bug": (1) search docs, forums, and GitHub issues, (2) read the library source, (3) write an isolated probe that eliminates your own usage errors. Only after all three confirm the behavior, label it a bug.


## Anti-Bias Rules

| AI Bias | Correct Practice |
|---|---|
| Declares an API broken after one failed attempt | Research docs + forums + issues first. Write an isolated test. Your usage is wrong until proven otherwise |
| Uses ideal/textbook models by default | Real systems have parasitics, losses, tolerances — state which you're neglecting and why |
| Writes tutorial-style notebooks with markdown explanations between every cell | Notebook is a calculation document — derivation, numbers, expected value. Not a teaching tool |
| Presents single-point results as definitive | Every result has a tolerance band. If you can't state the band, you don't understand the result |
| Defaults to SI base units everywhere | Use domain-conventional units — kA for fault current, bar for hydraulic pressure, AWG for wire gauge |
| Rounds intermediate results | Never round until final reporting. Carry full precision through the calculation chain |
| Skips derating and safety factors | Components have temperature derating, altitude derating, aging factors. These are not optional |
| Cites standards without edition/table/clause | "Per IEEE 1547" is meaningless — "Per IEEE 1547-2018 Table 1, Category III" is a reference |
| Uses default solver settings without justification | Timestep, mesh density, tolerance — all must be explicit choices with stated rationale |
| Trusts simulation output without sanity checks | Conservation law check and order-of-magnitude hand calc before accepting any result |


## Mechanical Engineering Best Practices


### ME-Conventional Units

Use the units that appear on drawings and datasheets, not SI base units.

| Quantity | Use | Not |
|---|---|---|
| Length / dimensions | mm | m |
| Force | N, kN | — |
| Stress / modulus | MPa, GPa | Pa |
| Moment of inertia | mm^4 | m^4 |
| Deflection | mm | m |
| Mass | kg | — |
| Temperature | degC | K (except for thermal calcs) |

Let pint `.to()` handle conversion when computation requires it.


### CadQuery — Parametric Geometry in Python

Geometry is defined in `cad/model.py` using CadQuery. This is the mechanical equivalent of SKiDL — the geometry lives in code, not in a GUI file.

```python
import cadquery as cq
from sim.constants import BEAM_LENGTH, BEAM_WIDTH, BEAM_HEIGHT, ureg

def build_beam() -> cq.Workplane:
    l = BEAM_LENGTH.to(ureg.mm).magnitude
    w = BEAM_WIDTH.to(ureg.mm).magnitude
    h = BEAM_HEIGHT.to(ureg.mm).magnitude
    return cq.Workplane("XY").box(l, w, h)
```

**Key rules:**
- Dimensions come from `sim/constants.py` — strip pint units before passing to CadQuery
- Export to STEP for downstream FEM: `beam.export("cad/part.step")`
- CadQuery SVG export for drawings (front, side, iso projections)
- FreeCAD for interactive inspection only — not the source of truth


### pygccx — CalculiX FEM via Python

FEM analysis uses pygccx, which handles mesh generation (gmsh), input deck writing, solving (CalculiX), and result parsing in a single API.

```python
from pygccx import model as ccx_model
from pygccx import model_keywords as mk
from pygccx import step_keywords as sk
from pygccx import enums

with ccx_model.Model(CCX_PATH, CGX_PATH, jobname="part", working_dir=wkd) as model:
    gmsh = model.get_gmsh()
    gmsh.model.occ.importShapes("cad/part.step")
    gmsh.model.occ.synchronize()
    gmsh.model.mesh.generate(3)

    gmsh.model.add_physical_group(3, [1], name="BODY")
    gmsh.model.add_physical_group(2, face_tags, name="FIX")

    model.update_mesh_from_gmsh()
    mesh = model.mesh

    mat = mk.Material("STEEL")
    el = mk.Elastic((E_mpa, nu))
    sos = mk.SolidSection(elset=mesh.get_el_set_by_name("BODY"), material=mat)
    fix_set = mesh.get_node_set_by_name("FIX")
    model.add_model_keywords(mk.Boundary(fix_set, first_dof=1, last_dof=3), mat, el, sos)

    step = sk.Step(nlgeom=False)
    step.add_step_keywords(sk.Static(), cload, sk.NodeFile([enums.ENodeFileResults.U]), sk.ElFile([enums.EElFileResults.S]))
    model.add_steps(step)

    model.solve()
    frd = model.get_frd_result()
```

**Key rules:**
- Physical groups in gmsh define node/element sets for BCs and material assignment
- `model.update_mesh_from_gmsh()` converts gmsh mesh to pygccx mesh
- Node set `.ids` returns a `set[int]` — use `list()` for iteration
- **Cast numpy int64 to `int()` before passing to Cload** — pygccx `isinstance(nid, int)` fails on numpy types
- Use `st.get_mises_stress()` from `pygccx.tools.stress_tools` for von Mises — don't hand-roll
- Results from `frd.get_result_sets_by(entity=enums.EFrdEntities.DISP)` return numpy arrays


### FEM Validation Rules

- **Mesh convergence:** Refine mesh until result changes < 2% between refinements
- **Sanity check:** FEM result must be within 10% of Euler-Bernoulli hand calc for simple geometries
- **Element quality:** gmsh reports mesh quality — no degenerate tets (quality > 0.2)


### Poe Tasks (standardized across all templates)

| Task | What it does |
|------|-------------|
| checks | ruff format + lint |
| notebook | execute theory.ipynb |
| build | generate code-driven artifacts (STEP) |
| sim | simulation + pytest assertions |
| validate-model | design rule checks (BRep+bbox) |
| inspect-model | open single model GUI (part) |
| inspect-asm | open assembly GUI (multi-body STEP) |
| drawings | export SVG/PDF to spec/drawings/ |
| cover | pytest + coverage |
| review | AI code review |
| commit | full pipeline → push |


### CadQuery Gotchas

- **Never use `.faces()` selectors for hole placement.** CadQuery's `<X`/`>X` face selectors pick faces by center coordinate, which is ambiguous on L-shapes and complex geometry. Instead, cut holes explicitly with `.cut()` using cylinders at known 3D coordinates.
- **CadQuery `.fillet()` on `edges("|Y")` fillets ALL Y-parallel edges.** Use `.filter(lambda edge: ...)` with bounding box checks to target a specific edge.
- **CadQuery `extrude()` on XZ workplane goes in -Y direction.** Account for this when computing 3D positions for downstream operations.
- **CadQuery color names are limited.** Use `cq.Color(r, g, b)` with floats 0-1 instead of named colors — many common names like `"darkgray"` are not recognized.
- **CadQuery Assembly**: `assy.add(part, loc=cq.Location((x,y,z), (rx,ry,rz)))` for positioning. Rotation is Euler angles in degrees.


### gmsh / OCC Geometry Gotchas

- **OCC splits cylindrical hole surfaces into half-cylinders.** A through-hole produces 2 cylinder faces, each with area ≈ π·d·t/2. Detect by matching half the expected area, not full.
- **Use `gmsh.model.getType(dim, tag)` to distinguish surface types.** Returns `"Cylinder"`, `"Plane"`, `"BSpline"`, etc. Filter by type before checking area or bbox to avoid false matches (e.g. fillet cylinders vs bolt hole cylinders).
- **Use `gmsh.model.occ.getMass(dim, tag)` for surface area.** This is the reliable way to get face area for identification — more robust than bbox dimensions.
- **Fillet surfaces are also cylinders in OCC.** A 90° fillet of radius r across width w has area = π·r·w/2. Distinguish from bolt holes by area magnitude.


### pygccx Reaction Force Extraction

- **Request reaction forces with `sk.NodeFile([enums.ENodeFileResults.RF])`** in the step keywords. Results appear in FRD as `enums.EFrdEntities.FORC`.
- **Split constrained nodes by coordinate to get per-feature forces.** Sum reaction vectors per group, then take magnitude for the resultant.
- **Fixing all DOFs on cylindrical hole surfaces models a rigid pin.** This over-constrains vs real bolted connections. Expect FEM bolt forces to be 15-25% lower than rigid-bracket hand calcs — the hand calc is intentionally conservative for design.


### Hand Calc vs FEM Tolerance Guidelines

| Comparison | Typical tolerance | Reason |
|---|---|---|
| Simple beam (Euler-Bernoulli vs FEM) | 5-10% | Closed-form is exact for prismatic beams |
| Bolt group (rigid assumption vs FEM) | 20-25% | Rigid bracket assumption is conservative by design |
| Stress at geometric discontinuities | 10-15% | Mesh-dependent near fillets, holes, corners |
| Global equilibrium (total reaction vs applied load) | < 1% | Must hold — if not, model is broken |


